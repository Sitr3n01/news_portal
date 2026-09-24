from pathlib import Path

import environ

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

    # Wagtail CMS (7.4.x LTS) — must come after Django contrib apps,
    # before other third-party and project apps.
    # django-taggit provides the Tag model used by Wagtail's images/documents;
    # it must be installed before any Wagtail app that uses TaggableManager.
    'taggit',
    'wagtail',
    'wagtail.admin',
    'wagtail.documents',
    'wagtail.snippets',
    'wagtail.images',
    'wagtail.search',
    'wagtail.sites',
    # OBRIGATÓRIO, ainda que os usuários sejam gerenciados no /admin/ do Django.
    # `wagtail.users` é onde vive o modelo UserProfile (preferências de tema,
    # densidade e notificação de cada conta), e wagtail.admin o usa em
    # admin/mail.py, admin/forms/account.py e nas templatetags — ou seja, no
    # caminho dos e-mails de workflow e da tela de conta.
    # Sem o app na lista, o Django não acha `wagtail.users` no registro e resolve
    # o app_label subindo o pacote até `wagtail` (label `wagtailcore`): o modelo
    # passa a se chamar wagtailcore.UserProfile e esperar a tabela
    # `wagtailcore_userprofile`, que NENHUMA migration do wagtailcore cria. O
    # resultado é tabela inexistente em runtime.
    # As telas de Usuários/Grupos que este app acrescenta ao /cms/ são protegidas
    # pelas permissões `wagtailusers`, que nenhum grupo de cargo recebe
    # (ver apps/accounts/admin_roles.GENERAL_ADMIN_APP_LABELS), então só
    # superusuário as enxerga.
    'wagtail.users',
    'wagtail.contrib.table_block',
    # Redirecionamentos: trocar o endereço (slug) de uma notícia que já esteve
    # no ar cria um 301 do endereço antigo para o novo (apps/news/signals.py),
    # para não quebrar links compartilhados nem o que o Google já indexou.
    'wagtail.contrib.redirects',

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
    'apps.cms_media.apps.CmsMediaConfig',
    'apps.social.apps.SocialConfig',
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
    # Só age em respostas 404: procura um redirecionamento para o caminho
    # pedido. Endereço que existe nunca é desviado.
    'wagtail.contrib.redirects.middleware.RedirectMiddleware',
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

# Redes sociais — credenciais opcionais do app TikTok, usadas só para renovar o
# token de acesso (refresh). Vazias por padrão; preenchidas por variável de ambiente
# quando houver app oficial. Nunca versionar segredos. O Instagram renova o token de
# longa duração apenas com o próprio token, sem segredo de app.
TIKTOK_CLIENT_KEY = env('TIKTOK_CLIENT_KEY', default='')
TIKTOK_CLIENT_SECRET = env('TIKTOK_CLIENT_SECRET', default='')

# Token de recuperação de senha expira em 1 hora (padrão do Django: 24h).
PASSWORD_RESET_TIMEOUT = 3600

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
# Apenas pt-br na lista: com LocaleMiddleware ativo, qualquer idioma extra aqui
# faria o admin (Django core + Unfold) seguir o Accept-Language do navegador,
# misturando inglês e português. Restringir os idiomas suportados força o
# fallback para LANGUAGE_CODE (pt-br) em qualquer navegador.
LANGUAGES = [
    ('pt-br', 'Português (BR)'),
]
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True
# Datas curtas no painel ("24/07/2026 18:27"); ver config/formats/pt_BR/formats.py.
FORMAT_MODULE_PATH = ['config.formats']

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

# ── Wagtail 7.4.x LTS Configuration ────────────────────────────────────────
# WAGTAILADMIN_BASE_URL monta URLs absolutas (links de preview, e-mails de
# notificação) — precisa ser o domínio real em produção, não localhost.
# Mesmo padrão de KOMUNIKI_PUBLIC_URL/KELLY_BLOG_PUBLIC_URL logo abaixo.
WAGTAIL_SITE_NAME = 'Portal de Notícias'
WAGTAILADMIN_BASE_URL = env('WAGTAILADMIN_BASE_URL', default='http://localhost:8000')

