from django.contrib.sites.shortcuts import get_current_site

from apps.common.turnstile import get_turnstile_site_key


NEWS_PORTAL_NAME = 'Blog da Kelly'


def site_context(request):
    current_site = get_current_site(request)
    context = {
        'current_site': current_site,
        'news_portal_name': NEWS_PORTAL_NAME,
        'turnstile_site_key': get_turnstile_site_key(),
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
    from apps.news.models import Category
    return {
        'nav_categories': (
            Category.objects
            .filter(parent__isnull=True)
            .order_by('order', 'name')[:8]
        ),
    }
