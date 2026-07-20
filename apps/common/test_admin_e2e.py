"""Testes e2e do re-tema Material 3 do admin e das correções de confiabilidade
(FASE 3 do plano de execução M3). Cobre: dashboard, todas as telas do admin
registradas, guias, integridade do menu UNFOLD, persona Editor de Notícias,
upload da biblioteca de mídia, registro com/sem Turnstile, índices do Article,
cache da sidebar do blog, smoke do front público e IP real nas curtidas.

Os dois portais (Komuniki e Blog da Kelly) compartilham o mesmo Site
(SITE_ID=1) — os fixtures usam Site.objects.get_current() em vez de criar um
segundo site, como o restante do projeto já faz.
"""
from io import BytesIO

import pytest
from django.contrib import admin as django_admin
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from PIL import Image

from apps.accounts.admin_roles import ensure_admin_role_groups, sync_user_role_group
from apps.accounts.models import CustomUser
from apps.common import turnstile
from apps.media_library.admin import MAX_MEDIA_UPLOAD_BYTES, MediaFileForm
from apps.news.models import Article, ArticleLike
from apps.news.utils import get_sidebar_context


@pytest.fixture(autouse=True)
def staticfiles_storage(settings):
    """Páginas do admin usam {% static %} para os assets do próprio Unfold.
    Troca para storage sem manifesto para não depender de collectstatic ter
    rodado antes desta suíte especificamente."""
    settings.STORAGES = {
        **settings.STORAGES,
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }


def make_superuser(django_user_model, username):
    return django_user_model.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password='SenhaTeste#2026',
        is_staff=True,
        is_superuser=True,
    )


def make_png_upload(name='foto.png', size=(64, 64)):
    buf = BytesIO()
    Image.new('RGB', size, (10, 80, 160)).save(buf, format='PNG')
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type='image/png')


# ── 1. Dashboard M3 ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_admin_dashboard_renders_m3_theme_and_greeting(client, django_user_model):
    user = make_superuser(django_user_model, 'm3_dashboard_super')
    client.force_login(user)

    response = client.get(reverse('admin:index'))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'kb-dashboard' in content
    assert 'm3_theme.css' in content
    assert 'fonts.googleapis.com' in content
    assert 'Olá,' in content


# ── 2. Todas as telas de admin registradas ───────────────────────────────────

@pytest.mark.django_db
def test_all_registered_admin_models_are_reachable_by_superuser(client, django_user_model):
    user = make_superuser(django_user_model, 'registry_super')
    client.force_login(user)

    permission_request = RequestFactory().get('/admin/')
    permission_request.user = user

    for model, model_admin in list(django_admin.site._registry.items()):
        opts = model._meta
        changelist_url = reverse(f'admin:{opts.app_label}_{opts.model_name}_changelist')
        response = client.get(changelist_url)
        assert response.status_code == 200, f'changelist de {opts.label} retornou {response.status_code}'

        if model_admin.has_add_permission(permission_request):
            add_url = reverse(f'admin:{opts.app_label}_{opts.model_name}_add')
            add_response = client.get(add_url)
            assert add_response.status_code == 200, f'add de {opts.label} retornou {add_response.status_code}'


# ── 3. Guias ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.parametrize('route_name', ['admin_school_guide', 'admin_news_guide', 'admin_management_guide'])
def test_admin_guides_return_200_for_superuser(client, django_user_model, route_name):
    user = make_superuser(django_user_model, f'guide_{route_name}')
    client.force_login(user)

    response = client.get(reverse(route_name))

    assert response.status_code == 200


# ── 4. Integridade do menu UNFOLD ────────────────────────────────────────────

@pytest.mark.django_db
def test_unfold_sidebar_navigation_integrity(settings, django_user_model):
    user = make_superuser(django_user_model, 'nav_integrity_super')
    request = RequestFactory().get('/admin/')
    request.user = user

    groups = settings.UNFOLD['SIDEBAR']['navigation']
    assert groups

    for group in groups:
        for item in group['items']:
            link = str(item['link'])
            assert link.startswith('/'), f'{item["title"]}: link não é uma URL absoluta ({link!r})'

            permission = item.get('permission')
            if permission is not None:
                assert permission(request) is True, f'{item["title"]}: superuser deveria ter permissão'

            active = item.get('active')
            if active is not None:
                active(request)  # não pode levantar exceção


# ── 5. Persona Editor de Notícias ────────────────────────────────────────────

@pytest.mark.django_db
def test_news_editor_persona_has_scoped_admin_access(client, django_user_model):
    ensure_admin_role_groups()
    user = django_user_model.objects.create_user(
        username='editora_persona',
        email='editora_persona@example.com',
        password='SenhaTeste#2026',
        is_staff=True,
        role='news_editor',
    )
    sync_user_role_group(user)
    client.force_login(user)

    assert client.get(reverse('admin:index')).status_code == 200
    assert client.get(reverse('admin:news_article_changelist')).status_code == 200
    assert client.get(reverse('admin:school_page_changelist')).status_code == 403


