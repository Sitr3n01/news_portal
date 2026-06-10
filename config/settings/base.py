from pathlib import Path

import environ
from django.urls import reverse_lazy

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

INSTALLED_APPS = [
    # Unfold MUST come before django.contrib.admin
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',

    # Django built-ins
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',

    # Third-party
    'django_htmx',
    'imagekit',
    'axes',

    # Project apps
    'apps.common.apps.CommonConfig',
    'apps.accounts.apps.AccountsConfig',
    'apps.school.apps.SchoolConfig',
    'apps.hiring.apps.HiringConfig',
    'apps.contact.apps.ContactConfig',
    'apps.news.apps.NewsConfig',
    'apps.media_library.apps.MediaLibraryConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'axes.middleware.AxesMiddleware',
    'csp.middleware.CSPMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.common.context_processors.site_context',
                'apps.common.context_processors.news_nav_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
    }
}

AUTH_USER_MODEL = 'accounts.CustomUser'

SITE_ID = 1

# Public portal URLs used by cross-domain navigation. The same Django app serves
# both domains, so relative links would stay on the current host.
KOMUNIKI_PUBLIC_URL = env('KOMUNIKI_PUBLIC_URL', default='https://komuniki.com.br')
KELLY_BLOG_PUBLIC_URL = env('KELLY_BLOG_PUBLIC_URL', default='https://kellyfarias.com.br/news')

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
LANGUAGES = [
    ('pt-br', 'Português (BR)'),
    ('en', 'English'),
]
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Django Unfold Admin Configuration ──────────────────────────────────────
def _admin_has_any(request, *permissions):
    return request.user.is_superuser or any(request.user.has_perm(permission) for permission in permissions)


def _admin_is_superuser(request):
    return request.user.is_superuser


