from django.contrib.sitemaps import Sitemap
from django.db.models import Max
from django.urls import reverse

from .courses import COURSE_GROUPS
from .models import Page


class CourseSitemap(Sitemap):
    """Páginas detalhadas dos cursos: catálogo estático em courses.py, sem updated_at."""

    changefreq = 'monthly'
    priority = 0.6

    def items(self):
        return [course['slug'] for group in COURSE_GROUPS for course in group['courses'] if course.get('page')]

    def location(self, slug):
        return reverse('school:course_detail', kwargs={'course_slug': slug})


class PageSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.5
    limit = 1000

    def items(self):
        return (
            Page.on_site
            .filter(is_published=True)
            .only('slug', 'updated_at')
            .order_by('pk')
        )

    def location(self, obj):
        # Page nao define get_absolute_url, e o default de Sitemap.location chama
        # exatamente isso: /sitemap.xml devolvia AttributeError -> 500 sempre que
        # existia uma pagina de escola publicada.
        return reverse('school:page_detail', kwargs={'slug': obj.slug})

    def lastmod(self, obj):
        return obj.updated_at

    def get_latest_lastmod(self):
        return self.items().aggregate(Max('updated_at'))['updated_at__max']
