"""Converte os blocos legados para Article.body e só então derruba ArticleBlock.

⚠️  IRREVERSÍVEL. O `DeleteModel` no fim apaga `news_articleblock` para sempre.
⚠️  Antes de rodar contra produção, execute nesta ordem (docs/technical/DEPLOY.md):
⚠️      1. manage.py migrate_featured_images --apply
⚠️      2. manage.py migrate_block_media --apply
⚠️      3. manage.py audit_article_blocks        (tem de acusar cobertura total)
⚠️      4. manage.py migrate
⚠️  O passo 2 é o que cria as `cms_media.Image` correspondentes às `MediaFile` dos
⚠️  blocos de imagem. Sem ele, `convert_blocks_to_streamfield` não tem para onde
⚠️  apontar as imagens e cada bloco de imagem é rebaixado a parágrafo de legenda.

Por que a conversão vive DENTRO desta migration, e não numa migration própria:
esta é a última posição do histórico em que a tabela `news_articleblock` ainda
existe. Uma migration posterior (0024+) rodaria depois do `DeleteModel` e não
encontraria mais nada; uma anterior quebraria o histórico dos bancos que já
aplicaram a 0021 (`InconsistentMigrationHistory`). Bancos de desenvolvimento que
já passaram por aqui simplesmente não re-executam nada.

Sem I/O de arquivo, de propósito: criar `Image` significa ler e reescrever arquivo
no MEDIA_ROOT, e falha no meio de uma migration deixa o banco a meio caminho. Esse
trabalho fica no comando `migrate_block_media`, que roda antes e é repetível.
"""

from django.db import migrations

from apps.news.legacy_blocks import build_stream_data, group_by_article


def convert_blocks_to_streamfield(apps, schema_editor):
    """Monta `Article.body` a partir dos ArticleBlock ordenados de cada artigo.

    Só escreve em artigos cujo `body` ainda está vazio: quem já foi editado no
    Wagtail tem body autoritativo e não pode ser atropelado pelo legado.

    `content` NÃO é tocado aqui. Ele é a rede de segurança que mantém o texto no ar
    caso algo dê errado; a migration 0024 o reconstrói a partir do novo `body`, e
    só quando a extração render conteúdo.
    """
    Article = apps.get_model('news', 'Article')
    ArticleBlock = apps.get_model('news', 'ArticleBlock')
    Image = apps.get_model('cms_media', 'Image')
    db_alias = schema_editor.connection.alias

    blocks = list(
        ArticleBlock.objects.using(db_alias)
        .order_by('article_id', 'order', 'id')
        .values('id', 'article_id', 'order', 'block_type', 'rich_text', 'media_id', 'caption', 'embed_url')
    )
    if not blocks:
        return

    image_pk_by_media_id = dict(
        Image.objects.using(db_alias)
        .filter(legacy_media_file_id__isnull=False)
        .values_list('legacy_media_file_id', 'pk')
    )

    def image_pk_for(media_id):
        return image_pk_by_media_id.get(media_id)

    grouped = group_by_article(blocks)

    # `body` volta do banco como StreamValue (StreamField.from_db_value), então o
    # teste é de veracidade e não comparação com string: StreamValue vazio, '' e
    # NULL são todos falsos. Body não vazio = artigo já editado no Wagtail, e o
    # legado não pode atropelar isso.
    existing_body = dict(
        Article.objects.using(db_alias)
        .filter(pk__in=grouped)
        .values_list('pk', 'body')
    )

    for article_id, article_blocks in grouped.items():
        if existing_body.get(article_id):
            continue

        stream = build_stream_data(article_blocks, image_pk_for)
        if not stream:
            continue

        # Lista de dicts crua, NÃO json.dumps(): quando o valor não é StreamValue,
        # StreamField.get_prep_value delega ao JSONField, que já serializa. Passar
        # string aqui gravaria JSON dentro de JSON.
        Article.objects.using(db_alias).filter(pk=article_id).update(body=stream)


def noop_reverse(apps, schema_editor):
    """Sem volta: o `DeleteModel` abaixo já é irreversível, e limpar o `body`
    convertido apagaria também o que os editores escreveram depois."""


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0020_alter_article_content_alter_article_slug_and_more'),
        ('cms_media', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(convert_blocks_to_streamfield, noop_reverse),
        migrations.DeleteModel(
            name='ArticleBlock',
        ),
    ]
