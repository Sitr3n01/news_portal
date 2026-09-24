"""Permissões das ações em massa do Django admin.

O Django só esconde uma ação por permissão quando ela declara
``permissions=``; sem isso, quem só pode ver a lista recebe a ação no seletor
e consegue dispará-la com um POST montado à mão (``index``, ``action``,
``_selected_action``). Cobrem: toda ação customizada declara as permissões,
quem só vê a lista não recebe nem consegue rodar as ações que alteram dados,
quem pode alterar continua rodando, os admins só de superusuário seguem
fechados para a equipe, e a exportação de e-mails da newsletter fica restrita
a superusuários.
"""

import pytest
from django.contrib import admin
from django.contrib.auth import get_permission_codename, get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.contact.models import ContactInquiry
from apps.hiring.models import Application, Department, JobPosting
from apps.news.models import Article, Comment, NewsletterSubscription
from apps.school.models import Testimonial as SchoolTestimonial
from apps.social.models import Platform, SocialAccount, SocialPost


@pytest.fixture
def root(make_panel_user):
    return make_panel_user('al_root', role=CustomUser.Role.SUPER_ADMIN, is_staff=True, is_superuser=True)


def _inquiry(site, **fields):
    return ContactInquiry.objects.create(site=site, name='Visitante', email='visitante@example.com', message='Oi', **fields)


def _subscription(site, **fields):
    return NewsletterSubscription.objects.create(site=site, email='assinante@example.com', **fields)


def _comment(site, **fields):
    article = Article.objects.create(
        title='Artigo', slug='artigo', excerpt='Resumo', content='Conteúdo',
        site=site, status=Article.Status.PUBLISHED,
    )
    author = get_user_model().objects.create_user(username='al_leitor', email='leitor@example.com', password='x')
    return Comment.objects.create(article=article, user=author, content='Comentário', **fields)


def _testimonial(site, **fields):
    return SchoolTestimonial.objects.create(site=site, name='Mãe de aluno', quote='Ótima escola.', **fields)


def _account(site, **fields):
    return SocialAccount.objects.create(
        site=site, platform=Platform.INSTAGRAM, display_name='Komuniki IG', username='komuniki', **fields,
    )


def _post(site, **fields):
    return SocialPost.objects.create(
        account=_account(site), permalink='https://www.instagram.com/p/abc/', published_at=timezone.now(), **fields,
    )


def _job(site, **fields):
    department = Department.objects.create(site=site, name='Pedagógico', slug='pedagogico')
    return JobPosting.objects.create(
        site=site, department=department, title='Professor', slug='professor', description='x', requirements='y', **fields,
    )


def _application(site, **fields):
    return Application.objects.create(
        job=_job(site), first_name='Ana', last_name='Silva', email='ana@example.com', phone='11999990000',
        resume='hiring/resumes/cv.pdf', **fields,
    )


# (fábrica, ação, campo alterado, valor antes, valor depois)
ACTION_CASES = [
    pytest.param(_inquiry, 'mark_resolved', 'status', 'new', 'archived', id='contato-arquivar'),
    pytest.param(_subscription, 'deactivate_subscriptions', 'is_active', True, False, id='newsletter-desativar'),
    pytest.param(_subscription, 'activate_subscriptions', 'is_active', False, True, id='newsletter-reativar'),
    pytest.param(_comment, 'approve_comments', 'is_active', False, True, id='comentario-aprovar'),
    pytest.param(_comment, 'hide_comments', 'is_active', True, False, id='comentario-ocultar'),
    pytest.param(_account, 'activate_accounts', 'is_active', False, True, id='conta-ativar'),
    pytest.param(_account, 'deactivate_accounts', 'is_active', True, False, id='conta-desativar'),
    pytest.param(_post, 'make_visible', 'is_visible', False, True, id='post-exibir'),
    pytest.param(_post, 'make_hidden', 'is_visible', True, False, id='post-ocultar'),
]

# Admins com SuperuserOnlyAdminMixin: lá ``has_change_permission`` é o próprio
# superusuário, então a equipe nem abre a lista, com ou sem ``change_*``.
SUPERUSER_ONLY_CASES = [
    pytest.param(_testimonial, 'feature_selected', 'is_featured', False, True, id='depoimento-destacar'),
    pytest.param(_testimonial, 'unfeature_selected', 'is_featured', True, False, id='depoimento-tirar-destaque'),
    pytest.param(_job, 'open_postings', 'status', 'draft', 'open', id='vaga-abrir'),
    pytest.param(_job, 'close_postings', 'status', 'open', 'closed', id='vaga-fechar'),
    pytest.param(_application, 'mark_reviewing', 'status', 'received', 'reviewing', id='candidatura-em-analise'),
    pytest.param(_application, 'mark_accepted', 'status', 'received', 'accepted', id='candidatura-aceitar'),
    pytest.param(_application, 'mark_rejected', 'status', 'received', 'rejected', id='candidatura-rejeitar'),
]


def _changelist(model):
    return reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist')


def _staff_with(make_panel_user, model, *perms):
    """Equipe sem cargo, só com as permissões indicadas no modelo."""
    user = make_panel_user(f'al_{"_".join(perms)}', is_staff=True)
    codenames = [get_permission_codename(perm, model._meta) for perm in perms]
    user.user_permissions.add(*Permission.objects.filter(content_type__app_label=model._meta.app_label, codename__in=codenames))
    return user


def _offered_actions(response):
    action_form = response.context['action_form']
    if action_form is None:
        return set()
    return {name for name, _label in action_form.fields['action'].choices}


def _run_action(client, model, action, obj):
    return client.post(_changelist(model), {
        'index': '0',
        'action': action,
        'select_across': '0',
        '_selected_action': [obj.pk],
    })


