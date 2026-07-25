"""Testes de fluxo do login unificado (/entrar/).

Cobre autenticação, autorização por cargo, adulteração do destino escolhido,
segurança do `next`, interceptação das telas antigas, sessão única entre áreas,
logout e bloqueio por tentativas repetidas.
"""

import re
from urllib.parse import unquote

import pytest
from django.urls import resolve, reverse

from apps.accounts import panel_views, panels
from apps.accounts.models import CustomUser

SENHA = 'SenhaTeste#2026'


@pytest.fixture
def leitor(make_panel_user):
    return make_panel_user('fluxo_leitor', role=CustomUser.Role.READER)


@pytest.fixture
def reporter(make_panel_user):
    return make_panel_user('fluxo_reporter', role=CustomUser.Role.REPORTER)


@pytest.fixture
def editor(make_panel_user):
    return make_panel_user('fluxo_editor', role=CustomUser.Role.NEWS_EDITOR)


@pytest.fixture
def admin_komuniki(make_panel_user):
    return make_panel_user('fluxo_komuniki', role=CustomUser.Role.SCHOOL_ADMIN, is_staff=True)


@pytest.fixture
def superusuario(make_panel_user):
    return make_panel_user('fluxo_root', role=CustomUser.Role.SUPER_ADMIN,
                           is_staff=True, is_superuser=True)


def entrar(client, user, **extra):
    return client.post(reverse('panel:login'),
                       {'username': user.get_username(), 'password': SENHA, **extra})


# ── Autenticação ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_login_page_renders_anonymous(client):
    response = client.get(reverse('panel:login'))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'Acessar a plataforma' in content
    assert 'Publicação de matérias' in content
    assert 'Administração do sistema' in content


@pytest.mark.django_db
def test_login_form_does_not_preselect_a_panel(client):
    """Regressão: com um rádio pré-marcado, TODA entrada carregaria uma escolha
    implícita, e a regra de destino (área única -> direto; duas -> tela de
    escolha) nunca chegaria a rodar."""
    content = client.get(reverse('panel:login')).content.decode()

    marcado = re.findall(r'<input[^>]*name="panel"[^>]*>', content)
    assert len(marcado) == 2
    assert not any('checked' in campo for campo in marcado)


@pytest.mark.django_db
def test_login_page_avoids_technical_jargon(client):
    """Regra de UX: o operador não deve ver nome de tecnologia na tela."""
    content = client.get(reverse('panel:login')).content.decode().lower()

    for termo in ('django', 'wagtail', 'backend'):
        assert termo not in content, termo


@pytest.mark.django_db
def test_login_success_sets_session(client, reporter):
    response = entrar(client, reporter)

    assert response.status_code == 302
    assert client.session.get('_auth_user_id') == str(reporter.pk)


@pytest.mark.django_db
def test_login_wrong_password_shows_ptbr_error(client, reporter):
    response = client.post(reverse('panel:login'),
                           {'username': reporter.get_username(), 'password': 'errada'})

    assert response.status_code == 200
    assert 'Usuário ou senha incorretos' in response.content.decode()
    assert '_auth_user_id' not in client.session


@pytest.mark.django_db
def test_inactive_user_cannot_log_in(client, make_panel_user):
    inativo = make_panel_user('fluxo_inativo', role=CustomUser.Role.NEWS_EDITOR, is_active=False)

    response = entrar(client, inativo)

    assert response.status_code == 200
    assert '_auth_user_id' not in client.session


@pytest.mark.django_db
def test_authenticated_user_revisiting_login_is_redirected(client, reporter):
    client.force_login(reporter)

    response = client.get(reverse('panel:login'))

    assert response.status_code == 302
    assert response.url == panels.panel_url(panels.PANEL_CMS)


# ── Autorização por cargo ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_reporter_lands_on_publishing_area(client, reporter):
    response = entrar(client, reporter)

    assert response.url == panels.panel_url(panels.PANEL_CMS)


@pytest.mark.django_db
def test_school_admin_lands_on_system_administration(client, admin_komuniki):
    response = entrar(client, admin_komuniki)

    assert response.url == panels.panel_url(panels.PANEL_ADMIN)