UNFOLD = {
    'SITE_TITLE': 'Olá!',
    'SITE_HEADER': 'Olá!',
    'SITE_URL': None,  # Removido — links de portal estão na sidebar (Visualizar Portais)
    'SITE_ICON': None,  # Deixar None ou apontar para um favicon estático
    # Força o tema escuro de fato (antes só o seletor era escondido via CSS, mas o
    # tema caía em 'auto' e seguia o SO). Com THEME='dark', o Unfold aplica
    # class="dark" sempre e esconde o seletor — mantém o design system kb- consistente.
    'THEME': 'dark',
    'SHOW_HISTORY': True,
    'SHOW_VIEW_ON_SITE': True,
    'STYLES': [
        lambda request: '/static/admin/css/overrides.css',
        lambda request: '/static/admin/css/dashboard.css',
        lambda request: '/static/admin/css/admin_ux.css',
    ],
    'COLORS': {
        'primary': {
            '50': '239 246 255',
            '100': '219 234 254',
            '200': '191 219 254',
            '300': '147 197 253',
            '400': '96 165 250',
            '500': '59 130 246',
            '600': '17 82 212',   # #1152d4 — cor primária do projeto
            '700': '29 78 216',
            '800': '30 64 175',
            '900': '30 58 138',
            '950': '23 37 84',
        },
    },
    'SIDEBAR': {
        'show_search': True,
        'show_all_applications': False,
        'navigation': [
            {
                'title': 'Guias de Operação',
                'separator': False,
                'items': [
                    {
                        'title': 'Guia Komuniki',
                        'icon': 'school',
                        'link': reverse_lazy('admin_school_guide'),
                        'permission': lambda request: _admin_has_any(
                            request,
                            'school.view_page',
                            'school.view_schoolhomeconfig',
                            'school.view_schoolfeature',
                            'school.view_testimonial',
                            'contact.view_contactinquiry',
                        ),
                        'active': lambda request: request.path.startswith('/admin/guias/escola/'),
                    },
                    {
                        'title': 'Guia Editorial',
                        'icon': 'newspaper',
                        'link': reverse_lazy('admin_news_guide'),
                        'permission': lambda request: _admin_has_any(
                            request,
                            'news.view_article',
                            'news.view_category',
                            'news.view_tag',
                            'news.view_comment',
                            'news.view_newslettersubscription',
                            'news.view_newsletterdelivery',
                        ),
                        'active': lambda request: request.path.startswith('/admin/guias/noticias/'),
                    },
                    {
                        'title': 'Guia de Gerenciamento',
                        'icon': 'admin_panel_settings',
                        'link': reverse_lazy('admin_management_guide'),
                        'permission': lambda request: _admin_has_any(
                            request,
                            'accounts.view_customuser',
                            'auth.view_group',
                            'sites.view_site',
                            'common.view_siteextension',
                            'media_library.view_mediafile',
                            'media_library.view_mediafolder',
                        ),
                        'active': lambda request: request.path.startswith('/admin/guias/gerenciamento/'),
                    },
                ],
            },
            {
                'title': 'Visualizar Portais',
                'separator': False,
                'items': [
                    {
                        'title': 'Blog da Kelly',
                        'icon': 'newspaper',
                        'link': '/news/',
                        'active': lambda request: False,  # Links externos — nunca marcar como ativo no admin
                    },
                    {
                        'title': 'Komuniki',
                        'icon': 'school',
                        'link': '/',  # Escola está montada no prefixo raiz (path('', include(school.urls)))
                        'active': lambda request: False,  # '/' seria substring de qualquer URL → sempre falso
                    },
                ],
            },
            {
                'title': 'Komuniki',
                'separator': True,
                'items': [
                    {
                        'title': 'Página Cursos',
                        'icon': 'article',
                        'link': reverse_lazy('admin:school_page_changelist'),
                        'permission': lambda request: request.user.has_perm('school.view_page'),
                    },
                    {
                        'title': 'Home Komuniki',
                        'icon': 'home',
                        'link': reverse_lazy('admin:school_schoolhomeconfig_changelist'),
                        'permission': lambda request: request.user.has_perm('school.view_schoolhomeconfig'),
                    },
                    {
                        'title': 'Blocos da Home',
                        'icon': 'auto_awesome',
                        'link': reverse_lazy('admin:school_schoolfeature_changelist'),
                        'permission': lambda request: request.user.has_perm('school.view_schoolfeature'),
                    },
                    {
                        'title': 'Mensagens',
                        'icon': 'contact_mail',
                        'link': reverse_lazy('admin:contact_contactinquiry_changelist'),
                        'permission': lambda request: request.user.has_perm('contact.view_contactinquiry'),
                    },
                ],
            },
            {
                'title': 'Blog da Kelly',
                'separator': True,
                'items': [
                    {
                        'title': 'Artigos',
                        'icon': 'newspaper',
                        'link': reverse_lazy('admin:news_article_changelist'),
                        'permission': lambda request: request.user.has_perm('news.view_article'),
                    },
                    {
                        'title': 'Categorias',
                        'icon': 'category',
                        'link': reverse_lazy('admin:news_category_changelist'),
                        'permission': lambda request: request.user.has_perm('news.view_category'),
                    },
                    {
                        'title': 'Tags',
                        'icon': 'label',
                        'link': reverse_lazy('admin:news_tag_changelist'),
                        'permission': lambda request: request.user.has_perm('news.view_tag'),
                    },
                    {
                        'title': 'Comentários',
                        'icon': 'chat',
                        'link': reverse_lazy('admin:news_comment_changelist'),
                        'permission': lambda request: request.user.has_perm('news.view_comment'),
                    },
                    {
                        'title': 'Newsletter',
                        'icon': 'mail',
                        'link': reverse_lazy('admin:news_newslettersubscription_changelist'),
                        'permission': lambda request: request.user.has_perm('news.view_newslettersubscription'),
                    },
                    {
                        'title': 'Entregas de Newsletter',
                        'icon': 'mark_email_read',
                        'link': reverse_lazy('admin:news_newsletterdelivery_changelist'),
                        'permission': lambda request: request.user.has_perm('news.view_newsletterdelivery'),
                    },
                ],
            },
            {
                'title': 'Recursos guardados',
                'separator': True,
                'items': [
                    {
                        'title': 'Depoimentos',
                        'icon': 'format_quote',
                        'link': reverse_lazy('admin:school_testimonial_changelist'),
                        'permission': _admin_is_superuser,
                    },
                    {
                        'title': 'Equipe',
                        'icon': 'group',
                        'link': reverse_lazy('admin:school_teammember_changelist'),
                        'permission': _admin_is_superuser,
                    },
                    {
                        'title': 'Vagas',
                        'icon': 'work',
                        'link': reverse_lazy('admin:hiring_jobposting_changelist'),
                        'permission': _admin_is_superuser,
                    },
                    {
                        'title': 'Departamentos',
                        'icon': 'business',
                        'link': reverse_lazy('admin:hiring_department_changelist'),
                        'permission': _admin_is_superuser,
                    },
                    {
                        'title': 'Candidaturas',
                        'icon': 'description',
                        'link': reverse_lazy('admin:hiring_application_changelist'),
                        'permission': _admin_is_superuser,
                    },
                    {
                        'title': 'Curtidas',
                        'icon': 'favorite',
                        'link': reverse_lazy('admin:news_articlelike_changelist'),
                        'permission': _admin_is_superuser,
                    },
                    {
                        'title': 'Favoritos',
                        'icon': 'bookmark',
                        'link': reverse_lazy('admin:news_articlebookmark_changelist'),
                        'permission': _admin_is_superuser,
                    },
                ],
            },
            {
                'title': 'Sistema',
                'separator': True,
                'items': [
                    {
                        'title': 'Usuários',
                        'icon': 'manage_accounts',
                        'link': reverse_lazy('admin:accounts_customuser_changelist'),
                        'permission': lambda request: _admin_has_any(request, 'accounts.view_customuser'),
                    },
                    {
                        'title': 'Grupos e Permissões',
                        'icon': 'badge',
                        'link': reverse_lazy('admin:auth_group_changelist'),
                        'permission': lambda request: _admin_has_any(request, 'auth.view_group'),
                    },
                    {
                        'title': 'Configurações do Site',
                        'icon': 'settings',
                        'link': reverse_lazy('admin:common_siteextension_changelist'),
                        'permission': lambda request: _admin_has_any(request, 'common.view_siteextension'),
                    },
                    {
                        'title': 'Biblioteca de Mídia',
                        'icon': 'perm_media',
                        'link': reverse_lazy('admin:media_library_mediafile_changelist'),
                        'permission': lambda request: _admin_has_any(request, 'media_library.view_mediafile'),
                    },
                ],
            },
        ],
    },
    'DASHBOARD_CALLBACK': 'apps.common.dashboard.dashboard_callback',
}