# Custom image/document models (Fase 2) — required BEFORE the first migration
# of cms_media, otherwise Wagtail creates the stock models instead.
WAGTAILIMAGES_IMAGE_MODEL = 'cms_media.Image'
WAGTAILDOCS_DOCUMENT_MODEL = 'cms_media.Document'

# Teto de upload de imagem no caminho do Wagtail (/cms/images/).
#
# `apps.common.validators.validate_uploaded_image` (5 MB + Pillow verify) está ligado
# só aos ProcessedImageField legados e ao media_library — o upload do Wagtail passava
# direto e caía nos defaults dele: 10 MB e 128 MEGAPIXELS. Um único arquivo assim faz
# o Pillow alocar centenas de MB dentro de um worker limitado a 1500M.
#
# Os valores são repetidos aqui de propósito, e não importados de
# apps.common.validators: settings é avaliado antes do app registry estar pronto.
# Fonte de verdade do número: MAX_UPLOAD_BYTES naquele módulo.
WAGTAILIMAGES_MAX_UPLOAD_SIZE = 5 * 1024 * 1024   # espelha validators.MAX_UPLOAD_BYTES
WAGTAILIMAGES_MAX_IMAGE_PIXELS = 25_000_000       # ~6000x4000; o default do Wagtail é 128 MP
WAGTAILIMAGES_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp']  # o default do Wagtail também aceita gif

# Manda o require_admin_access e o botão de sair do Wagtail para o login
# unificado (ver wagtail/admin/auth.py e wagtail/admin/views/account.py). É o
# gancho oficial — nada de editar código do Wagtail.
WAGTAILADMIN_LOGIN_URL = 'panel:login'

# Desliga o fluxo de recuperação de senha PRÓPRIO do Wagtail. Ele é um segundo
# emissor de tokens, sem o domain_override contra host header poisoning e sem
# rate limit — os dois presentes em apps.accounts.views.CustomPasswordResetView,
# que passa a ser o único caminho.
WAGTAIL_PASSWORD_RESET_ENABLED = False

# Backend de tasks explícito, e não por omissão.
#
# O Wagtail 7.4 traz django_tasks e enfileira ali a atualização do índice de
# referências e do índice de busca a cada save. Sem a chave TASKS, a biblioteca cai
# no ImmediateBackend, que executa a tarefa de forma síncrona no próprio processo
# que salvou. Isso é aceitável aqui: quem paga é a request de um editor salvando um
# artigo, não o tráfego público. A alternativa (DatabaseBackend) exigiria um
# processo `db_worker` permanente, que em 1 vCPU custa mais do que economiza.
#
# Declarar não muda comportamento — transforma um default acidental em decisão.
TASKS = {
    'default': {
        'BACKEND': 'django_tasks.backends.immediate.ImmediateBackend',
    },
}



# ── Django Unfold Admin Configuration ──────────────────────────────────────
# O /admin/ faz parte do painel unificado (apps/common/newsroom): a sidebar e o
# cabeçalho do Unfold foram trocados pelos do painel (templates/admin/nav_sidebar.html
# e templates/unfold/helpers/header.html), e a navegação inteira — com as
# checagens de permissão — mora em apps/common/newsroom/navigation.py. Por isso
# SIDEBAR['navigation'] fica vazio: manter um segundo menu aqui seria uma
# segunda fonte de verdade.
#
# A página inicial do /admin/ redireciona para a visão geral (/painel/); o
# antigo DASHBOARD_CALLBACK saiu junto com ela (as peças operacionais que ele
# montava estão em apps/common/dashboard.py e aparecem na visão geral).
def _static(path):
    """URL de estático resolvida por requisição (respeita o manifesto do
    whitenoise). Import tardio: settings não pode puxar o sistema de templates."""

    def resolve(request):
        from django.templatetags.static import static

        return static(path)

    return resolve


