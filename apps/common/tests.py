import pytest
from django.contrib.auth.models import Group, Permission
from django.contrib.sites.models import Site
from django.test import RequestFactory, override_settings
from django.urls import NoReverseMatch, reverse

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
    assert 'Guia Editorial' not in content
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

    # Bug A: wagtailadmin.access_admin para ambos os grupos
    assert news_group.permissions.filter(content_type__app_label='wagtailadmin', codename='access_admin').exists(), (
        'Editor de Notícias deve ter wagtailadmin.access_admin'
    )
    assert general_group.permissions.filter(content_type__app_label='wagtailadmin', codename='access_admin').exists(), (
        'Administrador Geral deve ter wagtailadmin.access_admin'
    )

    # Bug A: Editor de Notícias também deve poder ver o snippet NewsHomeConfig
    assert news_group.permissions.filter(content_type__app_label='news', codename='view_newshomeconfig').exists(), (
        'Editor de Notícias deve ter view_newshomeconfig'
    )


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
def test_site_context_reads_site_settings_saved_by_another_worker(current_site):
    SiteExtension.objects.update_or_create(site=current_site, defaults={'tagline': 'Antes'})
    request = RequestFactory().get('/')
    assert site_context(request)['site_settings'].tagline == 'Antes'

    # update() não passa por este processo nem dispara signals, como uma edição salva em outro worker do gunicorn
    SiteExtension.objects.filter(site=current_site).update(tagline='Depois')

    assert site_context(request)['site_settings'].tagline == 'Depois'


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
    # A Home atual só mostra a barra de confiança
    assert choices == [SchoolFeature.Placement.TRUST]


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
    form = response.context['adminform'].form
    fields = set(form.fields)

    assert response.status_code == 200
    assert 'hero_title_en' in fields
    assert 'team_title' not in fields
    assert 'team_title_en' not in fields
    assert 'team_description' not in fields
    assert 'team_description_en' not in fields
    assert 'proposal_title' not in fields
    assert 'proposal_title_en' not in fields
    # Campos do layout anterior que a Home atual não mostra
    assert 'visual_footer_title' not in fields
    assert 'life_title' not in fields
    # Os campos hiring_* alimentam o painel final de cursos, e o rótulo diz isso
    assert form.fields['hiring_title'].label == 'Título da chamada de cursos'


@pytest.mark.django_db
def test_wagtail_snippet_siteextension_list_accessible_by_authorized_staff(client, django_user_model, current_site):
    """Usuário com permissão common.change_siteextension + acesso ao Wagtail admin
    consegue acessar a listagem do Snippet."""
    from apps.common.models import SiteExtension
    SiteExtension.objects.get_or_create(site=current_site)
    user = make_staff_user(
        django_user_model,
        'site_snippet_editor',
        ['common.view_siteextension', 'common.change_siteextension'],
        is_superuser=True,
    )
    client.force_login(user)

    response = client.get(reverse('wagtailsnippets_common_siteextension:list'))

    assert response.status_code == 200

@pytest.mark.django_db
def test_collection_permissions_created_after_ensure_admin_role_groups():
    """Bug B: GroupCollectionPermission rows existem para ambos os grupos após ensure_admin_role_groups()."""
    from wagtail.models import GroupCollectionPermission

    ensure_admin_role_groups()

    expected_codenames = ['add_image', 'choose_image', 'add_document', 'choose_document']

    for group_name in ('Editor de Notícias', 'Administrador Geral'):
        count = GroupCollectionPermission.objects.filter(
            group__name=group_name,
            permission__codename__in=expected_codenames,
        ).count()
        assert count >= 4, (
            f'{group_name}: esperado >= 4 GroupCollectionPermission rows, '
            f'encontrado {count}. Codenames: {expected_codenames}'
        )


def test_admin_news_guide_retired():
    """O guia editorial foi aposentado — a rota não existe mais."""
    with pytest.raises(NoReverseMatch):
        reverse('admin_news_guide')


# ── Integridade do grafo de migrations ─────────────────────────────────────


def test_migration_graph_loads_without_missing_dependencies():
    """Toda dependência declarada por uma migration existe de fato.

    Este teste nasceu de um deploy que quase foi: quatro migrations de `news`
    declaravam depender de `wagtailcore.0098_userprofile`, que NÃO existe no
    Wagtail 7.4.2. O arquivo estava presente na máquina de desenvolvimento
    apenas como resquício de outra versão instalada antes — órfão, fora do
    RECORD da distribuição. Localmente tudo passava; em qualquer instalação
    limpa (CI, produção) o `migrate` morria antes de aplicar a primeira
    migration, com 267 erros de coleta e nenhuma pista do motivo.

    Construir o grafo é o que dá a mensagem direta: aponta a migration e a
    dependência que falta.
    """
    from django.db.migrations.exceptions import NodeNotFoundError
    from django.db.migrations.loader import MigrationLoader

    try:
        loader = MigrationLoader(None, ignore_no_migrations=True)
        loader.graph.validate_consistency()
    except NodeNotFoundError as exc:
        pytest.fail(
            f'Migration com dependência inexistente: {exc}\n'
            'Se a dependência é de um app de terceiro (wagtailcore, taggit...), '
            'confira se a versão fixada em requirements/base.txt realmente traz '
            'aquela migration — e se o seu venv não tem arquivo órfão de outra versão.'
        )


