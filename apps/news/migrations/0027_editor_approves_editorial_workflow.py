from django.db import migrations

TASK_NAME = 'Aprovação Editorial'
EDITOR_GROUP = 'Editor de Notícias'


def _add_editor_as_approver(apps, schema_editor):
    """Editor de Notícias passa a aprovar a etapa "Aprovação Editorial".

    Migração só de DADOS — nenhuma tabela ou coluna muda. Até aqui só o
    "Administrador Geral" aprovava; o repórter enviava para revisão e o editor,
    que tem ``news.publish_article``, não conseguia aprovar nem publicar a
    matéria em revisão (o Wagtail trava a edição para quem não é aprovador da
    etapa). O Administrador Geral continua aprovador.

    Idempotente: se a tarefa não existir (foi removida pelo painel), nada é
    recriado; se o grupo já for aprovador, nada muda.
    """
    GroupApprovalTask = apps.get_model('wagtailcore', 'GroupApprovalTask')
    Group = apps.get_model('auth', 'Group')

    task = GroupApprovalTask.objects.filter(name=TASK_NAME).first()
    if task is None:
        return
    editor_group, _ = Group.objects.get_or_create(name=EDITOR_GROUP)
    task.groups.add(editor_group)


def _remove_editor_as_approver(apps, schema_editor):
    """Reverso: tira só o Editor de Notícias da etapa; o resto fica como estava."""
    GroupApprovalTask = apps.get_model('wagtailcore', 'GroupApprovalTask')
    Group = apps.get_model('auth', 'Group')

    task = GroupApprovalTask.objects.filter(name=TASK_NAME).first()
    editor_group = Group.objects.filter(name=EDITOR_GROUP).first()
    if task is not None and editor_group is not None:
        task.groups.remove(editor_group)


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('news', '0026_article_news_article_site_status_pub'),
        ('wagtailcore', '0097_baselogentry_uuid_action_timestamp_indexes'),
    ]

    operations = [
        migrations.RunPython(_add_editor_as_approver, _remove_editor_as_approver),
    ]
