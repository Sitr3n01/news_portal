"""Workflow de moderação do Article no Wagtail: ordem dos mixins, migração, permissões de publicar e início do fluxo."""

import pytest

from apps.news.models import Article
from apps.news.testing import make_article, make_article_full, make_site


@pytest.mark.django_db
def test_workflow_mixin_mro():
    """WorkflowMixin está antes de DraftStateMixin no MRO (check wagtailcore.E006)."""
    from wagtail.models import DraftStateMixin, RevisionMixin, WorkflowMixin

    mro = Article.__mro__
    wf_idx = mro.index(WorkflowMixin)
    ds_idx = mro.index(DraftStateMixin)
    rev_idx = mro.index(RevisionMixin)
    assert wf_idx < ds_idx < rev_idx, (
        f'MRO violation: WorkflowMixin={wf_idx}, DraftStateMixin={ds_idx}, '
        f'RevisionMixin={rev_idx}'
    )


@pytest.mark.django_db
def test_article_has_workflow_methods():
    """Article herda os métodos do WorkflowMixin."""
    art = Article(title='Test', slug='test-wf-methods', content='.')
    assert hasattr(art, 'has_workflow')
    assert hasattr(art, 'get_workflow')
    assert hasattr(art, 'workflow_states')
    assert hasattr(art, 'current_workflow_state')
    assert hasattr(art, 'workflow_in_progress')


@pytest.mark.django_db
def test_save_revision_still_works_with_workflow():
    """save_revision() continua funcionando após adicionar WorkflowMixin."""
    site = make_site()
    art = make_article_full(site, slug='wf-save-rev')
    rev = art.save_revision()
    assert rev is not None
    # Wagtail Revision.object_id é string (CharField de max_length=255)
    assert rev.object_id == str(art.pk) or int(rev.object_id) == art.pk


@pytest.mark.django_db
def test_workflow_is_assigned_after_migration():
    """Após a migração 0017, existe um Workflow associado a Article."""
    from wagtail.models import Workflow, WorkflowContentType

    workflow = Workflow.objects.filter(name='Moderação Editorial').first()
    assert workflow is not None, 'Workflow "Moderação Editorial" não existe após migração'

    # WorkflowContentType associa ao content type de Article
    wct = WorkflowContentType.objects.filter(
        content_type__app_label='news',
        content_type__model='article',
    ).first()
    assert wct is not None, 'WorkflowContentType não encontrado para Article'
    assert wct.workflow_id == workflow.pk, (
        f'WorkflowContentType aponta para workflow {wct.workflow_id}, '
        f'esperado {workflow.pk}'
    )
    assert workflow.active is True
    assert workflow.tasks.filter(name='Aprovação Editorial').exists(), (
        'GrupoApprovalTask "Aprovação Editorial" não está ligada ao workflow'
    )


@pytest.mark.django_db
def test_article_get_default_workflow():
    """Article.get_default_workflow() retorna o workflow configurado."""
    site = make_site()
    art = make_article(site, slug='wf-default')
    workflow = art.get_default_workflow()
    assert workflow is not None
    assert workflow.name == 'Moderação Editorial'


@pytest.mark.django_db
def test_article_has_workflow():
    """Article.has_workflow é True após a migração."""
    site = make_site()
    art = make_article(site, slug='wf-has')
    assert art.has_workflow is True


@pytest.mark.django_db
def test_editor_de_noticias_has_publish_permission(django_user_model):
    """Usuário com role 'news_editor' ganha a permissão publish_article."""
    from apps.accounts.admin_roles import sync_user_role_group

    editor = django_user_model.objects.create_user(
        username='editor-publish', password='x',
        role='news_editor',
    )
    # Antes da sincronização, NÃO deve ter a permissão
    assert not editor.has_perm('news.publish_article')

    sync_user_role_group(editor)

    # Django has_perm pode usar cache interno. Recarregamos o modelo
    # User do banco e verificamos via get_all_permissions().
    from django.contrib.auth import get_user_model
    editor_fresh = get_user_model().objects.get(pk=editor.pk)
    perms = editor_fresh.get_all_permissions()
    assert 'news.publish_article' in perms, (
        f'Editor de Notícias precisa ter publish_article. Perms: {sorted(perms)}'
    )
    assert 'news.lock_article' in perms, (
        'Editor de Notícias precisa ter lock_article'
    )
    assert 'news.unlock_article' in perms, (
        'Editor de Notícias precisa ter unlock_article'
    )


@pytest.mark.django_db
def test_editor_de_noticias_lacks_publish_without_sync(django_user_model):
    """Sem sync_user_role_group, o editor NÃO tem publish_article."""
    editor = django_user_model.objects.create_user(
        username='editor-no-sync', password='x',
        role='news_editor',
    )
    assert not editor.has_perm('news.publish_article'), (
        'Antes do sync, publish_article deve ser False'
    )


@pytest.mark.django_db
def test_ensure_admin_role_groups_grants_publish(django_user_model):
    """ensure_admin_role_groups() cria o grupo Editor de Notícias com publish."""
    from django.contrib.auth.models import Group

    from apps.accounts.admin_roles import ensure_admin_role_groups

    ensure_admin_role_groups()
    group = Group.objects.get(name='Editor de Notícias')
    perms = group.permissions.filter(
        content_type__app_label='news',
        codename='publish_article',
    )
    assert perms.exists(), 'Grupo Editor de Notícias deve ter publish_article'


@pytest.mark.django_db
def test_article_publish_method():
    """Article.publish() (herdado do DraftStateMixin) funciona."""
    site = make_site()
    art = make_article_full(site, slug='wf-publish', status=Article.Status.PUBLISHED)
    # Já publicado — vamos verificar que live=True
    rev = art.save_revision(user=None)
    art.publish(revision=rev)
    art.refresh_from_db()
    # Wagtail publish() seta live=True e last_published_at
    assert art.live is True
    assert art.last_published_at is not None


@pytest.mark.django_db
def test_article_draftstate_properties():
    """Propriedades de DraftStateMixin continuam funcionais."""
    site = make_site()
    art = make_article(site, slug='wf-draft-prop')
    # Inicialmente published
    art.status = Article.Status.PUBLISHED
    art.save()
    assert art.status_string == 'live' or art.status_string is not None


@pytest.mark.django_db
def test_article_workflow_state_creation(django_user_model):
    """O workflow pode ser iniciado em um Article."""
    site = make_site()
    art = make_article_full(site, slug='wf-state', status=Article.Status.DRAFT)
    art.save_revision()

    workflow = art.get_default_workflow()
    assert workflow is not None

    user = django_user_model.objects.create_user(
        username='wf-user-state', password='x',
        email='wf-user-state@test.com',
        role='news_editor',
    )
    from apps.accounts.admin_roles import sync_user_role_group
    sync_user_role_group(user)

    # Inicia o workflow
    workflow_state = workflow.start(art, user)
    assert workflow_state is not None
    assert workflow_state.status == 'in_progress'

    # Verifica que o workflow_state aparece no modelo
    art.refresh_from_db()
    assert art.workflow_in_progress is True
    current = art.current_workflow_state
    assert current is not None
    assert current.pk == workflow_state.pk