UNFOLD = {
    'SITE_TITLE': 'Newsroom',
    'SITE_HEADER': 'Newsroom',
    'SITE_URL': None,
    'SITE_ICON': None,
    # Tema claro forçado: é o tema da referência aprovada do painel e o mesmo
    # aplicado ao Wagtail (static/newsroom/css/newsroom-wagtail.css). Com THEME
    # definido, o Unfold aplica a classe sempre e esconde o seletor de tema.
    'THEME': 'light',
    'SHOW_HISTORY': True,
    'SHOW_VIEW_ON_SITE': True,
    'STYLES': [
        _static('newsroom/css/newsroom.css'),
        _static('admin/css/dashboard.css'),
        _static('admin/css/admin_ux.css'),
        _static('newsroom/css/newsroom-unfold.css'),
    ],
    'SCRIPTS': [
        _static('newsroom/js/newsroom.js'),
    ],
    # Paleta do painel (tokens em static/newsroom/css/newsroom.css): cinzas
    # neutros e "primária" na tinta #171717 — botões primários pretos, como na
    # referência. O azul de destaque (#2563eb) entra pelo CSS do painel.
    'COLORS': {
        'base': {
            '50': '#fafafa',
            '100': '#f5f5f5',
            '200': '#eaeaea',
            '300': '#d4d4d4',
            '400': '#a3a3a3',
            '500': '#737373',
            '600': '#525252',
            '700': '#404040',
            '800': '#262626',
            '900': '#171717',
            '950': '#0a0a0a',
        },
        'primary': {
            '50': '#f5f5f5',
            '100': '#eaeaea',
            '200': '#d4d4d4',
            '300': '#a3a3a3',
            '400': '#737373',
            '500': '#404040',
            '600': '#171717',
            '700': '#343434',
            '800': '#0a0a0a',
            '900': '#0a0a0a',
            '950': '#000000',
        },
    },
    'BORDER_RADIUS': '8px',
    'SIDEBAR': {
        'show_search': False,
        'show_all_applications': False,
        'navigation': [],
    },
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
# Mutuamente exclusivo com EMAIL_USE_TLS: o Django levanta ValueError no envio
# se os dois forem True. TLS/587 é o padrão; SSL/465 é para provedores legados.
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=False)
# Sem timeout, um servidor SMTP travado pendura o worker gunicorn
# indefinidamente a cada pedido de recuperação de senha.
EMAIL_TIMEOUT = env.int('EMAIL_TIMEOUT', default=10)
SERVER_EMAIL = env('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)

# Cloudflare Turnstile anti-bot verification.
# In DEBUG/local, apps.common.turnstile falls back to Cloudflare's official test keys.
CLOUDFLARE_TURNSTILE_SITE_KEY = env('CLOUDFLARE_TURNSTILE_SITE_KEY', default='')
CLOUDFLARE_TURNSTILE_SECRET_KEY = env('CLOUDFLARE_TURNSTILE_SECRET_KEY', default='')
CLOUDFLARE_TURNSTILE_VERIFY_TIMEOUT = env.float('CLOUDFLARE_TURNSTILE_VERIFY_TIMEOUT', default=5.0)

# ── Cache ──────────────────────────────────────────────────────────────────
# DatabaseCache (e não LocMemCache) porque o cache é usado para rate limiting:
# o LocMem é por processo, então com N workers gunicorn o limite efetivo vira
# N× o pretendido. A tabela é criada pela migration apps/common/0009.
# Sem Redis por decisão de projeto (docs/ai/development_rules.md §4).
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache',
        'TIMEOUT': 300,
        'KEY_PREFIX': 'kb',
        # MAX_ENTRIES subiu de 5000 porque o cache passou a carregar tambem as chaves
        # de dedup de view_count (apps/news/views.py) e as paginas de sitemap, alem do
        # rate limiting. Com o teto antigo, o cull comecaria a derrubar justamente as
        # entradas de rate limit. CULL_FREQUENCY 4 remove 1/4 no estouro, em vez de 1/3.
        'OPTIONS': {'MAX_ENTRIES': 20000, 'CULL_FREQUENCY': 4},
    },
}