# ── 6. Uploads da Biblioteca de Mídia ────────────────────────────────────────

@pytest.mark.django_db
def test_media_file_form_rejects_html_upload():
    upload = SimpleUploadedFile('pagina.html', b'<html><body>oi</body></html>', content_type='text/html')
    form = MediaFileForm(data={'title': 'Arquivo html'}, files={'file': upload})

    assert not form.is_valid()
    assert 'file' in form.errors


@pytest.mark.django_db
def test_media_file_form_rejects_svg_upload():
    upload = SimpleUploadedFile('icone.svg', b'<svg xmlns="http://www.w3.org/2000/svg"></svg>', content_type='image/svg+xml')
    form = MediaFileForm(data={'title': 'Ícone svg'}, files={'file': upload})

    assert not form.is_valid()
    assert 'file' in form.errors


@pytest.mark.django_db
def test_media_file_form_rejects_oversized_upload():
    payload = b'%PDF-1.4' + (b'0' * (MAX_MEDIA_UPLOAD_BYTES + 1))
    upload = SimpleUploadedFile('grande.pdf', payload, content_type='application/pdf')
    form = MediaFileForm(data={'title': 'Arquivo grande'}, files={'file': upload})

    assert not form.is_valid()
    assert 'file' in form.errors


@pytest.mark.django_db
def test_media_file_form_accepts_small_pdf():
    upload = SimpleUploadedFile('edital.pdf', b'%PDF-1.4 conteudo pequeno', content_type='application/pdf')
    form = MediaFileForm(data={'title': 'Edital'}, files={'file': upload})

    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_media_file_form_accepts_valid_png(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    upload = make_png_upload()
    form = MediaFileForm(data={'title': 'Foto'}, files={'file': upload})

    assert form.is_valid(), form.errors


# ── 7. Registro com/sem Turnstile ────────────────────────────────────────────

@pytest.mark.django_db
def test_register_view_get_returns_200(client):
    response = client.get(reverse('accounts:register'))

    assert response.status_code == 200


@pytest.mark.django_db
def test_register_without_turnstile_site_key_skips_anti_bot_check(client, settings):
    settings.CLOUDFLARE_TURNSTILE_SITE_KEY = ''
    settings.CLOUDFLARE_TURNSTILE_SECRET_KEY = ''

    response = client.post(reverse('accounts:register'), {
        'username': 'sem_turnstile',
        'email': 'sem_turnstile@example.com',
        'password1': 'SenhaTeste#2026',
        'password2': 'SenhaTeste#2026',
    })

    assert response.status_code == 302
    assert CustomUser.objects.filter(username='sem_turnstile').exists()


@pytest.mark.django_db
def test_register_with_site_key_rejects_invalid_turnstile(client, settings, monkeypatch):
    settings.CLOUDFLARE_TURNSTILE_SITE_KEY = 'test-site-key'
    settings.CLOUDFLARE_TURNSTILE_SECRET_KEY = 'test-secret-key'
    monkeypatch.setattr(turnstile, 'verify_turnstile', lambda token, remote_ip='': False)

    response = client.post(reverse('accounts:register'), {
        'username': 'bloqueado_turnstile',
        'email': 'bloqueado@example.com',
        'password1': 'SenhaTeste#2026',
        'password2': 'SenhaTeste#2026',
        'cf-turnstile-response': 'qualquer-coisa',
    })

    assert response.status_code == 200
    assert not CustomUser.objects.filter(username='bloqueado_turnstile').exists()
    assert 'Confirme a verificação anti-bot' in response.content.decode()


@pytest.mark.django_db
def test_register_with_site_key_accepts_valid_turnstile(client, settings, monkeypatch):
    settings.CLOUDFLARE_TURNSTILE_SITE_KEY = 'test-site-key'
    settings.CLOUDFLARE_TURNSTILE_SECRET_KEY = 'test-secret-key'
    monkeypatch.setattr(turnstile, 'verify_turnstile', lambda token, remote_ip='': True)

    response = client.post(reverse('accounts:register'), {
        'username': 'aprovado_turnstile',
        'email': 'aprovado@example.com',
        'password1': 'SenhaTeste#2026',
        'password2': 'SenhaTeste#2026',
        'cf-turnstile-response': 'token-valido',
    })

    assert response.status_code == 302
    assert CustomUser.objects.filter(username='aprovado_turnstile').exists()


# ── 8. Índices do Article ────────────────────────────────────────────────────

def test_article_meta_includes_new_composite_indexes():
    index_names = {index.name for index in Article._meta.indexes}

    assert 'news_art_site_status_pub' in index_names
    assert 'news_art_status_newsletter' in index_names


# ── 9. Cache da sidebar do blog ──────────────────────────────────────────────

@pytest.mark.django_db
def test_get_sidebar_context_is_cached_per_site():
    cache.clear()
    Site.objects.clear_cache()
    site = Site.objects.get_current()
    Article.objects.create(
        title='Artigo cacheado',
        slug='artigo-cacheado',
        content='Conteúdo para a sidebar.',
        site=site,
        status=Article.Status.PUBLISHED,
    )

    first = get_sidebar_context()
    assert len(first['popular_articles']) == 1

    with CaptureQueriesContext(connection) as ctx:
        second = get_sidebar_context()

    assert len(ctx.captured_queries) == 0
    assert len(second['popular_articles']) == 1


# ── 10. Smoke do front público ───────────────────────────────────────────────

@pytest.mark.django_db
def test_front_public_routes_smoke(client):
    # Nenhum fixture extra de Site/SchoolHomeConfig é necessário: o Site
    # padrão (SITE_ID=1) já existe via migração e as views públicas caem em
    # conteúdo de fallback quando não há configuração específica no banco.
    assert client.get('/').status_code == 200
    assert client.get('/news/').status_code == 200
    assert client.get('/healthz/').status_code == 200
    assert client.get('/contact/').status_code == 200
    assert client.get('/hiring/').status_code == 200
    assert client.get('/accounts/login/').status_code == 200


# ── 11. IP real nas curtidas ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_toggle_like_records_ip_from_x_forwarded_for(client, django_user_model):
    site = Site.objects.get_current()
    article = Article.objects.create(
        title='Artigo curtido',
        slug='artigo-curtido',
        content='Conteúdo do artigo curtido.',
        site=site,
        status=Article.Status.PUBLISHED,
    )
    user = django_user_model.objects.create_user(
        username='curtidor', email='curtidor@example.com', password='SenhaTeste#2026',
    )
    client.force_login(user)

    response = client.post(
        reverse('news:toggle_like', args=[article.id]),
        HTTP_X_FORWARDED_FOR='203.0.113.7',
    )

    assert response.status_code in (200, 302)
    like = ArticleLike.objects.get(article=article, user=user)
    assert like.ip_address == '203.0.113.7'


# ── 12. Data migration: reclassificação de file_type legado ─────────────────

@pytest.mark.django_db
def test_media_migration_reclassifies_legacy_svg_to_other():
    from importlib import import_module

    from django.apps import apps as django_apps

    from apps.media_library.models import MediaFile

    # Linha legada: .svg persistido como IMAGE antes da allowlist (renderizava <img>).
    legacy_svg = MediaFile.objects.create(title='Ícone legado', file='media_library/files/legado.svg', file_type=MediaFile.FileType.IMAGE)
    kept_png = MediaFile.objects.create(title='Foto', file='media_library/files/foto.png', file_type=MediaFile.FileType.IMAGE)

    migration = import_module('apps.media_library.migrations.0003_refresh_legacy_file_types')
    migration.refresh_file_types(django_apps, None)

    legacy_svg.refresh_from_db()
    kept_png.refresh_from_db()
    assert legacy_svg.file_type == MediaFile.FileType.OTHER
    assert kept_png.file_type == MediaFile.FileType.IMAGE


# ── 13. Redirect pós-login do admin (hidden field "next") ────────────────────
# templates/admin/login.html não renderizava o hidden "next" que o próprio
# AdminSite.login() já disponibiliza no contexto — um acesso direto a
# /admin/login/ (sem ?next=) caía no fallback de LOGIN_REDIRECT_URL em vez do
# painel.

@pytest.mark.django_db
def test_admin_login_page_renders_next_hidden_field_pointing_to_index(client):
    response = client.get(reverse('admin:login'))

    assert response.status_code == 200
    content = response.content.decode()
    assert f'name="next" value="{reverse("admin:index")}"' in content


@pytest.mark.django_db
def test_admin_login_without_explicit_next_redirects_to_admin_index(client, django_user_model):
    # Replica o navegador real: o hidden "next" só existe porque o GET o
    # renderiza (testado acima) — um POST sem passar por esse form não prova
    # nada sobre o fix. client.post(url, {...}) não interpreta o HTML do GET.
    user = make_superuser(django_user_model, 'login_redirect_super')

    response = client.post(
        reverse('admin:login'),
        {'username': user.username, 'password': 'SenhaTeste#2026', 'next': reverse('admin:index')},
    )

    assert response.status_code == 302
    assert response.url == reverse('admin:index')
