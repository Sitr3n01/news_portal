"""Explicitly selected, loopback-only settings for the editorial experiment."""
import os

# base.py requires these at import. These values belong only to this preview.
os.environ['SECRET_KEY'] = 'komuniki-editorial-local-preview-only-do-not-use-in-production'
for _key in ('DB_NAME', 'DB_USER', 'DB_PASSWORD'):
    os.environ[_key] = 'unused-local-preview'

from .base import *  # noqa: E402,F403

DESIGN_PREVIEW = True
DESIGN_PREVIEW_SCENARIO = os.environ.get('KOMUNIKI_PREVIEW_SCENARIO', 'current')
if DESIGN_PREVIEW_SCENARIO not in {'current', 'demo', 'local'}:
    raise ValueError('KOMUNIKI_PREVIEW_SCENARIO must be current, demo or local.')

DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
PREVIEW_ROOT = BASE_DIR / '.preview'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': PREVIEW_ROOT / f'{DESIGN_PREVIEW_SCENARIO}.sqlite3',
    },
}
MEDIA_ROOT = PREVIEW_ROOT / f'{DESIGN_PREVIEW_SCENARIO}-media'
STATIC_ROOT = PREVIEW_ROOT / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
EMAIL_CHECK_SKIP = True
GOOGLE_OAUTH_ENABLED = False
GOOGLE_OAUTH_CLIENT_ID = ''
GOOGLE_OAUTH_CLIENT_SECRET = ''
GOOGLE_OAUTH_REDIRECT_URI = ''
CLOUDFLARE_TURNSTILE_SITE_KEY = '1x00000000000000000000AA'
CLOUDFLARE_TURNSTILE_SECRET_KEY = '1x0000000000000000000000000000000AA'
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_NAME = f'komuniki_preview_{DESIGN_PREVIEW_SCENARIO}_session'
CSRF_COOKIE_NAME = f'komuniki_preview_{DESIGN_PREVIEW_SCENARIO}_csrf'
KOMUNIKI_PUBLIC_URL = 'http://127.0.0.1:' + ('8011' if DESIGN_PREVIEW_SCENARIO == 'current' else '8012')
# Blog links remain the public destinations present in the original site.
TEMPLATES[0]['OPTIONS']['context_processors'] += ['apps.school.preview_context.design_preview']
# config.urls includes debug_toolbar whenever DEBUG is true and it is installed.
# Register the existing development dependency; its toolbar stays hidden.
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware', *MIDDLEWARE]
DEBUG_TOOLBAR_CONFIG = {'SHOW_TOOLBAR_CALLBACK': lambda request: False}