# ── Autenticação / login unificado ─────────────────────────────────────────
# A equipe entra pelos painéis em `panel:login` (/entrar/); leitores do portal
# usam `accounts:login`. LOGIN_URL aponta para o do leitor porque é ele que o
# @login_required das views públicas precisa alcançar — o Wagtail é redirecionado
# por WAGTAILADMIN_LOGIN_URL e o Django admin pela rota-sombra em config/urls.py.
LOGIN_URL = 'accounts:login'
# Antes indefinido: o default do Django ('/accounts/profile/') resolve neste
# projeto para uma view @require_POST, devolvendo 405 a quem entrasse sem `next`.
LOGIN_REDIRECT_URL = 'news:list'
LOGOUT_REDIRECT_URL = 'news:list'

# Tela amigável em PT-BR quando o axes bloqueia por tentativas repetidas.
AXES_LOCKOUT_TEMPLATE = 'auth/lockout.html'

# Interruptor de emergência: com False, /admin/login/ e /cms/login/ voltam às
# telas nativas sem precisar de deploy de código (ver config/urls.py).
UNIFIED_LOGIN_ENABLED = env.bool('UNIFIED_LOGIN_ENABLED', default=True)

# ── Login com Google (OpenID Connect) ──────────────────────────────────────
# Alternativa ao login por senha, NUNCA um caminho de autorização: o Google só
# diz QUEM é a pessoa; o que ela alcança continua vindo de apps/accounts/panels.py
# e das permissões no banco. Ver apps/accounts/oauth_google.py.
#
# Crie a credencial em console.cloud.google.com -> "ID do cliente OAuth" ->
# tipo "Aplicativo da Web", e registre lá o MESMO redirect URI de baixo.
GOOGLE_OAUTH_CLIENT_ID = env('GOOGLE_OAUTH_CLIENT_ID', default='')
GOOGLE_OAUTH_CLIENT_SECRET = env('GOOGLE_OAUTH_CLIENT_SECRET', default='')
# Fixado por variável de ambiente em vez de montado com request.build_absolute_uri():
# atrás do nginx o Host é influenciável, e um redirect_uri derivado dele poderia
# ser apontado para outro domínio. O Google também exige correspondência exata
# com o que está registrado no console.
GOOGLE_OAUTH_REDIRECT_URI = env('GOOGLE_OAUTH_REDIRECT_URI', default='')
# Sem credencial, o botão nem aparece e as rotas devolvem 404 — assim CI, testes
# e qualquer instalação sem Google seguem funcionando sem configuração nenhuma.
GOOGLE_OAUTH_ENABLED = bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET and GOOGLE_OAUTH_REDIRECT_URI)

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

# ── Códigos de verificação ──────────────────────────────────────────────────
# Confirmação de e-mail e recuperação de senha por código (apps.accounts.
# verification) compartilham as duas configurações abaixo. TTL curto e teto de
# tentativas baixo são a defesa real de um segredo de 6 dígitos — não um KDF
# lento (ver o comentário de _hash_code em apps/accounts/verification.py).
VERIFICATION_CODE_TTL = env.int('VERIFICATION_CODE_TTL', default=600)  # 10 minutos
VERIFICATION_CODE_MAX_ATTEMPTS = env.int('VERIFICATION_CODE_MAX_ATTEMPTS', default=5)

# ── Content Security Policy (django-csp) — defense-in-depth ────────────────
# Espelha a política CSP do docker/nginx/nginx.conf para proteção mesmo sem
# reverse proxy. As duas TÊM de andar juntas: o nginx usa `add_header ... always`,
# então quando os dois mandam CSP o navegador aplica a INTERSEÇÃO das políticas —
# relaxar só um lado não tem efeito nenhum em produção.
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
        # Anti-clickjacking moderno. SELF, e não NONE, porque o painel de preview
        # do Wagtail renderiza a própria página dentro de um <iframe> de mesma
        # origem (wagtailadmin/shared/side_panels/preview.html). Com NONE o
        # preview fica em branco: o Wagtail força X-Frame-Options: SAMEORIGIN nas
        # views de preview (xframe_options_sameorigin_override), mas pela spec do
        # CSP `frame-ancestors` PREVALECE sobre X-Frame-Options — então NONE
        # anulava o override e nenhum navegador desenhava o iframe.
        # SELF continua barrando clickjacking de qualquer outra origem, que é o
        # ataque que esta diretiva existe para impedir.
        'frame-ancestors': [SELF],
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
        'apps.email': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}
