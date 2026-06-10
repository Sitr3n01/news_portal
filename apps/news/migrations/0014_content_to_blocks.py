from django.db import migrations


def content_to_blocks(apps, schema_editor):
    """Converte o HTML existente de cada artigo em um bloco de texto inicial.

    Preserva o conteúdo atual (inclusive iframes legados do YouTube) como o
    primeiro bloco RICH_TEXT, para que artigos antigos continuem renderizando
    igual após a migração para blocos. Idempotente: pula artigos que já têm
    blocos.
    """
    Article = apps.get_model('news', 'Article')
    ArticleBlock = apps.get_model('news', 'ArticleBlock')

    for article in Article.objects.all():
        if article.content and not ArticleBlock.objects.filter(article=article).exists():
            ArticleBlock.objects.create(
                article=article,
                order=0,
                block_type='rich_text',
                rich_text=article.content,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0013_alter_article_content_articleblock'),
    ]

    operations = [
        # Reverso é no-op: não removemos blocos para não perder edições posteriores.
        migrations.RunPython(content_to_blocks, migrations.RunPython.noop),
    ]
