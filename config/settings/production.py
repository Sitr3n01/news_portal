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
