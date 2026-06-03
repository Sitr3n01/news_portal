import pytest
from django.contrib.auth.models import Group, Permission
from django.urls import reverse

from apps.accounts.admin_roles import ensure_admin_role_groups


@pytest.fixture(autouse=True)
def staticfiles_storage(settings):
    settings.STORAGES = {
        **settings.STORAGES,
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }


def make_staff_user(django_user_model, username, permissions=None, is_superuser=False):
    user = django_user_model.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password='SenhaTeste#2026',
        is_staff=True,
        is_superuser=is_superuser,
    )
    for permission in permissions or []:
        app_label, codename = permission.split('.')
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app_label, codename=codename)
        )
    return user


@pytest.mark.django_db
def test_admin_guides_require_staff_login(client):
    response = client.get(reverse('admin_school_guide'))

    assert response.status_code == 302
    assert reverse('admin:login') in response['Location']


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('route_name', 'permission', 'expected_text'),
    [
        ('admin_school_guide', 'school.view_page', 'Operação do Portal Escolar'),
        ('admin_news_guide', 'news.view_article', 'Operação Editorial'),
        ('admin_management_guide', 'accounts.view_customuser', 'Operação e Configurações'),
    ],
)
def test_admin_guides_render_for_authorized_staff(client, django_user_model, route_name, permission, expected_text):
    user = make_staff_user(django_user_model, f'user_{route_name}', [permission])
    client.force_login(user)

    response = client.get(reverse(route_name))

    assert response.status_code == 200
    assert expected_text in response.content.decode()


@pytest.mark.django_db
def test_admin_dashboard_guide_cards_follow_permissions(client, django_user_model):
    school_user = make_staff_user(django_user_model, 'school_user', ['school.view_page'])
    client.force_login(school_user)

    response = client.get(reverse('admin:index'))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'Guia do Portal Escolar' in content
    assert 'Guia Editorial' not in content
    assert 'Guia de Gerenciamento' not in content


@pytest.mark.django_db
def test_admin_dashboard_superuser_sees_all_guides(client, django_user_model):
    user = make_staff_user(django_user_model, 'super_user', is_superuser=True)
    client.force_login(user)

    response = client.get(reverse('admin:index'))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'Guia do Portal Escolar' in content
    assert 'Guia Editorial' in content
    assert 'Guia de Gerenciamento' in content


@pytest.mark.django_db
def test_admin_role_groups_are_created_with_operational_permissions():
    ensure_admin_role_groups()

    school_group = Group.objects.get(name='Administrador Escolar')
    news_group = Group.objects.get(name='Editor de Notícias')
    hiring_group = Group.objects.get(name='Contratações')
    general_group = Group.objects.get(name='Administrador Geral')

    assert school_group.permissions.filter(content_type__app_label='school', codename='change_schoolhomeconfig').exists()
    assert news_group.permissions.filter(content_type__app_label='news', codename='add_article').exists()
    assert hiring_group.permissions.filter(content_type__app_label='hiring', codename='change_application').exists()
    assert general_group.permissions.filter(content_type__app_label='accounts', codename='view_customuser').exists()


@pytest.mark.django_db
def test_role_change_revokes_previous_role_group_but_keeps_manual_groups(django_user_model):
    from apps.accounts.admin_roles import sync_user_role_group

    user = django_user_model.objects.create_user(
        username='rotated_user',
        email='rotated@example.com',
        password='SenhaTeste#2026',
        role='super_admin',
    )
    manual_group = Group.objects.create(name='Equipe Especial')
    user.groups.add(manual_group)

    sync_user_role_group(user)
    assert user.groups.filter(name='Administrador Geral').exists()

    # Rebaixa o cargo: o grupo do cargo anterior deve ser revogado (sem privilégio residual).
    user.role = 'news_editor'
    user.save()
    sync_user_role_group(user)

    assert not user.groups.filter(name='Administrador Geral').exists()
    assert user.groups.filter(name='Editor de Notícias').exists()
    # Grupo atribuído manualmente (fora do mapa role->grupo) é preservado.
    assert user.groups.filter(name='Equipe Especial').exists()
