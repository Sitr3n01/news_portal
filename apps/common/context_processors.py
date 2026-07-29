from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site

from apps.common.turnstile import get_turnstile_site_key
from apps.news.models import Category

NEWS_PORTAL_NAME = 'Blog da Kelly'


def _with_trailing_slash(url):
    return f'{str(url).rstrip("/")}/'


def site_context(request):
    current_site = get_current_site(request)
    context = {
        'current_site': current_site,
        'news_portal_name': NEWS_PORTAL_NAME,
        'komuniki_public_url': _with_trailing_slash(settings.KOMUNIKI_PUBLIC_URL),
        'kelly_blog_public_url': _with_trailing_slash(settings.KELLY_BLOG_PUBLIC_URL),
        'turnstile_site_key': get_turnstile_site_key(),
        # Sem credencial do Google configurada, o botão "Entrar com Google" nem
        # é renderizado — as rotas devolvem 404 nesse caso, e um botão que leva
        # a 404 é pior do que botão nenhum.
        'google_oauth_enabled': settings.GOOGLE_OAUTH_ENABLED,
    }
    try:
        context['site_settings'] = current_site.extension
    except Exception:
        context['site_settings'] = None
    return context


def news_nav_context(request):
    """Inject top-level categories for news navigation.

    Only runs on /news/ pages to avoid unnecessary queries on other pages.
    """
    if not request.path.startswith('/news/'):
        return {}
    return {
        'nav_categories': (
            Category.objects
            .filter(parent__isnull=True)
            .order_by('order', 'name')[:8]
        ),
    }
