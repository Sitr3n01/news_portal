"""Troca valores de exemplo semeados por migrações pelos dados reais publicados da Komuniki.

Um campo só muda quando ainda guarda exatamente um valor semeado conhecido; o que foi
editado no admin fica como está. Os valores reais são os do site público consultado em
12/09/2026, registrados em scripts/preview/komuniki-public-content.json.
"""
from django.db import migrations

KOMUNIKI_SITE_ID = 1
KOMUNIKI_ADDRESS = 'QI 11 Bloco A Comércio Local salas 102/104 Guará 1\nBrasília DF, 70274-530, BR'

# Campo: (valores semeados que podem ser trocados, valor real).
# Os exemplos vêm de common.0002. komunikiagencia e o canal por ID vêm de school.0007,
# mas o site público usa os perfis da escola.
SITE_EXTENSION_REAL_DATA = {
    'tagline': ({'Moldando o futuro, inspirando mentes.'}, 'Comunicação que gera resultados'),
    'primary_email': ({'contato@exemplo.edu.br'}, 'komunikicomunicacao@gmail.com'),
    'phone_number': ({'(11) 99999-9999'}, '(61) 92003-8428'),
    'address': ({'Rua da Educação, 123, São Paulo - SP'}, KOMUNIKI_ADDRESS),
    'facebook_url': ({'https://facebook.com/exemplo'}, ''),
    'instagram_url': (
        {'https://instagram.com/exemplo', 'https://www.instagram.com/komunikiagencia/'},
        'https://www.instagram.com/komunikiescola/',
    ),
    'youtube_url': (
        {'https://youtube.com/exemplo', 'https://www.youtube.com/channel/UCidKmbl0ENPRl5vy70-GwfA'},
        'https://youtube.com/@escolakomuniki?si=8AR-FzPrJh8QCbu3',
    ),
}
SEEDED_SITE_NAME = 'Escola e Portal de Notícias'
SOCIAL_SECTION_TEST_TITLE = 'TESTE FASE 11 — Redes Sociais Kelly'
SOCIAL_SECTION_TITLE = 'Acompanhe a Komuniki nas redes'


def apply_real_public_data(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    SiteExtension = apps.get_model('common', 'SiteExtension')
    SchoolFeature = apps.get_model('school', 'SchoolFeature')

    Site.objects.filter(pk=KOMUNIKI_SITE_ID, name=SEEDED_SITE_NAME).update(name='Komuniki')

    for extension in SiteExtension.objects.filter(site_id=KOMUNIKI_SITE_ID):
        changed = []
        for field, (seeded, real) in SITE_EXTENSION_REAL_DATA.items():
            if getattr(extension, field) in seeded:
                setattr(extension, field, real)
                changed.append(field)
        # A seção social com o título de teste é dado de teste: volta ao título padrão e fica
        # desligada, como na Home pública
        if extension.social_section_title == SOCIAL_SECTION_TEST_TITLE:
            extension.social_section_title = SOCIAL_SECTION_TITLE
            extension.social_section_enabled = False
            changed += ['social_section_title', 'social_section_enabled']
        if changed:
            extension.save(update_fields=changed)

    # A Home pública mostra três diferenciais; o cartão do Jovem Comunicador fica guardado e desativado
    SchoolFeature.objects.filter(
        site_id=KOMUNIKI_SITE_ID, placement='trust', title='Projeto Jovem Comunicador', is_active=True,
    ).update(is_active=False)


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0009_create_cache_table'),
        ('school', '0009_translate_legacy_communicator_feature'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        # Sem volta: restaurar os dados de exemplo não teria utilidade
        migrations.RunPython(apply_real_public_data, migrations.RunPython.noop),
    ]
