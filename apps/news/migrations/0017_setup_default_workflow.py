from django.db import migrations


def _get_or_create_workflow(apps, schema_editor):
    """Cria o workflow padrão para moderação de artigos.

    Fase 8 — um único workflow "Moderação Editorial" com uma tarefa de
    aprovação em grupo (GroupApprovalTask) que requer aprovação do
    grupo "Administrador Geral".

    Idempotente: não duplica o workflow, a tarefa, a associação entre
    eles ou a associação ao content-type se já existirem.
    """
    Workflow = apps.get_model('wagtailcore', 'Workflow')
    WorkflowTask = apps.get_model('wagtailcore', 'WorkflowTask')
    WorkflowContentType = apps.get_model('wagtailcore', 'WorkflowContentType')
    GroupApprovalTask = apps.get_model('wagtailcore', 'GroupApprovalTask')
    Task = apps.get_model('wagtailcore', 'Task')
    Group = apps.get_model('auth', 'Group')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    # Garante que o ContentType para article existe.
    # Durante o setup de banco de teste, ContentTypes podem ainda não ter
    # sido populados pelo post_migrate do contenttypes — forçamos a criação.
    article_ct, _ = ContentType.objects.get_or_create(
        app_label='news',
        model='article',
    )

    # 1. Workflow "Moderação Editorial"
    workflow, created = Workflow.objects.get_or_create(
        name='Moderação Editorial',
        defaults={'active': True},
    )
    if not created and not workflow.active:
        workflow.active = True
        workflow.save(update_fields=['active'])

    # 2. Grupo "Administrador Geral"
    admin_group, _ = Group.objects.get_or_create(name='Administrador Geral')

    # 3. GroupApprovalTask
    task_ct = ContentType.objects.get_for_model(GroupApprovalTask, for_concrete_model=False)
    task, task_created = Task.objects.get_or_create(
        name='Aprovação Editorial',
        content_type=task_ct,
        defaults={'active': True},
    )
    if not task_created and not task.active:
        task.active = True
        task.save(update_fields=['active'])

    # No histórico, a herança multi-tabela pode não estar resolvida.
    # Garantimos que a linha de GroupApprovalTask existe.
    try:
        group_task = GroupApprovalTask.objects.get(pk=task.pk)
    except GroupApprovalTask.DoesNotExist:
        group_task = GroupApprovalTask(task_ptr=task)
        group_task.save_base(raw=True)
    group_task.groups.add(admin_group)

    # 4. WorkflowTask (ordenação)
    WorkflowTask.objects.get_or_create(
        workflow=workflow,
        task=task,
        defaults={'sort_order': 0},
    )

    # 5. WorkflowContentType — associa o workflow ao model Article
    wct, wct_created = WorkflowContentType.objects.get_or_create(
        content_type=article_ct,
        defaults={'workflow': workflow},
    )
    if not wct_created and wct.workflow != workflow:
        wct.workflow = workflow
        wct.save(update_fields=['workflow'])


def _remove_default_workflow(apps, schema_editor):
    """Reverso: remove o workflow padrão e suas associações."""
    Workflow = apps.get_model('wagtailcore', 'Workflow')
    WorkflowTask = apps.get_model('wagtailcore', 'WorkflowTask')
    WorkflowContentType = apps.get_model('wagtailcore', 'WorkflowContentType')
    Task = apps.get_model('wagtailcore', 'Task')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    article_ct = ContentType.objects.filter(app_label='news', model='article').first()
    if article_ct:
        WorkflowContentType.objects.filter(content_type=article_ct).delete()

    WorkflowTask.objects.filter(workflow__name='Moderação Editorial').delete()
    Task.objects.filter(name='Aprovação Editorial').delete()
    Workflow.objects.filter(name='Moderação Editorial').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0016_alter_article_body'),
        ('wagtailcore', '0098_userprofile'),
    ]

    operations = [
        migrations.RunPython(_get_or_create_workflow, _remove_default_workflow),
    ]

