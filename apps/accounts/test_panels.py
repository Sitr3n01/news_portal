"""Testes da camada de autorização dos painéis (apps.accounts.panels).

Funções puras e checagens de permissão — sem views. Se algo aqui quebrar, o
problema é a REGRA de acesso, não a tela.
"""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import reverse

from apps.accounts import panels
from apps.accounts.models import CustomUser


@pytest.fixture
def rf_request():
    request = RequestFactory().get('/entrar/')
    return request


# ── Portões ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_can_access_admin_requires_staff_and_active(make_panel_user):
    staff = make_panel_user('gate_staff', role=CustomUser.Role.SCHOOL_ADMIN, is_staff=True)
    assert panels.can_access_admin(staff) is True

    sem_staff = make_panel_user('gate_sem_staff', role=CustomUser.Role.SCHOOL_ADMIN)
    assert panels.can_access_admin(sem_staff) is False

    inativo = make_panel_user('gate_inativo', role=CustomUser.Role.SCHOOL_ADMIN, is_staff=True, is_active=False)
    assert panels.can_access_admin(inativo) is False


@pytest.mark.django_db
def test_can_access_cms_matches_wagtail_permission(make_panel_user):
    editor = make_panel_user('gate_editor', role=CustomUser.Role.NEWS_EDITOR)
    assert editor.has_perm('wagtailadmin.access_admin') is True
    assert panels.can_access_cms(editor) is True

    leitor = make_panel_user('gate_leitor', role=CustomUser.Role.READER)
    assert panels.can_access_cms(leitor) is False


@pytest.mark.django_db
def test_inactive_superuser_has_no_panels(make_panel_user):
    """Regressão: admin_nav.can() devolveria True aqui (curto-circuita em
    is_superuser), o que criaria laço de redirecionamento no login."""
    user = make_panel_user('super_inativo', role=CustomUser.Role.SUPER_ADMIN,
                           is_staff=True, is_superuser=True, is_active=False)
    assert panels.available_panels(user) == []
    assert panels.can_access_admin(user) is False
    assert panels.can_access_cms(user) is False


def test_anonymous_user_has_no_panels():
    anon = AnonymousUser()
    assert panels.available_panels(anon) == []
    assert panels.can_access_admin(anon) is False
    assert panels.can_access_cms(anon) is False
    assert panels.default_panel(anon) is None


@pytest.mark.django_db
@pytest.mark.parametrize(('role', 'is_staff', 'esperado'), [
    (CustomUser.Role.READER, False, []),
    (CustomUser.Role.REPORTER, False, [panels.PANEL_CMS]),
    (CustomUser.Role.NEWS_EDITOR, False, [panels.PANEL_CMS]),
    (CustomUser.Role.SCHOOL_ADMIN, True, [panels.PANEL_ADMIN]),
    (CustomUser.Role.SCHOOL_ADMIN, False, []),
    (CustomUser.Role.HIRING_MANAGER, False, []),
    (CustomUser.Role.SUPER_ADMIN, True, [panels.PANEL_CMS, panels.PANEL_ADMIN]),
])
def test_available_panels_per_role(make_panel_user, role, is_staff, esperado):
    user = make_panel_user(f'matriz_{role}_{is_staff}', role=role, is_staff=is_staff)
    assert panels.available_panels(user) == esperado


@pytest.mark.django_db
def test_superuser_reaches_both_panels(make_panel_user):
    user = make_panel_user('root', is_staff=True, is_superuser=True)
    assert panels.available_panels(user) == [panels.PANEL_CMS, panels.PANEL_ADMIN]


@pytest.mark.django_db
def test_default_panel_is_none_when_zero_or_two_panels(make_panel_user):
    leitor = make_panel_user('def_leitor', role=CustomUser.Role.READER)
    assert panels.default_panel(leitor) is None

    repórter = make_panel_user('def_reporter', role=CustomUser.Role.REPORTER)
    assert panels.default_panel(repórter) == panels.PANEL_CMS

    root = make_panel_user('def_root', is_staff=True, is_superuser=True)
    assert panels.default_panel(root) is None


# ── URLs ───────────────────────────────────────────────────────────────────

def test_panel_url_uses_reverse_not_literals():
    assert panels.panel_url(panels.PANEL_CMS) == reverse('wagtailadmin_home')
    assert panels.panel_url(panels.PANEL_ADMIN) == reverse('admin:index')


def test_panel_roots_always_end_with_slash():
    for panel in panels.PANEL_ORDER:
        assert panels.panel_root(panel).endswith('/')


def test_panel_for_url_classifies_panel_roots():
    assert panels.panel_for_url('/cms/') == panels.PANEL_CMS
    assert panels.panel_for_url('/cms/pages/12/edit/') == panels.PANEL_CMS
    assert panels.panel_for_url('/admin/') == panels.PANEL_ADMIN
    assert panels.panel_for_url('/admin/accounts/customuser/') == panels.PANEL_ADMIN


def test_panel_for_url_rejects_lookalike_prefixes():
    """Sem a normalização de barra final, estes casariam com /admin/ e /cms/."""
    assert panels.panel_for_url('/administracao/') is None
    assert panels.panel_for_url('/adminfoo') is None
    assert panels.panel_for_url('/cmsx/') is None


def test_panel_for_url_handles_absolute_same_host_url():
    assert panels.panel_for_url('https://exemplo.com.br/admin/settings/') == panels.PANEL_ADMIN


