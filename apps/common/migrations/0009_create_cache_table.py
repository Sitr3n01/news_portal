"""Cria a tabela usada pelo DatabaseCache (settings.CACHES['default']).

Como migration, e não como passo manual de deploy, para que a tabela exista
automaticamente em dev, no banco de teste, no CI e em produção — o cache é
usado para rate limiting, então a ausência dela derrubaria a recuperação de
senha em vez de apenas degradar o desempenho.

`createcachetable` é idempotente: sai cedo se a tabela já existir, então é
seguro rodar em um banco onde alguém já executou o comando à mão.
"""

from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    call_command(
        'createcachetable',
        'django_cache',
        database=schema_editor.connection.alias,
        verbosity=0,
    )


def drop_cache_table(apps, schema_editor):
    table = schema_editor.connection.ops.quote_name('django_cache')
    schema_editor.execute(f'DROP TABLE IF EXISTS {table}')


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0008_siteextension_social_show_instagram_and_more'),
    ]

    operations = [
        migrations.RunPython(create_cache_table, drop_cache_table),
    ]