@pytest.mark.django_db
def test_superuser_lands_on_panel_picker(client, superusuario):
    response = entrar(client, superusuario)

    assert response.url == reverse('panel:picker')

    picker = client.get(reverse('panel:picker'))
    assert picker.status_code == 200
    assert 'Para onde você quer ir?' in picker.content.decode()


@pytest.mark.django_db
def test_reader_without_panels_lands_on_public_portal(client, leitor):
    """Regressão: sem LOGIN_REDIRECT_URL o default do Django dava 405."""
    response = entrar(client, leitor)

    assert response.url == reverse('news:list')
    assert client.get(response.url).status_code == 200


@pytest.mark.django_db
def test_hiring_manager_has_no_panels(client, make_panel_user):
    guardado = make_panel_user('fluxo_hiring', role=CustomUser.Role.HIRING_MANAGER)

    response = entrar(client, guardado)

    assert response.url == reverse('news:list')


@pytest.mark.django_db
def test_reporter_cannot_reach_admin_by_url(client, reporter):
    """Cadeia completa de quem já está autenticado e digita /admin/ na barra:

    /admin/ -> /admin/login/ (AdminSite.admin_view reverte 'admin:login', URL
    fixa no código do Django) -> /entrar/ (rota-sombra) -> como a sessão já
    existe, o login não pede senha de novo: manda direto para a explicação.
    """
    client.force_login(reporter)

    response = client.get(reverse('admin:index'), follow=True)

    assert response.redirect_chain[0][0] == '/admin/login/?next=/admin/'
    assert response.redirect_chain[1][0].startswith('/entrar/')
    assert unquote(response.redirect_chain[1][0]).endswith('next=/admin/')
    assert response.redirect_chain[-1][0] == panels.no_access_url(panels.PANEL_ADMIN)
    assert response.status_code == 403


@pytest.mark.django_db
def test_reader_cannot_reach_cms_by_url(client, leitor):
    client.force_login(leitor)

    response = client.get(panels.panel_url(panels.PANEL_CMS), follow=True)

    assert reverse('wagtailadmin_home') not in response.request['PATH_INFO']


# ── Adulteração do destino escolhido ───────────────────────────────────────

@pytest.mark.django_db
def test_chosen_panel_is_honored_when_permitted(client, superusuario):
    response = entrar(client, superusuario, panel=panels.PANEL_ADMIN)

    assert response.url == panels.panel_url(panels.PANEL_ADMIN)


@pytest.mark.django_db
def test_reporter_choosing_admin_is_downgraded_not_granted(client, reporter):
    """A escolha do formulário é conselho, nunca autorização."""
    response = entrar(client, reporter, panel=panels.PANEL_ADMIN)

    assert response.url == panels.panel_url(panels.PANEL_CMS)

    # E o painel negado continua fechado de verdade.
    admin_response = client.get(reverse('admin:index'))
    assert admin_response.status_code == 302


@pytest.mark.django_db
def test_invalid_panel_value_does_not_authenticate(client, reporter):
    response = client.post(reverse('panel:login'), {
        'username': reporter.get_username(), 'password': SENHA, 'panel': 'root',
    })

    assert response.status_code == 200
    assert '_auth_user_id' not in client.session


# ── Segurança do redirecionamento ──────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.parametrize('malicioso', [
    'https://evil.com/',
    '//evil.com/',
    'http://evil.com/admin/',
])
def test_external_next_is_ignored(client, reporter, malicioso):
    response = entrar(client, reporter, next=malicioso)

    assert response.url == panels.panel_url(panels.PANEL_CMS)
    assert 'evil.com' not in response.url


@pytest.mark.django_db
def test_next_to_login_page_is_ignored(client, reporter):
    """Sem o filtro de is_auth_path isto viraria laço de redirecionamento."""
    response = entrar(client, reporter, next=reverse('panel:login'))

    assert response.url == panels.panel_url(panels.PANEL_CMS)


