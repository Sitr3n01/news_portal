from django.db import migrations


def ensure_siteextension_for_all_sites(apps, schema_editor):
    """Garante uma linha de SiteExtension para cada Site.

    A seed inicial (0002_default_site) só cria a configuração do site #1, então
    portais adicionais ficavam sem onde definir o remetente da newsletter — a
    causa do "não acho onde alterar o e-mail". get_or_create é idempotente e
    nunca sobrescreve dados já preenchidos.
    """
    Site = apps.get_model('sites', 'Site')
    SiteExtension = apps.get_model('common', 'SiteExtension')
    for site in Site.objects.all():
        SiteExtension.objects.get_or_create(site=site)


def noop(apps, schema_editor):
    # Reverso intencionalmente vazio: não apagamos configurações já criadas.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0005_update_newsletter_sender_help_text'),
        ('sites', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(ensure_siteextension_for_all_sites, noop),
    ]
