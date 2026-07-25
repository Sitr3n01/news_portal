from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import RedirectView
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from apps.accounts import panel_views
from apps.common import admin_guides
from apps.common.views import health_check
from apps.news.sitemaps import ArticleSitemap
from apps.school.sitemaps import PageSitemap

sitemaps = {
    'news': ArticleSitemap,
    'school': PageSitemap,
}


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
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
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
