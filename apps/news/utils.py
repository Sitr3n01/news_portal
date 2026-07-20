from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.db.models import Count, Q

# TTL curto o bastante para refletir publicações novas em minutos, mas alto o
# bastante para tirar as 3 queries da sidebar de toda página de notícias.
SIDEBAR_CACHE_TTL = 600


def _build_sidebar_context():
    """Monta as 3 listas da sidebar com consultas reais ao banco (sem cache)."""
    from .models import Article, Category, Tag

    popular_articles = list(
        Article.on_site
        .filter(status=Article.Status.PUBLISHED)
        .order_by('-view_count')[:5]
        .select_related('category')
    )
    top_categories = list(
        Category.objects
        .annotate(
            article_count=Count(
                'articles',
                filter=Q(articles__status='published'),
            )
        )
        .filter(article_count__gt=0)
        .order_by('-article_count')[:8]
    )
    top_tags = list(
        Tag.objects
        .annotate(
            article_count=Count(
                'articles',
                filter=Q(articles__status='published'),
            )
        )
        .filter(article_count__gt=0)
        .order_by('-article_count')[:20]
    )
    return {
        'popular_articles': popular_articles,
        'top_categories': top_categories,
        'top_tags': top_tags,
    }


def get_sidebar_context(request=None):
    """Return sidebar data: popular articles, top categories, top tags.

    Cacheada por site (TTL de SIDEBAR_CACHE_TTL segundos): a sidebar é igual
    para todo mundo no mesmo site e antes rodava as mesmas 3 queries em toda
    página do portal de notícias.
    """
    site_id = get_current_site(request).pk if request is not None else settings.SITE_ID
    cache_key = f'news:sidebar:{site_id}'
    return cache.get_or_set(cache_key, _build_sidebar_context, timeout=SIDEBAR_CACHE_TTL)
