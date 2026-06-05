from django.db.models import Count, Q


def get_sidebar_context(request=None):
    """Return sidebar data: popular articles, top categories, top tags."""
    from .models import Article, Category, Tag

    popular_articles = (
        Article.on_site
        .filter(status=Article.Status.PUBLISHED)
        .order_by('-view_count')[:5]
        .select_related('category')
    )
    top_categories = (
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
    top_tags = (
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
    context = {
        'popular_articles': popular_articles,
        'top_categories': top_categories,
        'top_tags': top_tags,
    }
    return context
