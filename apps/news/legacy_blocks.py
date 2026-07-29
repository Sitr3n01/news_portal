"""Conversão do modelo antigo ``ArticleBlock`` para o StreamField ``Article.body``.

Este módulo é a ÚNICA descrição de como um bloco legado vira um bloco do
StreamField. Três consumidores dependem dela e não podem divergir:

* ``apps/news/migrations/0021_delete_articleblock.py`` — converte de verdade,
  imediatamente antes de derrubar a tabela;
* ``apps/news/management/commands/audit_article_blocks.py`` — prevê o resultado
  em produção sem escrever nada, para você decidir se pode rodar o ``migrate``;
* ``apps/news/management/commands/migrate_block_media.py`` — descobre quais
  ``media_library.MediaFile`` precisam de uma ``cms_media.Image`` correspondente.

Por que SQL puro nos comandos: o modelo ``ArticleBlock`` já foi removido de
``apps/news/models.py``, mas a tabela continua existindo no banco de produção até
a migration 0021 rodar. Os comandos precisam ler a tabela nesse intervalo, e não
há modelo para isso. A migration, ao contrário, usa modelo histórico
(``apps.get_model``) porque lá dentro o ``ArticleBlock`` ainda existe no estado.

Nada aqui importa models — só ``django.utils.html`` — para poder ser importado de
dentro de uma migration sem ciclo.
"""

import uuid

from django.utils.html import escape

ARTICLE_BLOCK_TABLE = 'news_articleblock'

# Espelha ArticleBlock.BlockType, que não existe mais como código.
BLOCK_RICH_TEXT = 'rich_text'
BLOCK_IMAGE = 'image'
BLOCK_EMBED = 'embed'

# Colunas lidas da tabela legada, na ordem usada por _row_to_block().
LEGACY_COLUMNS = ('id', 'article_id', 'order', 'block_type', 'rich_text', 'media_id', 'caption', 'embed_url')


# ── Leitura da tabela legada (para os comandos, fora de migration) ───────────


def article_block_table_exists(connection):
    return ARTICLE_BLOCK_TABLE in connection.introspection.table_names()


def fetch_legacy_blocks(connection):
    """Todos os blocos legados, em ordem de artigo e posição.

    Devolve lista de dicts com as chaves de LEGACY_COLUMNS. O nome da tabela é
    constante do módulo (não vem de entrada), então a interpolação é segura.
    """
    table = connection.ops.quote_name(ARTICLE_BLOCK_TABLE)
    columns = ', '.join(connection.ops.quote_name(name) for name in LEGACY_COLUMNS)
    order = ', '.join(connection.ops.quote_name(name) for name in ('article_id', 'order', 'id'))
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT {columns} FROM {table} ORDER BY {order}')
        return [dict(zip(LEGACY_COLUMNS, row)) for row in cursor.fetchall()]


def referenced_media_ids(connection):
    """IDs de ``media_library.MediaFile`` usados por blocos de imagem."""
    table = connection.ops.quote_name(ARTICLE_BLOCK_TABLE)
    block_type = connection.ops.quote_name('block_type')
    media_id = connection.ops.quote_name('media_id')
    with connection.cursor() as cursor:
        cursor.execute(
            f'SELECT DISTINCT {media_id} FROM {table} '
            f'WHERE {block_type} = %s AND {media_id} IS NOT NULL',
            [BLOCK_IMAGE],
        )
        return [row[0] for row in cursor.fetchall()]


# ── Conversão ───────────────────────────────────────────────────────────────


def _stream_item(block_type, value):
    return {'type': block_type, 'value': value, 'id': str(uuid.uuid4())}


def _caption_paragraph(caption):
    """Legenda perdida vira parágrafo — degrada, não desaparece."""
    return _stream_item('texto', f'<p>{escape(caption.strip())}</p>')


def build_stream_data(blocks, image_pk_for, outcomes=None):
    """Converte blocos legados de UM artigo na lista crua do StreamField.

    ``blocks``       — iterável de dicts/objetos com ``block_type``, ``rich_text``,
                       ``media_id``, ``caption`` e ``embed_url``, já na ordem certa.
    ``image_pk_for`` — callable ``media_id -> pk da cms_media.Image`` ou ``None``.
    ``outcomes``     — ``Counter`` opcional; recebe a contagem por desfecho, que é
                       o que o comando de auditoria reporta.

    Devolve a lista de dicts ``{'type', 'value', 'id'}`` pronta para
    ``json.dumps`` e atribuição a ``Article.body``.
    """
    def note(key):
        if outcomes is not None:
            outcomes[key] += 1

    stream = []
    for block in blocks:
        get = block.get if isinstance(block, dict) else lambda name: getattr(block, name, None)
        block_type = get('block_type') or ''
        rich_text = (get('rich_text') or '').strip()
        caption = (get('caption') or '').strip()
        embed_url = (get('embed_url') or '').strip()
        media_id = get('media_id')

        if block_type == BLOCK_RICH_TEXT:
            if rich_text:
                # Legenda em bloco de texto é raridade, mas se existir entra como
                # parágrafo final em vez de ser descartada.
                html = f'{rich_text}\n<p>{escape(caption)}</p>' if caption else rich_text
                stream.append(_stream_item('texto', html))
                note('texto')
            elif caption:
                stream.append(_caption_paragraph(caption))
                note('texto_so_legenda')
            else:
                note('vazio_descartado')

        elif block_type == BLOCK_IMAGE:
            image_pk = image_pk_for(media_id) if media_id else None
            if image_pk:
                stream.append(_stream_item('imagem', {'imagem': image_pk, 'legenda': caption}))
                note('imagem')
            elif caption:
                # Sem Image correspondente não há como montar o bloco de imagem;
                # preservar a legenda é melhor que sumir em silêncio.
                stream.append(_caption_paragraph(caption))
                note('imagem_sem_destino_com_legenda')
            else:
                note('imagem_sem_destino_perdida')

        elif block_type == BLOCK_EMBED:
            if embed_url:
                stream.append(_stream_item('embed', {'embed_url': embed_url, 'legenda': caption}))
                note('embed')
            elif caption:
                stream.append(_caption_paragraph(caption))
                note('embed_sem_url_com_legenda')
            else:
                note('embed_sem_url_perdido')

        else:
            # Tipo desconhecido (banco mais antigo que o código): salva o que der.
            if rich_text:
                stream.append(_stream_item('texto', rich_text))
                note('tipo_desconhecido_texto')
            elif caption:
                stream.append(_caption_paragraph(caption))
                note('tipo_desconhecido_legenda')
            else:
                note('tipo_desconhecido_perdido')

    return stream


def group_by_article(blocks):
    """Agrupa uma lista plana de blocos por ``article_id``, preservando a ordem."""
    grouped = {}
    for block in blocks:
        article_id = block['article_id'] if isinstance(block, dict) else block.article_id
        grouped.setdefault(article_id, []).append(block)
    return grouped
