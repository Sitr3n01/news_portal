"""Regras de template que sustentam a CSP do site público (auditoria, XSS-02/XSS-03).

A política do Django exige nonce em script inline (sem 'unsafe-inline'). Ela
só se sustenta enquanto todo script inline levar o nonce da resposta e nenhum
template voltar a usar atributo on* — e o projeto proíbe |safe.
"""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from apps.accounts.models import CustomUser
from apps.news.models import Article

TEMPLATES = Path(settings.BASE_DIR) / 'templates'
DATA_SCRIPT_TYPES = {'application/ld+json', 'application/json'}
SCRIPT_TAG = re.compile(r'<script\b([^>]*)>', re.IGNORECASE)
INLINE_HANDLER = re.compile(r'<[a-zA-Z][^>]*?\son[a-z]+\s*=\s*["\']', re.DOTALL)
NONCE = re.compile(r"'nonce-([^']+)'")


def _templates():
    return sorted(TEMPLATES.rglob('*.html'))


def _inline_executable_scripts(html):
    """Atributos de cada <script> inline que o navegador executaria."""
    for attrs in SCRIPT_TAG.findall(html):
        if 'src=' in attrs:
            continue
        kind = re.search(r'type="([^"]+)"', attrs)
        if kind and kind.group(1) in DATA_SCRIPT_TYPES:
            continue
        yield attrs


# ── Estático: vale para todo template, inclusive os que nenhum teste renderiza ──


def test_no_template_uses_safe_filter():
    offenders = [str(path.relative_to(TEMPLATES)) for path in _templates() if re.search(r'\|\s*safe(seq)?\b', path.read_text())]
    assert offenders == []


def test_no_template_uses_inline_event_handlers():
    offenders = [str(path.relative_to(TEMPLATES)) for path in _templates() if INLINE_HANDLER.search(path.read_text())]
    assert offenders == [], 'use data-* + static/js/site-actions.js no lugar de on*="..."'


def test_every_inline_script_in_templates_carries_the_nonce():
    offenders = [
        f'{path.relative_to(TEMPLATES)}: <script{attrs}>'
        for path in _templates()
        for attrs in _inline_executable_scripts(path.read_text())
        if 'nonce="{{ request.csp_nonce }}"' not in attrs
    ]
    assert offenders == []


# ── Dinâmico: o cabeçalho de verdade bate com as tags de verdade ─────────────


@pytest.fixture
def article(current_site):
    return Article.objects.create(
        title='Notícia no ar', slug='noticia-no-ar', excerpt='Resumo', content='<p>Texto</p>',
        site=current_site, status=Article.Status.PUBLISHED,
    )


def _assert_strict_csp(response):
    assert response.status_code == 200, response.status_code
    header = response['Content-Security-Policy']
    script_src = next(part for part in header.split(';') if part.strip().startswith('script-src'))
    assert "'unsafe-inline'" not in script_src
    html = response.content.decode()
    scripts = list(_inline_executable_scripts(html))
    if scripts:
        nonce = NONCE.search(script_src)
        assert nonce, 'script inline na página, mas sem nonce no cabeçalho'
        for attrs in scripts:
            assert f'nonce="{nonce.group(1)}"' in attrs, attrs


@pytest.mark.django_db
@pytest.mark.parametrize('url', [
    '/',
    '/news/',
    '/news/noticia-no-ar/',
    '/cursos/comunicador-profissionalizante/',
    '/contact/',
    '/entrar/',
    '/accounts/login/',
    '/accounts/register/',
])
def test_public_pages_send_strict_csp(client, settings, article, url):
    settings.CLOUDFLARE_TURNSTILE_SITE_KEY = '1x00000000000000000000AA'  # renderiza o script do Turnstile
    _assert_strict_csp(client.get(url))


@pytest.mark.django_db
def test_logged_in_pages_send_strict_csp(client, make_panel_user, django_user_model, article):
    reader = django_user_model.objects.create_user(username='leitor_csp', password='x', email_verified=True)
    client.force_login(reader)
    _assert_strict_csp(client.get(reverse('news:user_dashboard')))

    client.force_login(make_panel_user('editor_csp', role=CustomUser.Role.NEWS_EDITOR, is_staff=True))
    _assert_strict_csp(client.get(reverse('panel:dashboard')))


@pytest.mark.django_db
def test_admin_areas_keep_their_own_policy(client, django_user_model, current_site):
    client.force_login(django_user_model.objects.create_superuser('raiz_csp', 'raiz@example.com', 'x'))
    for url in ('/admin/accounts/customuser/', '/cms/reports/noticias-em-revisao/'):
        response = client.get(url)
        assert response.status_code == 200, url
        assert 'Content-Security-Policy' not in response, url
