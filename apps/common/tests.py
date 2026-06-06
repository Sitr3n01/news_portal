import pytest
from django.contrib.auth.models import Group, Permission
from django.contrib.sites.models import Site
from django.test import RequestFactory, override_settings
from django.urls import reverse

from apps.accounts.admin_roles import ensure_admin_role_groups
from apps.common.context_processors import site_context
from apps.common.models import SiteExtension
from apps.school.models import Page, SchoolFeature, SchoolHomeConfig


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
        ('admin_school_guide', 'school.view_page', 'Operação Komuniki'),
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
    assert 'Guia Komuniki' in content
    assert 'Guia do Portal Escolar' not in content
    assert 'Vagas' not in content
    assert 'Candidaturas' not in content
    assert 'Equipe' not in content
    assert 'Guia Editorial' not in content
    assert 'Guia de Gerenciamento' not in content


@pytest.mark.django_db
def test_admin_dashboard_superuser_sees_all_guides(client, django_user_model):
    user = make_staff_user(django_user_model, 'super_user', is_superuser=True)
    client.force_login(user)

    response = client.get(reverse('admin:index'))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'Guia Komuniki' in content
    assert 'Guia Editorial' in content
    assert 'Guia de Gerenciamento' in content


@pytest.mark.django_db
def test_admin_role_groups_are_created_with_operational_permissions():
    ensure_admin_role_groups()

    school_group = Group.objects.get(name='Administrador Komuniki')
    news_group = Group.objects.get(name='Editor de Notícias')
    hiring_group = Group.objects.get(name='Contratações (guardado)')
    general_group = Group.objects.get(name='Administrador Geral')

    assert school_group.permissions.filter(content_type__app_label='school', codename='change_schoolhomeconfig').exists()
    assert school_group.permissions.filter(content_type__app_label='school', codename='change_schoolfeature').exists()
    assert not school_group.permissions.filter(content_type__app_label='school', codename='change_teammember').exists()
    assert not school_group.permissions.filter(content_type__app_label='hiring').exists()
    assert news_group.permissions.filter(content_type__app_label='news', codename='add_article').exists()
    assert not news_group.permissions.filter(content_type__app_label='news', codename='view_articlelike').exists()
    assert hiring_group.permissions.count() == 0
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


@pytest.mark.django_db
def test_legacy_role_groups_are_cleared_and_moved(django_user_model):
    legacy_group = Group.objects.create(name='Administrador Escolar')
    legacy_permission = Permission.objects.get(content_type__app_label='hiring', codename='change_application')
    legacy_group.permissions.add(legacy_permission)
    user = django_user_model.objects.create_user(username='legacy_school', email='legacy@example.com', password='x')
    user.groups.add(legacy_group)

    ensure_admin_role_groups()

    assert not Group.objects.get(name='Administrador Escolar').permissions.exists()
    assert user.groups.filter(name='Administrador Komuniki').exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    'route_name,permission',
    [
        ('admin:school_teammember_changelist', 'school.view_teammember'),
        ('admin:hiring_jobposting_changelist', 'hiring.view_jobposting'),
        ('admin:hiring_department_changelist', 'hiring.view_department'),
        ('admin:hiring_application_changelist', 'hiring.view_application'),
        ('admin:news_articlelike_changelist', 'news.view_articlelike'),
        ('admin:news_articlebookmark_changelist', 'news.view_articlebookmark'),
    ],
)
def test_guarded_admin_models_are_hidden_from_staff(client, django_user_model, route_name, permission):
    user = make_staff_user(django_user_model, f'guarded_{route_name.replace(":", "_")}', [permission])
    client.force_login(user)

    response = client.get(reverse(route_name))

    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    'route_name',
    [
        'admin:school_teammember_changelist',
        'admin:hiring_jobposting_changelist',
        'admin:hiring_department_changelist',
        'admin:hiring_application_changelist',
        'admin:news_articlelike_changelist',
        'admin:news_articlebookmark_changelist',
    ],
)
def test_guarded_admin_models_remain_available_to_superuser(client, django_user_model, route_name):
    user = make_staff_user(django_user_model, f'super_{route_name.replace(":", "_")}', is_superuser=True)
    client.force_login(user)

    response = client.get(reverse(route_name))

    assert response.status_code == 200


@pytest.fixture
def current_site(settings):
    site, _ = Site.objects.update_or_create(
        pk=settings.SITE_ID,
        defaults={'domain': 'testserver', 'name': 'Komuniki Teste'},
    )
    Site.objects.clear_cache()
    return site