def test_panel_for_url_returns_none_for_public_urls():
    for url in ('/news/', '/documents/1/arquivo.pdf', '/', '/contact/'):
        assert panels.panel_for_url(url) is None


def test_admin_guides_url_classified_as_admin_panel():
    """/admin/guias/escola/ é rota de topo embrulhada em admin_view."""
    assert panels.panel_for_url(reverse('admin_school_guide')) == panels.PANEL_ADMIN


def test_is_auth_path_blocks_login_and_logout_urls():
    for url in ('/entrar/', '/sair/', '/accounts/login/', '/accounts/logout/',
                '/admin/login/', '/admin/logout/', '/cms/login/', '/cms/logout/'):
        assert panels.is_auth_path(url) is True, url

    for url in ('/news/', '/cms/pages/', '/admin/accounts/'):
        assert panels.is_auth_path(url) is False, url


# ── Segurança do next ──────────────────────────────────────────────────────

@pytest.mark.parametrize('url', [
    'https://evil.com/',
    '//evil.com/',
    r'https:/\evil.com/',
    'http://evil.com/admin/',
])
def test_is_safe_next_rejects_external_destinations(rf_request, url):
    assert panels.is_safe_next(url, rf_request) is False


@pytest.mark.parametrize('url', ['/news/', '/cms/pages/', '/admin/'])
def test_is_safe_next_accepts_internal_paths(rf_request, url):
    assert panels.is_safe_next(url, rf_request) is True


# ── Destino pós-login ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_post_login_target_honors_public_next(make_panel_user, rf_request):
    leitor = make_panel_user('alvo_leitor', role=CustomUser.Role.READER)
    assert panels.post_login_target(leitor, rf_request, next_url='/news/artigo/') == '/news/artigo/'


@pytest.mark.django_db
def test_post_login_target_rejects_external_next(make_panel_user, rf_request):
    repórter = make_panel_user('alvo_externo', role=CustomUser.Role.REPORTER)
    destino = panels.post_login_target(repórter, rf_request, next_url='https://evil.com/')
    assert destino == panels.panel_url(panels.PANEL_CMS)


@pytest.mark.django_db
def test_post_login_target_ignores_auth_path_next(make_panel_user, rf_request):
    """`next=/entrar/` devolveria o usuário ao login — laço."""
    repórter = make_panel_user('alvo_laco', role=CustomUser.Role.REPORTER)
    destino = panels.post_login_target(repórter, rf_request, next_url='/entrar/')
    assert destino == panels.panel_url(panels.PANEL_CMS)


@pytest.mark.django_db
def test_post_login_target_sends_to_no_access_for_forbidden_panel(make_panel_user, rf_request):
    repórter = make_panel_user('alvo_proibido', role=CustomUser.Role.REPORTER)
    destino = panels.post_login_target(repórter, rf_request, next_url='/admin/settings/')
    assert destino == panels.no_access_url(panels.PANEL_ADMIN)


@pytest.mark.django_db
def test_post_login_target_honors_permitted_chosen_panel(make_panel_user, rf_request):
    root = make_panel_user('alvo_escolha', is_staff=True, is_superuser=True)
    destino = panels.post_login_target(root, rf_request, chosen_panel=panels.PANEL_ADMIN)
    assert destino == panels.panel_url(panels.PANEL_ADMIN)


@pytest.mark.django_db
def test_post_login_target_downgrades_forbidden_chosen_panel(make_panel_user, rf_request):
    """Escolher um painel proibido no formulário não autoriza nada."""
    repórter = make_panel_user('alvo_adultera', role=CustomUser.Role.REPORTER)
    destino = panels.post_login_target(repórter, rf_request, chosen_panel=panels.PANEL_ADMIN)
    assert destino == panels.panel_url(panels.PANEL_CMS)


@pytest.mark.django_db
def test_post_login_target_picker_for_two_panels(make_panel_user, rf_request):
    root = make_panel_user('alvo_dois', is_staff=True, is_superuser=True)
    assert panels.post_login_target(root, rf_request) == reverse('panel:picker')


@pytest.mark.django_db
def test_post_login_target_public_portal_without_panels(make_panel_user, rf_request, settings):
    leitor = make_panel_user('alvo_sem_painel', role=CustomUser.Role.READER)
    destino = panels.post_login_target(leitor, rf_request)
    assert destino == reverse('news:list')


# ── Cards ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_panel_cards_flag_only_reachable_panels(make_panel_user):
    repórter = make_panel_user('cards_reporter', role=CustomUser.Role.REPORTER)
    cards = {card['key']: card for card in panels.panel_cards(repórter)}

    assert cards[panels.PANEL_CMS]['allowed'] is True
    assert cards[panels.PANEL_ADMIN]['allowed'] is False
    assert cards[panels.PANEL_CMS]['label'] == 'Publicação de matérias'
    assert cards[panels.PANEL_ADMIN]['label'] == 'Administração do sistema'


def test_panel_labels_avoid_technical_jargon():
    """Regra de UX: nada de Django/Wagtail/CMS/backend na interface."""
    proibidos = ('django', 'wagtail', 'cms', 'backend', 'admin site')
    for texto in [*panels.PANEL_LABELS.values(), *panels.PANEL_DESCRIPTIONS.values()]:
        assert not any(termo in texto.lower() for termo in proibidos), texto