@pytest.mark.django_db
def test_public_next_is_honored(client, reporter):
    response = entrar(client, reporter, next='/news/artigo-qualquer/')

    assert response.url == '/news/artigo-qualquer/'


@pytest.mark.django_db
def test_next_to_reachable_panel_is_honored(client, superusuario):
    destino = reverse('admin:index') + 'accounts/'

    response = entrar(client, superusuario, next=destino)

    assert response.url == destino


@pytest.mark.django_db
def test_next_to_unreachable_panel_shows_no_access(client, reporter):
    response = entrar(client, reporter, next=reverse('admin:index') + 'accounts/')

    assert response.url == panels.no_access_url(panels.PANEL_ADMIN)

    pagina = client.get(response.url)
    assert pagina.status_code == 403
    assert 'Administração do sistema' in pagina.content.decode()


# ── Interceptação das telas antigas ────────────────────────────────────────

def test_admin_login_url_is_intercepted():
    """Nível de resolve() de propósito: se alguém reordenar config/urls.py, o
    sequestro para de valer silenciosamente e nenhum status code denunciaria."""
    assert resolve('/admin/login/').func.view_class.__name__ == 'RedirectView'


def test_cms_login_url_is_intercepted():
    assert resolve('/cms/login/').func.view_class.__name__ == 'RedirectView'


def test_logout_urls_point_to_unified_view():
    for path in ('/admin/logout/', '/cms/logout/', '/sair/'):
        assert resolve(path).func is panel_views.panel_logout, path


@pytest.mark.django_db
def test_admin_login_redirect_preserves_next(client):
    response = client.get('/admin/login/?next=/admin/accounts/')

    assert response.status_code == 302
    assert response.url == '/entrar/?next=/admin/accounts/'


@pytest.mark.django_db
def test_cms_login_redirect_preserves_next(client):
    response = client.get('/cms/login/?next=/cms/pages/')

    assert response.status_code == 302
    assert response.url == '/entrar/?next=/cms/pages/'


@pytest.mark.django_db
def test_anonymous_hitting_cms_is_sent_to_unified_login(client):
    """Exercita WAGTAILADMIN_LOGIN_URL: o Wagtail redireciona direto, sem escala."""
    response = client.get(reverse('wagtailadmin_home'))

    assert response.status_code == 302
    assert response.url.startswith('/entrar/')
    assert 'next=' in response.url


@pytest.mark.django_db
def test_anonymous_hitting_admin_is_sent_to_unified_login(client):
    response = client.get(reverse('admin:index'), follow=True)

    assert response.redirect_chain[-1][0].startswith('/entrar/')


def test_reverse_wagtailadmin_login_still_resolves():
    """Regressão: nomear as rotas-sombra de /cms/ sequestraria este reverse,
    porque wagtail.admin.urls não define app_name."""
    assert reverse('wagtailadmin_login') == '/cms/login/'
    assert reverse('wagtailadmin_logout') == '/cms/logout/'


def test_reverse_admin_login_unchanged():
    """apps/common/tests.py depende deste valor."""
    assert reverse('admin:login') == '/admin/login/'


@pytest.mark.django_db
def test_wagtail_password_reset_is_disabled(client):
    response = client.get('/cms/password_reset/done/')

    assert response.status_code == 404


@pytest.mark.django_db
def test_admin_password_reset_redirects_to_single_flow(client):
    response = client.get(reverse('admin_password_reset'))

    assert response.status_code == 302
    assert response.url == reverse('accounts:password_reset')


# ── Sessão única entre as áreas ────────────────────────────────────────────

@pytest.mark.django_db
def test_single_login_grants_both_panels(client, superusuario):
    entrar(client, superusuario, panel=panels.PANEL_CMS)

    assert client.get(reverse('wagtailadmin_home')).status_code == 200
    # Nenhuma segunda autenticação: mesma sessão do Django nas duas áreas.
    assert client.get(reverse('admin:index')).status_code == 200


@pytest.mark.django_db
def test_remember_unchecked_sets_browser_session_expiry(client, reporter):
    entrar(client, reporter)

    assert client.session.get_expiry_age() == 0 or client.session.get_expire_at_browser_close()


