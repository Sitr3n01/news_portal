from .base import *  # noqa: F401,F403
from .base import BASE_DIR, INSTALLED_APPS, MIDDLEWARE

DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS += [  # noqa: F405
    'django_extensions',
    'debug_toolbar',
]

MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')  # noqa: F405

INTERNAL_IPS = ['127.0.0.1', '0.0.0.0']

# E-mail: NÃO fixar backend aqui. base.py já lê EMAIL_BACKEND/DEFAULT_FROM_EMAIL
# do .env com fallback seguro para console — travar o valor neste arquivo era
# exatamente o que impedia testar entrega real em desenvolvimento (Mailpit, via
# docker/docker-compose.yml) sem comentar/descomentar código a cada troca.

# Simplified static files for development
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