@pytest.mark.django_db
@override_settings(
    KOMUNIKI_PUBLIC_URL='https://komuniki.com.br',
    KELLY_BLOG_PUBLIC_URL='https://kellyfarias.com.br/news/',
)
def test_site_context_exposes_public_cross_domain_urls(current_site):
    request = RequestFactory().get('/news/', HTTP_HOST='kellyfarias.com.br')

    context = site_context(request)

    assert context['komuniki_public_url'] == 'https://komuniki.com.br/'
    assert context['kelly_blog_public_url'] == 'https://kellyfarias.com.br/news/'


@pytest.mark.django_db
def test_page_admin_staff_only_sees_courses_page(client, django_user_model, current_site):
    Page.objects.update_or_create(
        site=current_site,
        slug='cursos',
        defaults={'title': 'Cursos', 'is_published': True},
    )
    hidden_page = Page.objects.create(site=current_site, title='Projeto Interno', slug='projeto-interno', is_published=True)
    user = make_staff_user(django_user_model, 'page_editor', ['school.view_page', 'school.change_page'])
    client.force_login(user)

    response = client.get(reverse('admin:school_page_changelist'))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'Cursos' in content
    assert 'Projeto Interno' not in content

    hidden_response = client.get(reverse('admin:school_page_change', args=[hidden_page.pk]))
    assert hidden_response.status_code in (302, 404)


@pytest.mark.django_db
def test_page_admin_staff_cannot_create_generic_pages(client, django_user_model):
    user = make_staff_user(django_user_model, 'page_creator', ['school.add_page', 'school.view_page'])
    client.force_login(user)

    response = client.get(reverse('admin:school_page_add'))

    assert response.status_code == 403


@pytest.mark.django_db
def test_school_feature_admin_staff_only_sees_front_home_placements(client, django_user_model, current_site):
    SchoolFeature.objects.create(
        site=current_site,
        placement=SchoolFeature.Placement.TRUST,
        title='Bloco visível',
        description='Aparece na home.',
    )
    SchoolFeature.objects.create(
        site=current_site,
        placement=SchoolFeature.Placement.PROPOSAL,
        title='Bloco guardado',
        description='Não aparece na home atual.',
    )
    user = make_staff_user(
        django_user_model,
        'feature_editor',
        ['school.view_schoolfeature', 'school.add_schoolfeature'],
    )
    client.force_login(user)

    response = client.get(reverse('admin:school_schoolfeature_changelist'))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'Bloco visível' in content
    assert 'Bloco guardado' not in content

    add_response = client.get(reverse('admin:school_schoolfeature_add'))
    choices = [choice[0] for choice in add_response.context['adminform'].form.fields['placement'].choices]
    assert choices == [SchoolFeature.Placement.TRUST, SchoolFeature.Placement.LIFE]


@pytest.mark.django_db
def test_school_home_admin_staff_hides_legacy_fields(client, django_user_model, current_site):
    home, _ = SchoolHomeConfig.objects.update_or_create(site=current_site, defaults={})
    user = make_staff_user(
        django_user_model,
        'home_editor',
        ['school.view_schoolhomeconfig', 'school.change_schoolhomeconfig'],
    )
    client.force_login(user)

    response = client.get(reverse('admin:school_schoolhomeconfig_change', args=[home.pk]))
    fields = set(response.context['adminform'].form.fields)

    assert response.status_code == 200
    assert 'hero_title_en' in fields
    assert 'team_title' not in fields
    assert 'team_title_en' not in fields
    assert 'team_description' not in fields
    assert 'team_description_en' not in fields
    assert 'proposal_title' not in fields
    assert 'proposal_title_en' not in fields


@pytest.mark.django_db
def test_site_extension_admin_staff_hides_unused_technical_fields(client, django_user_model, current_site):
    extension, _ = SiteExtension.objects.get_or_create(site=current_site)
    user = make_staff_user(
        django_user_model,
        'site_settings_editor',
        ['common.view_siteextension', 'common.change_siteextension'],
    )
    client.force_login(user)

    response = client.get(reverse('admin:common_siteextension_change', args=[extension.pk]))
    fields = set(response.context['adminform'].form.fields)

    assert response.status_code == 200
    assert 'google_analytics_id' not in fields
    assert 'facebook_url' not in fields
    assert 'instagram_url' not in fields
    assert 'youtube_url' not in fields
