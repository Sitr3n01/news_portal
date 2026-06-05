from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404
from django.urls import reverse

from apps.common.context_processors import NEWS_PORTAL_NAME

from .models import Article, Category


class LatestArticlesFeed(Feed):
    title = f'{NEWS_PORTAL_NAME} - Últimas publicações'
    description = 'Conteúdos, notícias e bastidores da Komuniki com Kelly Farias.'

    def link(self):
        return reverse('news:list')

    def items(self):
        return (
            Article.on_site
            .filter(status=Article.Status.PUBLISHED)
            .select_related('category', 'author')
            .order_by('-published_at')[:20]
        )

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt or item.meta_description

    def item_pubdate(self, item):
        return item.published_at

    def item_author_name(self, item):
        return item.author.get_full_name() if item.author else ''

    def item_categories(self, item):
        return [item.category.name] if item.category else []


class CategoryFeed(Feed):

    def get_object(self, request, slug):
        return get_object_or_404(Category, slug=slug)

    def title(self, obj):
        return f'{NEWS_PORTAL_NAME} - {obj.name}'

    def link(self, obj):
        return reverse('news:category_detail', kwargs={'slug': obj.slug})

    def description(self, obj):
        return obj.description or f'Artigos da categoria {obj.name}'

    def items(self, obj):
        return (
            Article.on_site
            .filter(category=obj, status=Article.Status.PUBLISHED)
            .select_related('author')
            .order_by('-published_at')[:20]
        )

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt or item.meta_description

    def item_pubdate(self, item):
        return item.published_at