def test_project_migrations_reference_existing_wagtail_nodes():
    """As dependências de wagtailcore usadas pelo projeto existem no Wagtail instalado.

    Complementa o teste acima com uma mensagem específica: em vez de "nó
    ausente", diz qual migration do projeto aponta para onde e o que o Wagtail
    instalado realmente oferece.
    """
    from django.db.migrations.loader import MigrationLoader

    loader = MigrationLoader(None, ignore_no_migrations=True)
    nos_wagtailcore = {nome for app, nome in loader.disk_migrations if app == 'wagtailcore'}
    assert nos_wagtailcore, 'Nenhuma migration de wagtailcore encontrada — Wagtail instalado?'

    apps_do_projeto = {'news', 'cms_media', 'common', 'accounts', 'school', 'social'}
    faltando = []
    for (app, nome), migration in loader.disk_migrations.items():
        if app not in apps_do_projeto:
            continue
        for dep_app, dep_nome in migration.dependencies:
            if dep_app == 'wagtailcore' and dep_nome not in nos_wagtailcore:
                faltando.append(f'{app}.{nome} -> wagtailcore.{dep_nome}')

    assert not faltando, (
        'Migrations do projeto dependem de nós de wagtailcore que não existem na '
        f'versão instalada: {faltando}. Maior nó disponível: {max(nos_wagtailcore)}'
    )


# ── robots.txt ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_robots_txt_bloqueia_busca_e_anuncia_sitemap(client):
    """robots.txt sai como texto puro, barra /news/search/ e aponta o sitemap.

    A busca faz `content__icontains` (ILIKE '%...%') sobre o corpo dos artigos,
    sem indice possivel e com o Paginator executando a consulta duas vezes —
    manter crawler fora dela e o maior ganho de CPU do portal.
    """
    response = client.get('/robots.txt')

    assert response.status_code == 200
    assert response['Content-Type'].startswith('text/plain')

    body = response.content.decode()
    assert 'Disallow: /news/search/' in body
    assert 'Disallow: /cms/' in body
    assert 'Disallow: /admin/' in body


@pytest.mark.django_db
def test_robots_txt_usa_o_host_da_request(client):
    """A linha Sitemap: segue o host, porque dois dominios dividem esta aplicacao.

    Um caminho absoluto fixo apontaria o crawler de um dominio para o outro.
    """
    response = client.get('/robots.txt', HTTP_HOST='kellyfarias.com.br')

    assert 'Sitemap: http://kellyfarias.com.br/sitemap.xml' in response.content.decode()


# ── Tetos de upload de imagem: os dois caminhos não podem divergir ──────────


def test_teto_de_upload_do_wagtail_casa_com_o_validador_legado(settings):
    """WAGTAILIMAGES_MAX_UPLOAD_SIZE espelha validators.MAX_UPLOAD_BYTES.

    O numero e repetido em config/settings/base.py porque settings e avaliado antes
    do app registry — nao da para importar apps.common.validators la. Este teste e a
    trava contra os dois valores divergirem em silencio, deixando o upload por
    /cms/images/ mais permissivo que o dos campos legados.
    """
    from apps.common.validators import ALLOWED_IMAGE_EXTENSIONS, MAX_UPLOAD_BYTES

    assert settings.WAGTAILIMAGES_MAX_UPLOAD_SIZE == MAX_UPLOAD_BYTES
    assert set(settings.WAGTAILIMAGES_EXTENSIONS) == {
        ext.lstrip('.') for ext in ALLOWED_IMAGE_EXTENSIONS
    }


def test_teto_de_pixels_fica_abaixo_do_default_do_wagtail(settings):
    """O default do Wagtail e 128 MP — decode suficiente para derrubar o worker.

    Ver wagtail/images/fields.py: sem a setting, um unico upload pode fazer o Pillow
    alocar centenas de MB dentro de um container limitado a 1500M.
    """
    assert settings.WAGTAILIMAGES_MAX_IMAGE_PIXELS < 128 * 1_000_000


# ── scan_orphan_media: o HTML legado não tem FK que o rastreie ──────────────


def _escreve(media_root, caminho_relativo):
    destino = media_root / caminho_relativo
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(b'conteudo-de-teste')
    return destino


