from django.contrib.sitemaps import Sitemap

from .models import Article


class ArticleSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Article.on_site.filter(status=Article.Status.PUBLISHED)

    def lastmod(self, obj):
        return obj.updated_at