@pytest.mark.django_db
def test_remember_checked_keeps_persistent_session(client, reporter):
    entrar(client, reporter, remember='on')

    assert client.session.get_expire_at_browser_close() is False


# ── Logout ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_logout_post_ends_session(client, reporter):
    client.force_login(reporter)

    response = client.post(reverse('panel:logout'))

    assert response.status_code == 302
    assert '_auth_user_id' not in client.session


@pytest.mark.django_db
def test_logout_get_does_not_log_out(client, reporter):
    """GET nunca altera estado — evita logout por prefetch ou link visitado."""
    client.force_login(reporter)

    response = client.get(reverse('panel:logout'))

    assert response.status_code == 302
    assert response.url == reverse('panel:login')
    assert client.session.get('_auth_user_id') == str(reporter.pk)


@pytest.mark.django_db
@pytest.mark.parametrize('path', ['/admin/logout/', '/cms/logout/'])
def test_legacy_logout_urls_end_session(client, superusuario, path):
    client.force_login(superusuario)

    response = client.post(path)

    assert response.status_code == 302
    assert response.url == reverse('panel:login')
    assert '_auth_user_id' not in client.session


@pytest.mark.django_db
def test_logout_from_one_area_ends_the_other(client, superusuario):
    client.force_login(superusuario)
    assert client.get(reverse('admin:index')).status_code == 200

    client.post('/cms/logout/')

    assert client.get(reverse('admin:index')).status_code == 302


@pytest.mark.django_db
def test_reader_logout_still_goes_to_news(client, leitor):
    """Compatibilidade: a navbar do portal depende de accounts:logout."""
    client.force_login(leitor)

    response = client.post(reverse('accounts:logout'))

    assert response.status_code == 302
    assert response.url == '/news/'
    assert '_auth_user_id' not in client.session


# ── Página de acesso negado ────────────────────────────────────────────────

@pytest.mark.django_db
def test_no_access_returns_403_and_lists_available_panels(client, reporter):
    client.force_login(reporter)

    response = client.get(panels.no_access_url(panels.PANEL_ADMIN))

    assert response.status_code == 403
    content = response.content.decode()
    assert 'Administração do sistema' in content
    assert 'Publicação de matérias' in content


@pytest.mark.django_db
def test_no_access_explains_remedy_when_user_has_nothing(client, leitor):
    client.force_login(leitor)

    response = client.get(reverse('panel:no_access'))

    assert response.status_code == 403
    assert 'Administrador Geral' in response.content.decode()


@pytest.mark.django_db
def test_no_access_redirects_anonymous_to_login(client):
    """Não revela a existência das áreas a quem não se identificou."""
    response = client.get(panels.no_access_url(panels.PANEL_ADMIN))

    assert response.status_code == 302
    assert response.url == reverse('panel:login')


@pytest.mark.django_db
def test_picker_redirects_when_only_one_panel(client, reporter):
    client.force_login(reporter)

    response = client.get(reverse('panel:picker'))

    assert response.status_code == 302
    assert response.url == panels.panel_url(panels.PANEL_CMS)


# ── Bloqueio por tentativas repetidas (django-axes) ────────────────────────

@pytest.mark.django_db
def test_lockout_after_repeated_failures(client, reporter, settings):
    for _ in range(settings.AXES_FAILURE_LIMIT):
        client.post(reverse('panel:login'),
                    {'username': reporter.get_username(), 'password': 'errada'})

    # Senha CORRETA depois do limite: continua barrado — é o ponto do bloqueio.
    bloqueado = client.post(reverse('panel:login'),
                            {'username': reporter.get_username(), 'password': SENHA})

    # 429 (Too Many Requests) é o default do django-axes 8.x e é o código
    # semanticamente certo para limite de tentativas.
    assert bloqueado.status_code == settings.AXES_HTTP_RESPONSE_CODE == 429
    assert 'Acesso bloqueado temporariamente' in bloqueado.content.decode()
    assert '_auth_user_id' not in client.session
