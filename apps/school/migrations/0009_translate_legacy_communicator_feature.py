from django.db import migrations

LEGACY_TITLE = 'Comunicador'
LEGACY_DESCRIPTION = 'Curso de 420 horas para quem quer se profissionalizar na área de comunicação.'
LEGACY_TITLE_EN = 'Communicator'
LEGACY_DESCRIPTION_EN = 'A 420-hour course for people who want to become professionals in communication.'


def translate_legacy_communicator_feature(apps, schema_editor):
    SchoolFeature = apps.get_model('school', 'SchoolFeature')

    features = SchoolFeature.objects.filter(title=LEGACY_TITLE, description=LEGACY_DESCRIPTION)
    for feature in features:
        update_fields = []
        if not feature.title_en:
            feature.title_en = LEGACY_TITLE_EN
            update_fields.append('title_en')
        if not feature.description_en:
            feature.description_en = LEGACY_DESCRIPTION_EN
            update_fields.append('description_en')
        if update_fields:
            feature.save(update_fields=update_fields)


def noop_reverse(apps, schema_editor):
    # Traduções podem ter sido revisadas no admin depois da migração; não apagamos no rollback.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('school', '0008_bilingual_home_content'),
    ]

    operations = [
        migrations.RunPython(translate_legacy_communicator_feature, noop_reverse),
    ]
