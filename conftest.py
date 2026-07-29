"""Fixtures compartilhadas por toda a suíte.

Fixtures definidas dentro de um módulo de teste têm precedência sobre as daqui
(pytest resolve do mais específico para o mais genérico), então as cópias locais
que já existem em ``apps/*/tests.py`` continuam valendo e nada muda para elas.
"""

import pytest
from django.contrib.sites.models import Site
from django.core.cache import cache


@pytest.fixture(autouse=True)
def staticfiles_storage(settings):
    """Desliga o storage com manifesto durante os testes.

    ``base.py`` usa ``CompressedManifestStaticFilesStorage`` (whitenoise), que
    exige ``collectstatic`` prévio: sem isto qualquer teste que renderize um
    template com ``{% static %}`` morre com ``Missing staticfiles manifest entry``.
    """
    settings.STORAGES = {
        **settings.STORAGES,
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }


@pytest.fixture(autouse=True)
def clear_cache():
    """Isola o cache entre testes.

    O rate limit de recuperação de senha (apps.accounts.views) guarda estado no
    cache; sem limpar, um teste envenena o seguinte.
    """
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def current_site(settings):
    site, _ = Site.objects.update_or_create(
        pk=settings.SITE_ID,
        defaults={'domain': 'testserver', 'name': 'Komuniki Teste'},
    )
    Site.objects.clear_cache()
    return site


@pytest.fixture
def make_panel_user(db, django_user_model):
    """Cria um usuário já com o grupo do cargo aplicado.

    Espelha o que o admin faz no ``save_related`` (apps/accounts/admin.py): o
    ``role`` só vira grupo quando ``sync_user_role_group`` é chamado
    explicitamente. Sem isso o usuário nasce sem permissão nenhuma.
    """
    from apps.accounts.admin_roles import ensure_admin_role_groups, sync_user_role_group

    def _make(username, role=None, is_staff=False, is_superuser=False, is_active=True, password='SenhaTeste#2026'):
        ensure_admin_role_groups()
        user = django_user_model.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password=password,
            is_staff=is_staff,
            is_superuser=is_superuser,
            is_active=is_active,
        )
        if role is not None:
            user.role = role
            user.save(update_fields=['role'])
        sync_user_role_group(user)
        return django_user_model.objects.get(pk=user.pk)

    return _make
