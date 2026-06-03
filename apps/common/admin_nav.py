"""Helpers e constantes compartilhados entre o dashboard do admin e os guias.

Centraliza os permission groups e os utilitários de navegação que antes estavam
duplicados (com pequenas divergências) em ``apps.common.dashboard`` e
``apps.common.admin_guides``. Fonte única de verdade evita drift.
"""
from urllib.parse import urlencode

from django.conf import settings
from django.urls import reverse

# ── Permission groups (fonte única) ────────────────────────────────────────
SCHOOL_PERMISSIONS = [
    'school.view_page',
    'school.view_schoolhomeconfig',
    'school.view_schoolfeature',
    'school.view_teammember',
    'school.view_testimonial',
    'hiring.view_jobposting',
    'hiring.view_department',
    'hiring.view_application',
    'contact.view_contactinquiry',
]

NEWS_PERMISSIONS = [
    'news.view_article',
    'news.view_category',
    'news.view_tag',
    'news.view_comment',
    'news.view_newslettersubscription',
    'news.view_newsletterdelivery',
]

MANAGEMENT_PERMISSIONS = [
    'accounts.view_customuser',
    'auth.view_group',
    'sites.view_site',
    'common.view_siteextension',
    'media_library.view_mediafile',
    'media_library.view_mediafolder',
]


# ── Permissões / navegação ─────────────────────────────────────────────────
def can(user, permission):
    if permission == 'superuser':
        return user.is_superuser
    return user.is_superuser or user.has_perm(permission)


def can_any(user, permissions):
    return user.is_superuser or any(can(user, permission) for permission in permissions)


def admin_url(route_name, query=None, args=None):
    url = reverse(route_name, args=args)
    if query:
        return f'{url}?{urlencode(query)}'
    return url


def visible(items):
    return [item for item in items if item]


# ── Configuração de e-mail (para a saúde do sistema) ───────────────────────
def get_setting(name, default=''):
    value = getattr(settings, name, default)
    if value is None:
        return ''
    return str(value)


def get_email_status():
    email_backend = get_setting('EMAIL_BACKEND')
    email_host = get_setting('EMAIL_HOST')
    email_host_user = get_setting('EMAIL_HOST_USER')
    email_host_password = get_setting('EMAIL_HOST_PASSWORD')
    default_from_email = get_setting('DEFAULT_FROM_EMAIL')

    missing = []
    if email_backend != 'django.core.mail.backends.smtp.EmailBackend':
        missing.append('EMAIL_BACKEND SMTP')
    if not email_host or email_host == 'localhost':
        missing.append('EMAIL_HOST')
    if not email_host_user:
        missing.append('EMAIL_HOST_USER')
    if not email_host_password:
        missing.append('EMAIL_HOST_PASSWORD')
    if not default_from_email or default_from_email == 'noreply@localhost':
        missing.append('DEFAULT_FROM_EMAIL')

    backend_parts = email_backend.split('.')
    email_backend_label = '.'.join(backend_parts[-2:]) if len(backend_parts) >= 2 else email_backend

    return {
        'email_backend': email_backend_label if email_backend else 'Não configurado',
        'email_host': email_host if email_host and email_host != 'localhost' else 'Não configurado',
        'email_port': get_setting('EMAIL_PORT', '587'),
        'smtp_configured': not missing,
        'email_missing_settings': ', '.join(missing),
    }
