import re
from html import unescape

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.accounts.models import CustomUser, GoogleIdentity

SENHA = 'SenhaTeste#2026'


def _input_value(html, name):
    match = re.search(rf'<input[^>]*name="{re.escape(name)}"[^>]*>', html)
    assert match is not None, name
    value = re.search(r'value="([^"]*)"', match.group(0))
    return unescape(value.group(1)) if value else ''


def _change_url(user):
    return reverse('admin:accounts_customuser_change', args=[user.pk])


def _post_user_change(client, user, role, *, is_staff=False):
    response = client.get(_change_url(user))
    assert response.status_code == 200
    html = response.content.decode()
    data = {
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'is_active': 'on',
        'role': role,
        'date_joined_0': _input_value(html, 'date_joined_0'),
        'date_joined_1': _input_value(html, 'date_joined_1'),
        '_save': 'Salvar',
    }
    if user.email_verified:
        data['email_verified'] = 'on'
    if is_staff:
        data['is_staff'] = 'on'
    if user.is_superuser:
        data['is_superuser'] = 'on'
    return client.post(_change_url(user), data)


@pytest.fixture
def admin_user(db, django_user_model):
    return django_user_model.objects.create_superuser(
        username='root-admin',
        email='root-admin@example.com',
        password=SENHA,
    )


@pytest.fixture
def oauth_user(db, django_user_model):
    user = django_user_model.objects.create(
        username='oauth-leitor',
        email='oauth-leitor@example.com',
        first_name='OAuth',
        last_name='Leitor',
        email_verified=True,
    )
    user.set_unusable_password()
    user.save(update_fields=['password'])
    GoogleIdentity.objects.create(user=user, google_sub='google-sub-admin-test', email=user.email)
    return user


@pytest.mark.django_db
def test_admin_change_form_renders_username_for_oauth_user(client, admin_user, oauth_user, current_site):
    client.force_login(admin_user)

    response = client.get(_change_url(oauth_user))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'name="username"' in content
    assert 'value="oauth-leitor"' in content


@pytest.mark.django_db
def test_school_admin_role_promotes_oauth_user_to_staff_and_syncs_group(client, admin_user, oauth_user, current_site):
    client.force_login(admin_user)

    response = _post_user_change(client, oauth_user, CustomUser.Role.SCHOOL_ADMIN)

    assert response.status_code == 302
    oauth_user.refresh_from_db()
    assert oauth_user.role == CustomUser.Role.SCHOOL_ADMIN
    assert oauth_user.is_staff is True
    assert oauth_user.is_superuser is False
    assert list(oauth_user.groups.values_list('name', flat=True)) == ['Administrador Komuniki']


@pytest.mark.django_db
def test_super_admin_role_does_not_grant_superuser(client, admin_user, oauth_user, current_site):
    client.force_login(admin_user)

    response = _post_user_change(client, oauth_user, CustomUser.Role.SUPER_ADMIN)

    assert response.status_code == 302
    oauth_user.refresh_from_db()
    assert oauth_user.role == CustomUser.Role.SUPER_ADMIN
    assert oauth_user.is_staff is True
    assert oauth_user.is_superuser is False
    assert Group.objects.get(name='Administrador Geral') in oauth_user.groups.all()


@pytest.mark.django_db
def test_news_editor_role_does_not_auto_promote_to_staff(client, admin_user, oauth_user, current_site):
    client.force_login(admin_user)

    response = _post_user_change(client, oauth_user, CustomUser.Role.NEWS_EDITOR)

    assert response.status_code == 302
    oauth_user.refresh_from_db()
    assert oauth_user.role == CustomUser.Role.NEWS_EDITOR
    assert oauth_user.is_staff is False
    assert list(oauth_user.groups.values_list('name', flat=True)) == ['Editor de Notícias']