# ── Upload Limits ──────────────────────────────────────────────────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760   # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760   # 10 MB

# ── Email ──────────────────────────────────────────────────────────────────
# Em produção, configurar via .env:
#   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
#   EMAIL_HOST=smtp.seuservidor.com
#   EMAIL_PORT=587
#   EMAIL_HOST_USER=seu@email.com
#   EMAIL_HOST_PASSWORD=sua_senha
#   EMAIL_USE_TLS=True
#   DEFAULT_FROM_EMAIL=News Portal <noticias@seusite.com>
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@localhost')
EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)

# Cloudflare Turnstile anti-bot verification.
# In DEBUG/local, apps.common.turnstile falls back to Cloudflare's official test keys.
CLOUDFLARE_TURNSTILE_SITE_KEY = env('CLOUDFLARE_TURNSTILE_SITE_KEY', default='')
CLOUDFLARE_TURNSTILE_SECRET_KEY = env('CLOUDFLARE_TURNSTILE_SECRET_KEY', default='')
CLOUDFLARE_TURNSTILE_VERIFY_TIMEOUT = env.float('CLOUDFLARE_TURNSTILE_VERIFY_TIMEOUT', default=5.0)

# ── Authentication Backends (axes brute-force protection) ──────────────────
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.5  # 30 minutos (em horas)
AXES_LOCKOUT_PARAMETERS = ['ip_address', 'username']
AXES_RESET_ON_SUCCESS = True
# axes 6+ delega a detecção de IP ao python-ipware (prefixo AXES_IPWARE_*).
AXES_IPWARE_PROXY_COUNT = 1
AXES_IPWARE_META_PRECEDENCE_ORDER = [
    'HTTP_X_FORWARDED_FOR',
    'REMOTE_ADDR',
]

# ── Content Security Policy (django-csp) — defense-in-depth ────────────────
# Espelha a política CSP do nginx.conf para proteção mesmo sem reverse proxy.
# Alpine.js, HTMX e Tailwind CDN requerem unsafe-inline/unsafe-eval e hosts CDN
# explicitamente permitidos para que o frontend publico renderize sob CSP.
from csp.constants import NONE, SELF, UNSAFE_EVAL, UNSAFE_INLINE  # noqa: E402

CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src': [SELF],
        'script-src': [
            SELF,
            UNSAFE_INLINE,
            UNSAFE_EVAL,
            'https://challenges.cloudflare.com',
        ],
        'style-src': [
            SELF,
            UNSAFE_INLINE,
            'https://fonts.googleapis.com',
        ],
        'img-src': [SELF, 'data:', 'https:'],
        'font-src': [SELF, 'https://fonts.gstatic.com'],
        'frame-src': [
            SELF,
            'https://www.youtube.com',
            'https://www.youtube-nocookie.com',
            'https://www.instagram.com',
            'https://www.tiktok.com',
            'https://challenges.cloudflare.com',
        ],
        'connect-src': [SELF, 'https://challenges.cloudflare.com'],
        'base-uri': [SELF],
        'form-action': [SELF],
        'object-src': [NONE],
        # Anti-clickjacking moderno — complementa X-Frame-Options: DENY (legado).
        'frame-ancestors': [NONE],
    },
}

# ── Logging (12-factor: stdout/stderr; o orquestrador captura) ──────────────
LOG_LEVEL = env('LOG_LEVEL', default='INFO')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {process:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': env('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}
