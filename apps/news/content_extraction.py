"""Extração do texto pesquisável de ``Article.body`` (StreamField) para ``content``.

``content`` não é decoração: é o campo que ``apps.news.views.article_search``
consulta com ``content__icontains``, a base de ``Article.reading_time`` e o teaser
da newsletter. **Todo bloco que carrega texto visível tem de contribuir aqui** —
senão o texto existe na matéria e não existe na busca.

Vive fora de ``models.py`` de propósito: uma data migration precisa reconstruir
``content`` com exatamente esta lógica, e migration não deve importar método de
modelo vivo (mesma razão da nota em ``0019_backfill_content_from_body``). Aqui é
função pura sobre o StreamValue — nada de models, nada de ciclo de import.

Ao adicionar um bloco novo em ``apps/news/blocks.py``, decida aqui se ele entra na
busca. O ``else`` final só pega ``legenda``; qualquer outro campo de texto passa
batido em silêncio.
"""

from django.utils.html import escape


def _paragraph(value):
    text = (value or '').strip()
    return f'<p>{escape(text)}</p>' if text else ''


def _table_parts(value):
    """Células de um ``TableBlock`` (dict com ``data``, lista de linhas).

    Tabela vazia, mal formada ou de uma versão anterior do bloco não pode derrubar
    um save — daí checar o formato em vez de confiar nele.
    """
    if not isinstance(value, dict):
        return []

    cells = []
    for row in value.get('data') or []:
        if not isinstance(row, (list, tuple)):
            continue
        for cell in row:
            text = str(cell or '').strip()
            if text:
                cells.append(escape(text))
    return [f'<p>{" ".join(cells)}</p>'] if cells else []


def block_text_parts(block):
    """Fragmentos de HTML com o texto pesquisável de UM bloco do StreamField."""
    block_type = block.block_type
    value = block.value

    # RichTextBlock: o valor já é HTML confiável — o Wagtail converte o
    # contentstate do editor para um subconjunto restrito de tags, então não
    # escapamos (escapar aqui mostraria as tags como texto na busca e no teaser).
    if block_type == 'texto':
        return [str(value)] if value else []

    if block_type == 'titulo':
        level = (value.get('nivel') or 'h2') if isinstance(value, dict) else 'h2'
        text = (value.get('texto') or '').strip() if isinstance(value, dict) else ''
        return [f'<{level}>{escape(text)}</{level}>'] if text else []

    if block_type == 'citacao':
        return [_paragraph(value.get('citacao')), _paragraph(value.get('atribuicao'))]

    if block_type == 'destaque':
        # `texto` é RichTextBlock — HTML, não escapar.
        return [str(value.get('texto') or '')]

    if block_type == 'fonte':
        return [_paragraph(value.get('rotulo'))]

    if block_type == 'tabela':
        return _table_parts(value)

    # Imagem, embed e qualquer bloco futuro que traga legenda.
    if isinstance(value, dict):
        return [_paragraph(value.get('legenda'))]

    return []


def extract_content_from_body(body):
    """HTML consolidado de um ``body`` (StreamValue). ``''`` se estiver vazio."""
    if not body:
        return ''

    parts = []
    for block in body:
        parts.extend(block_text_parts(block))

    return '\n'.join(part for part in parts if part)