@pytest.mark.django_db
def test_scan_orphan_media_nao_marca_arquivo_citado_no_html_legado(settings, tmp_path, current_site):
    """Imagem referenciada só em Article.content não pode virar órfã.

    É a razão de o comando existir: `content` guarda HTML legado com
    `<img src="/media/...">` e nenhuma chave estrangeira aponta para esse
    arquivo. Uma varredura por FK sozinha o apagaria — quebrando a imagem de um
    artigo publicado.
    """
    from io import StringIO

    from django.core.management import call_command

    from apps.news.models import Article

    settings.MEDIA_ROOT = str(tmp_path)
    _escreve(tmp_path, 'news/articles/citada-no-html.jpg')
    _escreve(tmp_path, 'media_library/files/ninguem-usa.png')

    Article.objects.create(
        title='Artigo com imagem embutida', slug='imagem-embutida',
        content='<p>texto</p><img src="/media/news/articles/citada-no-html.jpg">',
        site=current_site, status=Article.Status.PUBLISHED,
    )

    saida = StringIO()
    call_command('scan_orphan_media', stdout=saida)
    texto = saida.getvalue()

    assert 'citada-no-html.jpg' not in texto, 'imagem do HTML legado foi marcada como órfã'
    assert 'ninguem-usa.png' in texto
    assert 'Referências embutidas em texto: 1' in texto


@pytest.mark.django_db
def test_scan_orphan_media_marca_original_do_wagtail_como_risco_alto(settings, tmp_path):
    """Órfão em original_images/ sai como RISCO ALTO, sem linha `rm` pronta.

    É o original do Wagtail: apagar um que ainda esteja em uso destrói a
    regeneração de todas as renditions daquela imagem.
    """
    from io import StringIO

    from django.core.management import call_command

    settings.MEDIA_ROOT = str(tmp_path)
    _escreve(tmp_path, 'original_images/capa-solta.jpg')

    saida = StringIO()
    call_command('scan_orphan_media', stdout=saida)
    texto = saida.getvalue()

    assert 'RISCO ALTO' in texto
    assert 'capa-solta.jpg' in texto
    assert "rm '" not in texto, 'original do Wagtail não deve vir com rm pronto'


@pytest.mark.django_db
def test_scan_orphan_media_ignora_dotfiles(settings, tmp_path):
    """.gitkeep é marcador estrutural, não lixo."""
    from io import StringIO

    from django.core.management import call_command

    settings.MEDIA_ROOT = str(tmp_path)
    _escreve(tmp_path, '.gitkeep')

    saida = StringIO()
    call_command('scan_orphan_media', stdout=saida)

    assert 'Nenhum órfão' in saida.getvalue()


@pytest.mark.django_db
def test_scan_orphan_media_enxerga_referencia_em_pagina_da_escola(settings, tmp_path, current_site):
    """Imagem citada só em school.Page.content não pode virar órfã.

    Era o furo da primeira versão do comando: ela varria apenas
    `Article.content` e `Article.body`, então uma imagem em uso numa página da
    escola — TextField com HTML sanitizado, mesmo caso do `content` legado do
    artigo — aparecia como órfã e seria removida.
    """
    from io import StringIO

    from django.core.management import call_command

    from apps.school.models import Page

    settings.MEDIA_ROOT = str(tmp_path)
    _escreve(tmp_path, 'school/pages/usada-na-escola.jpg')
    _escreve(tmp_path, 'school/pages/ninguem-usa.jpg')

    Page.objects.create(
        site=current_site, title='Cursos', slug='cursos-scan', is_published=True,
        content='<p>texto</p><img src="/media/school/pages/usada-na-escola.jpg">',
    )

    saida = StringIO()
    call_command('scan_orphan_media', stdout=saida)
    texto = saida.getvalue()

    assert 'usada-na-escola.jpg' not in texto, 'imagem de página da escola foi marcada como órfã'
    assert 'ninguem-usa.jpg' in texto


@pytest.mark.django_db
def test_scan_orphan_media_enxerga_referencia_no_streamfield(settings, tmp_path, current_site):
    """Imagem citada só no StreamField do artigo também conta como em uso.

    Trava da detecção por `get_internal_type()`: o StreamField do Wagtail herda
    direto de `models.Field` — não de TextField nem de JSONField — mas se declara
    como JSONField no banco. Detectar por `isinstance` perderia `Article.body`.
    """
    from io import StringIO

    from django.core.management import call_command

    from apps.news.models import Article

    settings.MEDIA_ROOT = str(tmp_path)
    _escreve(tmp_path, 'news/articles/dentro-do-streamfield.jpg')

    Article.objects.create(
        title='Artigo com StreamField', slug='streamfield-scan',
        site=current_site, status=Article.Status.PUBLISHED,
        body=[
            {'type': 'texto', 'value': '<p><img src="/media/news/articles/dentro-do-streamfield.jpg"></p>'},
        ],
    )

    saida = StringIO()
    call_command('scan_orphan_media', stdout=saida)

    assert 'dentro-do-streamfield.jpg' not in saida.getvalue()
