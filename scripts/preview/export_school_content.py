"""Export school publication data to stdout; never export credentials or write to the DB.

Run from the project root with DJANGO_SETTINGS_MODULE configured. This script can
also be piped to the Python interpreter of the existing web container.
"""
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse


def main():
    root = Path.cwd()
    if not (root / 'manage.py').is_file() or not os.environ.get('DJANGO_SETTINGS_MODULE'):
        raise RuntimeError('Run from the Django project root with DJANGO_SETTINGS_MODULE set.')
    sys.path.insert(0, str(root))
    import django
    django.setup()

    from django.conf import settings
    from django.contrib.auth.models import AnonymousUser
    from django.contrib.sites.models import Site
    from django.core import serializers
    from django.db import connection, transaction
    from django.test import RequestFactory
    from django.urls import resolve

    from apps.common.models import SiteExtension
    from apps.common.social_section import get_social_section_posts
    from apps.school import views
    from apps.school.models import Page, SchoolFeature, SchoolHomeConfig, Testimonial
    from apps.social.models import SocialAccount

    public_site_fields = (
        'site', 'tagline', 'logo', 'favicon', 'primary_email', 'phone_number', 'address',
        'facebook_url', 'instagram_url', 'tiktok_url', 'youtube_url',
        'social_section_enabled', 'social_show_instagram', 'social_show_tiktok',
        'social_section_title', 'social_section_title_en',
        'social_section_subtitle', 'social_section_subtitle_en',
    )
    account_fields = ('site', 'platform', 'display_name', 'username', 'profile_url', 'is_active')
    post_fields = (
        'account', 'platform', 'external_id', 'permalink', 'caption', 'media_type',
        'thumbnail_url', 'thumbnail_image', 'media_url', 'published_at', 'is_visible', 'is_manual',
    )
    records = []

    def append_records(queryset, fields=None):
        records.extend(json.loads(serializers.serialize('json', queryset, fields=fields)))

    # Read-only is enforced by the database, in addition to the query-only code.
    with transaction.atomic():
        with connection.cursor() as cursor:
            if connection.vendor == 'postgresql':
                cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            elif connection.vendor == 'sqlite':
                cursor.execute('PRAGMA query_only = ON')
            else:
                raise RuntimeError('Read-only export supports PostgreSQL and SQLite only.')
        site = Site.objects.get(pk=settings.SITE_ID)
        append_records([site])
        append_records(SiteExtension.objects.filter(site=site), public_site_fields)
        append_records(SchoolHomeConfig.objects.filter(site=site, is_active=True))
        append_records(SchoolFeature.objects.filter(site=site, is_active=True))
        pages = list(Page.objects.filter(site=site, is_published=True))
        append_records(pages)
        append_records(Testimonial.objects.filter(site=site, is_featured=True)[:3])
        posts = list(get_social_section_posts(site))
        append_records(SocialAccount.objects.filter(pk__in={post.account_id for post in posts}), account_fields)
        append_records(posts, post_fields)

        routes = list(dict.fromkeys(['/', '/sobre/', '/cursos/', '/contact/', '/privacidade/']
                                    + [f'/{page.slug}/' for page in pages]))
        rendered = {}
        host = urlparse(settings.KOMUNIKI_PUBLIC_URL).netloc
        for route in routes:
            match = resolve(route)
            request = RequestFactory().get(route, secure=True, HTTP_HOST=host)
            request.site = site
            request.user = AnonymousUser()
            request.session = {}
            request.resolver_match = match
            response = match.func(request, *match.args, **match.kwargs)
            if response.status_code != 200:
                raise RuntimeError(f'Cannot export {route}: HTTP {response.status_code}.')
            rendered[route] = response.content.decode('utf-8')

        code_content = {
            name: getattr(views, name) for name in (
                'HOME_FALLBACK', 'TRUST_FEATURES_FALLBACK', 'COURSE_AWARD', 'COURSE_AWARD_EN',
                'COURSE_PROPOSAL_TITLE', 'COURSE_PROPOSAL_TITLE_EN',
                'COURSE_PROPOSAL_DESCRIPTION', 'COURSE_PROPOSAL_DESCRIPTION_EN',
                'COURSE_TRACKS', 'COURSE_GROUPS',
            )
        }
        public_source_files = ['apps/school/views.py', 'apps/school/courses.py', 'templates/base_school_editorial.html'] + [
            f'templates/school/{name}.html' for name in ('home', 'about', 'page_detail', 'privacy')
        ]
        report = {
            'schema_version': 1, 'exported_at': datetime.now(UTC).isoformat(),
            'settings_module': os.environ['DJANGO_SETTINGS_MODULE'],
            'database_read_only': True, 'site_id': site.pk,
            'source_url': settings.KOMUNIKI_PUBLIC_URL,
            'records': records, 'code_content': code_content, 'rendered_pages': rendered,
            'source_hashes': {
                name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                for name in public_source_files if (root / name).is_file()
            },
            'scope': 'Published school content only; no users, inquiries, subscriptions, API tokens or environment secrets.',
            'media_note': 'Image paths and public URLs are included; binary media must be transferred separately after reviewing the references.',
        }
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
