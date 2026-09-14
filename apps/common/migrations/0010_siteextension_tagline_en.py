from django.db import migrations, models

TAGLINE = 'Comunicação que gera resultados'
TAGLINE_EN = 'Communication that drives results'


def fill_tagline_en(apps, schema_editor):
    SiteExtension = apps.get_model('common', 'SiteExtension')
    # Só o slogan real publicado ganha a versão em inglês; um slogan editado no admin fica para quem o editou traduzir
    SiteExtension.objects.filter(tagline=TAGLINE, tagline_en='').update(tagline_en=TAGLINE_EN)


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0009_create_cache_table'),
        # Roda depois da troca dos exemplos, para um banco que tinha o slogan de exemplo já estar com o real
        ('school', '0010_komuniki_real_public_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteextension',
            name='tagline_en',
            field=models.CharField(blank=True, default='', help_text='Opcional. Se vazio, usa o texto em português.', max_length=255, verbose_name='Tagline (EN)'),
        ),
        migrations.RunPython(fill_tagline_en, migrations.RunPython.noop),
    ]
