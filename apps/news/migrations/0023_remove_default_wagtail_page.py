from django.db import migrations


def remove_default_wagtail_page(apps, schema_editor):
    """Remove a página semente criada pela própria instalação do Wagtail.

    Este projeto nunca usa a árvore de Páginas do Wagtail para conteúdo real —
    Article/Category/Tag/SiteExtension/NewsHomeConfig são todos Snippets, e
    nenhuma URL pública é roteada via wagtail_urls (config/urls.py só monta
    /cms/ e /documents/). A página "Welcome to your new Wagtail site!" é só
    o dado padrão do Wagtail, órfã, sem nenhum uso no projeto.

    Não remove a página Root (depth=1) — só o filho semente (depth=2).
    """
    Page = apps.get_model('wagtailcore', 'Page')
    Page.objects.filter(
        depth=2,
        slug='home',
        title='Welcome to your new Wagtail site!',
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0022_newshomeconfig'),
        ('wagtailcore', '0098_userprofile'),
    ]

    operations = [
        migrations.RunPython(remove_default_wagtail_page, migrations.RunPython.noop),
    ]
