from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import index as sitemap_index
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.decorators.cache import cache_control
from django.views.generic import RedirectView
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from apps.accounts import panel_views
from apps.common import admin_guides
from apps.common.views import health_check, robots_txt
from apps.news.sitemaps import ArticleSitemap
from apps.school.sitemaps import CourseSitemap, PageSitemap

sitemaps = {
    'news': ArticleSitemap,
    'school': PageSitemap,
    'school-courses': CourseSitemap,
}

# Cache de 6h no CDN/Cloudflare, e deliberadamente NÃO no DatabaseCache.
#
# `cache_page` chaveia por `build_absolute_uri()`, query string incluída: cada
# `/sitemap.xml?x=1`, `?x=2`, ... criaria uma linha nova em `django_cache`. Ao passar
# de MAX_ENTRIES, o cull do Django apaga as chaves lexicograficamente MENORES
# (`cache_key_culling_sql`) — e `pwd_reset:*`, o rate limit de recuperação de senha
# (apps/accounts/verification.py), ordena abaixo de `viewed:*` e `views.decorators:*`.
# Inundar o sitemap despejaria um controle de segurança.
#
# O header não tem esse problema: nada é armazenado do nosso lado. O conteúdo é
# idêntico para todo visitante (SITE_ID fixo), e a única coisa que varia — o
# Set-Cookie de quem está logado — o Cloudflare não guarda.
cache_sitemap = cache_control(public=True, max_age=60 * 60 * 6)


def _unified_login_shadows(prefix):
    """Rotas que sequestram as telas nativas de login/senha de uma área.

    A resolução de URL é primeiro-que-casa, então estes padrões só funcionam se
    forem declarados ANTES do include da área correspondente.

    Cuidado ao mexer: `wagtail.admin.urls` NÃO define `app_name`, então os nomes
    dele (wagtailadmin_login, wagtailadmin_logout) entram no dicionário plano de
    reverse. Por isso os padrões abaixo ficam SEM `name=` — nomeá-los com os
    mesmos nomes sequestraria também o reverse() e quebraria o Wagtail por
    dentro. `reverse('admin:login')` é imune por ser namespaced, e continua
    devolvendo /admin/login/ (usado por apps/common/tests.py).
    """
    return [
        path(f'{prefix}/login/', RedirectView.as_view(pattern_name='panel:login', query_string=True)),
        # Logout precisa ser view de verdade, não RedirectView: LogoutView do
        # Django 5 só aceita POST e um 302 converteria o POST em GET no caminho.
        path(f'{prefix}/logout/', panel_views.panel_logout),
        path(
            f'{prefix}/password_reset/',
            RedirectView.as_view(pattern_name='accounts:password_reset', query_string=True),
        ),
    ]


urlpatterns = [
    path('healthz/', health_check, name='healthz'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('i18n/', include('django.conf.urls.i18n')),
    # Acesso administrativo unificado (/entrar/, /sair/, /painel/, /sem-acesso/).
    path('', include('apps.accounts.urls_panel', namespace='panel')),
]

if settings.UNIFIED_LOGIN_ENABLED:
    urlpatterns += _unified_login_shadows('admin')
    # `admin_password_reset` é o nome que templates/admin/login.html procura
    # para exibir "Esqueceu a senha?". Nunca esteve roteado — nem pelo Django,
    # nem pelo Unfold — então o botão jamais aparecia. Registrar aqui o acende.
    urlpatterns += [
        path(
            'admin/password_reset/',
            RedirectView.as_view(pattern_name='accounts:password_reset', query_string=True),
            name='admin_password_reset',
        ),
    ]

urlpatterns += [
    path(
        'admin/guias/escola/',
        admin.site.admin_view(admin_guides.school_guide),
        name='admin_school_guide',
    ),
    path(
        'admin/guias/gerenciamento/',
        admin.site.admin_view(admin_guides.management_guide),
        name='admin_management_guide',
    ),
    path('admin/', admin.site.urls),
    # Indice de sitemaps, e nao um XML unico: so assim o `limit` das classes vale.
    # O `name=` da rota de secao e obrigatorio — o index reverte exatamente esse
    # nome para montar as URLs filhas.
    path('sitemap.xml', cache_sitemap(sitemap_index), {'sitemaps': sitemaps}, name='sitemap_index'),
    path(
        'sitemap-<section>.xml',
        cache_sitemap(sitemap),
        {'sitemaps': sitemaps},
        name='django.contrib.sitemaps.views.sitemap',
    ),
    path('hiring/', include('apps.hiring.urls', namespace='hiring')),
    path('contact/', include('apps.contact.urls', namespace='contact')),
    path('news/', include('apps.news.urls', namespace='news')),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
]

if settings.UNIFIED_LOGIN_ENABLED:
    urlpatterns += _unified_login_shadows('cms')

urlpatterns += [
    path('cms/', include(wagtailadmin_urls)),
    path('documents/', include(wagtaildocs_urls)),
    # Catch-all da escola: precisa continuar por último (development_rules §2).
    path('', include('apps.school.urls', namespace='school')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