def test_every_custom_action_declares_permissions():
    """Ação sem ``permissions=`` aparece para quem só pode ver a lista."""
    checked, missing = [], []
    for model, model_admin in admin.site._registry.items():
        if not model.__module__.startswith('apps.'):
            continue
        for action in model_admin.actions or ():
            func, name, _description = model_admin.get_action(action)
            checked.append(f'{model._meta.label}.{name}')
            if not getattr(func, 'allowed_permissions', None):
                missing.append(checked[-1])

    assert 'contact.ContactInquiry.mark_resolved' in checked
    assert 'hiring.Application.mark_rejected' in checked
    assert missing == []


@pytest.mark.django_db
@pytest.mark.parametrize(('make', 'action', 'field', 'before', 'after'), ACTION_CASES)
def test_view_only_staff_does_not_get_the_action(client, make_panel_user, current_site, make, action, field, before, after):
    """Só com ``view_*`` a ação não entra no seletor nem na barra de seleção."""
    obj = make(current_site, **{field: before})
    client.force_login(_staff_with(make_panel_user, type(obj), 'view'))

    response = client.get(_changelist(type(obj)))

    assert response.status_code == 200
    assert action not in _offered_actions(response)
    assert f'data-nr-action="{action}"' not in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(('make', 'action', 'field', 'before', 'after'), ACTION_CASES)
def test_view_only_staff_cannot_run_the_action_by_post(client, make_panel_user, current_site, make, action, field, before, after):
    """O POST montado à mão não altera nada: sem ação disponível o Django só redesenha a lista."""
    obj = make(current_site, **{field: before})
    client.force_login(_staff_with(make_panel_user, type(obj), 'view'))

    response = _run_action(client, type(obj), action, obj)

    assert response.status_code == 200
    obj.refresh_from_db()
    assert getattr(obj, field) == before


@pytest.mark.django_db
@pytest.mark.parametrize(('make', 'action', 'field', 'before', 'after'), ACTION_CASES)
def test_staff_with_change_permission_runs_the_action(client, make_panel_user, current_site, make, action, field, before, after):
    """Com ``change_*`` a ação aparece e o mesmo POST altera o registro."""
    obj = make(current_site, **{field: before})
    client.force_login(_staff_with(make_panel_user, type(obj), 'view', 'change'))

    assert action in _offered_actions(client.get(_changelist(type(obj))))

    response = _run_action(client, type(obj), action, obj)

    assert response.status_code == 302
    obj.refresh_from_db()
    assert getattr(obj, field) == after


@pytest.mark.django_db
@pytest.mark.parametrize(('make', 'action', 'field', 'before', 'after'), SUPERUSER_ONLY_CASES)
def test_superuser_only_admin_stays_closed_to_staff(client, make_panel_user, current_site, make, action, field, before, after):
    """Nem com ``view_*`` e ``change_*`` a equipe lista ou roda a ação."""
    obj = make(current_site, **{field: before})
    client.force_login(_staff_with(make_panel_user, type(obj), 'view', 'change'))

    assert client.get(_changelist(type(obj))).status_code == 403
    assert _run_action(client, type(obj), action, obj).status_code == 403
    obj.refresh_from_db()
    assert getattr(obj, field) == before


@pytest.mark.django_db
@pytest.mark.parametrize(('make', 'action', 'field', 'before', 'after'), SUPERUSER_ONLY_CASES)
def test_superuser_runs_the_action(client, root, current_site, make, action, field, before, after):
    """O ``permissions=['change']`` não tira a ação do superusuário."""
    obj = make(current_site, **{field: before})
    client.force_login(root)

    assert action in _offered_actions(client.get(_changelist(type(obj))))

    response = _run_action(client, type(obj), action, obj)

    assert response.status_code == 302
    obj.refresh_from_db()
    assert getattr(obj, field) == after


@pytest.mark.django_db
def test_action_outside_the_allowed_ones_is_rejected(client, make_panel_user, current_site):
    """Com outra ação disponível (remover), o formulário de ações recusa a que falta permissão."""
    inquiry = _inquiry(current_site, status='new')
    client.force_login(_staff_with(make_panel_user, ContactInquiry, 'view', 'delete'))

    assert _offered_actions(client.get(_changelist(ContactInquiry))) == {'', 'delete_selected'}

    response = _run_action(client, ContactInquiry, 'mark_resolved', inquiry)

    assert response.status_code == 302
    inquiry.refresh_from_db()
    assert inquiry.status == 'new'


@pytest.mark.django_db
def test_newsletter_export_is_superuser_only(client, make_panel_user, current_site):
    """O Editor de Notícias altera inscrições, mas não exporta a lista de e-mails."""
    subscription = _subscription(current_site)
    client.force_login(make_panel_user('al_editor', role=CustomUser.Role.NEWS_EDITOR, is_staff=True))

    offered = _offered_actions(client.get(_changelist(NewsletterSubscription)))
    assert 'deactivate_subscriptions' in offered
    assert 'export_emails' not in offered

    response = _run_action(client, NewsletterSubscription, 'export_emails', subscription)

    assert response.status_code == 302
    assert 'assinante@example.com' not in response.content.decode()


@pytest.mark.django_db
def test_newsletter_export_works_for_superuser(client, root, current_site):
    subscription = _subscription(current_site)
    client.force_login(root)

    assert 'export_emails' in _offered_actions(client.get(_changelist(NewsletterSubscription)))

    response = _run_action(client, NewsletterSubscription, 'export_emails', subscription)

    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv'
    assert 'assinante@example.com' in response.content.decode()
