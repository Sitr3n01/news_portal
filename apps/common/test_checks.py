"""Check de deploy que recusa segredos de exemplo (auditoria de segurança, SEC-01)."""

import secrets

import pytest
from django.core.checks import registry

from apps.common.checks import check_secret_placeholders

CHAVE_FORTE = secrets.token_urlsafe(64)


def _ids():
    return [error.id for error in check_secret_placeholders(None)]


def test_check_only_runs_with_deploy_flag():
    assert check_secret_placeholders in registry.registry.get_checks(include_deployment_checks=True)
    assert check_secret_placeholders not in registry.registry.get_checks(include_deployment_checks=False)


@pytest.mark.parametrize('key', [
    '__TROQUE_POR_UMA_CHAVE_FORTE__',
    'your-secret-key-here',
    'django-insecure-change-me-in-production',
    'ci-test-secret-key-not-for-production',
])
def test_public_secret_key_is_an_error(settings, key):
    settings.SECRET_KEY = key
    settings.DATABASES = {'default': {**settings.DATABASES['default'], 'PASSWORD': 'x' * 20}}
    assert 'common.E010' in _ids()


def test_real_secret_key_passes(settings):
    settings.SECRET_KEY = CHAVE_FORTE
    settings.DATABASES = {'default': {**settings.DATABASES['default'], 'PASSWORD': secrets.token_urlsafe(24)}}
    settings.EMAIL_HOST_PASSWORD = secrets.token_urlsafe(16)
    settings.CLOUDFLARE_TURNSTILE_SECRET_KEY = ''
    assert _ids() == []


@pytest.mark.parametrize('password', ['__TROQUE_POR_UMA_SENHA_FORTE__', 'news_portal_pass', 'kelly_pass'])
def test_public_db_password_is_an_error(settings, password):
    settings.SECRET_KEY = CHAVE_FORTE
    settings.DATABASES = {'default': {**settings.DATABASES['default'], 'PASSWORD': password}}
    assert 'common.E011' in _ids()


@pytest.mark.parametrize('name,value', [
    ('EMAIL_HOST_PASSWORD', '__SENHA_SMTP__'),
    ('CLOUDFLARE_TURNSTILE_SECRET_KEY', '__SECRET_KEY_DO_PAINEL_CLOUDFLARE__'),
])
def test_public_service_secret_is_an_error(settings, name, value):
    settings.SECRET_KEY = CHAVE_FORTE
    setattr(settings, name, value)
    assert 'common.E012' in _ids()
