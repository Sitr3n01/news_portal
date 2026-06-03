from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# Security
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 43200  # 12 horas
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])  # noqa: F405
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)  # noqa: F405
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Token de reset de senha expira em 1 hora (padrão Django: 24h)
PASSWORD_RESET_TIMEOUT = 3600

# Renovar sessão a cada request (evita logout de usuário ativo com SESSION_COOKIE_AGE)
SESSION_SAVE_EVERY_REQUEST = True

# Healthcheck interno do container bate em HTTP (sem proxy/header X-Forwarded-Proto),
# então isenta /healthz/ do redirect HTTPS para a probe não receber 301.
SECURE_REDIRECT_EXEMPT = [r'^healthz/$']

# ── Rastreamento de erros (Sentry) — habilitado apenas quando SENTRY_DSN existe ──
SENTRY_DSN = env('SENTRY_DSN', default='')  # noqa: F405
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=env.float('SENTRY_TRACES_SAMPLE_RATE', default=0.0),  # noqa: F405
        send_default_pii=False,
        environment=env('SENTRY_ENVIRONMENT', default='production'),  # noqa: F405
    )
