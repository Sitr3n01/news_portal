from .base import *

DEBUG = False
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# accounts.E001 (apps/accounts/checks.py) recusaria backend fora-de-SMTP fora
# de DEBUG — que é exatamente a combinação que esta suíte usa de propósito.
# Um interruptor explícito aqui é mais honesto do que o check tentar adivinhar
# "isto é teste?" por heurística de sys.argv, e evita que todo `pytest` vire
# um accounts.E001 e derrube o CI.
EMAIL_CHECK_SKIP = True

# LocMem nos testes: rápido, isolado por processo e sem depender da tabela de
# cache. O conftest da raiz limpa entre testes.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'tests',
    }
}
