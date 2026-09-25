"""Fronteira de superusuário (auditoria de segurança, PRIV-01).

O cargo Administrador Geral tem accounts.*_customuser, mas superusuário,
grupos e permissões avulsas são decisão só de superusuário — nos dois painéis.
Antes, um POST com is_superuser=on no /admin/ ou em /cms/users/new/ bastava.
"""

import re
from html import unescape

import pytest
from django.contrib.auth.models import Group, Permission
from django.urls import reverse

from apps.accounts.models import CustomUser

SENHA_NOVA = 'OutraSenha#2026forte'


def _input_value(html, name):
    match = re.search(rf'<input[^>]*name="{re.escape(name)}"[^>]*>', html)
    value = re.search(r'value="([^"]*)"', match.group(0)) if match else None
    return unescape(value.group(1)) if value else ''


def _post_change(client, user, **extra):
    url = reverse('admin:accounts_customuser_change', args=[user.pk])
    html = client.get(url).content.decode()
    data = {
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'is_active': 'on',
        'is_staff': 'on',
        'role': user.role,
        'date_joined_0': _input_value(html, 'date_joined_0'),
        'date_joined_1': _input_value(html, 'date_joined_1'),
        '_save': 'Salvar',
        **extra,
    }
    return client.post(url, data)


@pytest.fixture
def general_admin(make_panel_user):
    return make_panel_user('adm_geral', role=CustomUser.Role.SUPER_ADMIN, is_staff=True)


@pytest.fixture
def root(django_user_model):
    return django_user_model.objects.create_superuser('raiz', 'raiz@example.com', 'SenhaRaiz#2026')


# ── Django admin ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_general_admin_cannot_self_grant_superuser(client, general_admin, current_site):
    client.force_login(general_admin)
    html = client.get(reverse('admin:accounts_customuser_change', args=[general_admin.pk])).content.decode()
    assert 'name="is_superuser"' not in html
    assert 'name="groups"' not in html
    assert 'name="user_permissions"' not in html

    permission = Permission.objects.get(codename='delete_customuser')
    group = Group.objects.create(name='Grupo avulso')
    response = _post_change(client, general_admin, is_superuser='on', groups=[group.pk], user_permissions=[permission.pk])

    assert response.status_code == 302
    general_admin.refresh_from_db()
    assert general_admin.is_superuser is False
    assert not general_admin.groups.filter(pk=group.pk).exists()
    assert not general_admin.user_permissions.exists()


@pytest.mark.django_db
def test_general_admin_still_manages_regular_accounts_by_role(client, general_admin, make_panel_user, current_site):
    reporter = make_panel_user('reporter_x', role=CustomUser.Role.REPORTER)
    client.force_login(general_admin)

    response = _post_change(client, reporter, role=CustomUser.Role.NEWS_EDITOR)

    assert response.status_code == 302
    reporter.refresh_from_db()
    assert reporter.role == CustomUser.Role.NEWS_EDITOR
    assert reporter.groups.filter(name='Editor de Notícias').exists()
    assert not reporter.groups.filter(name='Repórter').exists()


@pytest.mark.django_db
def test_general_admin_cannot_touch_superuser_accounts(client, general_admin, root, current_site):
    client.force_login(general_admin)

    assert client.post(reverse('admin:auth_user_password_change', args=[root.pk]), {
        'password1': SENHA_NOVA, 'password2': SENHA_NOVA,
    }).status_code == 403
    assert _post_change(client, root, is_active='').status_code == 403
    assert client.post(reverse('admin:accounts_customuser_delete', args=[root.pk]), {'post': 'yes'}).status_code == 403
    assert client.post(reverse('admin:accounts_customuser_changelist'), {
        'action': 'delete_selected', '_selected_action': [root.pk], 'post': 'yes',
    }).status_code in (200, 403)

    root.refresh_from_db()
    assert root.check_password('SenhaRaiz#2026')
    assert root.is_active
    assert CustomUser.objects.filter(pk=root.pk).exists()


@pytest.mark.django_db
def test_superuser_keeps_full_control(client, root, make_panel_user, current_site):
    target = make_panel_user('promovido', role=CustomUser.Role.SUPER_ADMIN, is_staff=True)
    client.force_login(root)

    response = _post_change(client, target, is_superuser='on')

    assert response.status_code == 302
    target.refresh_from_db()
    assert target.is_superuser is True


@pytest.mark.django_db
def test_general_admin_only_views_groups(client, general_admin, current_site):
    general = Group.objects.get(name='Administrador Geral')
    assert general.permissions.filter(codename='view_group').exists()
    assert not general.permissions.filter(codename__in=['add_group', 'change_group', 'delete_group']).exists()

    client.force_login(general_admin)
    permission = Permission.objects.get(content_type__app_label='admin', codename='delete_logentry')
    response = client.post(reverse('admin:auth_group_change', args=[general.pk]), {
        'name': general.name, 'permissions': [permission.pk], '_save': 'Salvar',
    })

    assert response.status_code == 403
    assert not general.permissions.filter(pk=permission.pk).exists()


# ── Wagtail (/cms/users/) ────────────────────────────────────────────────────


@pytest.mark.django_db
def test_general_admin_cannot_create_superuser_in_wagtail(client, general_admin, current_site):
    client.force_login(general_admin)

    response = client.post(reverse('wagtailusers_users:add'), {
        'username': 'fantoche', 'email': 'fantoche@example.com', 'first_name': 'F', 'last_name': 'T',
        'password1': SENHA_NOVA, 'password2': SENHA_NOVA, 'is_superuser': 'on', 'is_active': 'on',
    })

    assert response.status_code == 302
    assert not CustomUser.objects.filter(username='fantoche').exists()


@pytest.mark.django_db
def test_general_admin_cannot_edit_or_delete_users_in_wagtail(client, general_admin, root, make_panel_user, current_site):
    reporter = make_panel_user('reporter_w', role=CustomUser.Role.REPORTER)
    client.force_login(general_admin)

    for target in (root, reporter):
        edit = client.get(reverse('wagtailusers_users:edit', args=[target.pk]))
        assert edit.status_code == 302
        assert client.post(reverse('wagtailusers_users:delete', args=[target.pk])).status_code == 302
    assert CustomUser.objects.filter(pk__in=[root.pk, reporter.pk]).count() == 2


@pytest.mark.django_db
def test_general_admin_cannot_run_user_bulk_actions_in_wagtail(client, general_admin, root, current_site):
    client.force_login(general_admin)
    url = reverse('wagtail_bulk_action', args=['accounts', 'customuser', 'set_active_state'])

    response = client.post(f'{url}?id={root.pk}', {'mark_as_active': 'False'})

    assert response.status_code == 302
    root.refresh_from_db()
    assert root.is_active


@pytest.mark.django_db
def test_superuser_still_manages_users_in_wagtail(client, root, current_site):
    client.force_login(root)
    assert client.get(reverse('wagtailusers_users:add')).status_code == 200
