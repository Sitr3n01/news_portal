"""Testes do painel administrativo unificado (apps/common/newsroom).

Cobrem: destino pós-login, acesso à visão geral, permissões por cargo na
navegação, isolamento entre os espaços de trabalho (Blog da Kelly × Komuniki),
busca/filtros/paginação no servidor, links oficiais de criação e edição,
reflexo dos fluxos nativos do Wagtail (rascunho, revisão, publicação), a casca
única nas telas do Wagtail e do Django admin, proteção contra acesso indevido e
preservação das rotas existentes.
"""

import pytest
from django.contrib.sites.models import Site
from django.urls import resolve, reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.contact.models import ContactInquiry
from apps.news.models import Article, Category, Comment, NewsletterSubscription

SENHA = 'SenhaTeste#2026'


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def site(current_site):
    return current_site


@pytest.fixture
def reporter(make_panel_user):
    return make_panel_user('nr_reporter', role=CustomUser.Role.REPORTER)


@pytest.fixture
def editor(make_panel_user):
    """Editor de Notícias SEM is_staff — o caso real do cargo."""
    return make_panel_user('nr_editor', role=CustomUser.Role.NEWS_EDITOR)


@pytest.fixture
def komuniki_admin(make_panel_user):
    return make_panel_user('nr_komuniki', role=CustomUser.Role.SCHOOL_ADMIN, is_staff=True)


@pytest.fixture
def root(make_panel_user):
    return make_panel_user('nr_root', role=CustomUser.Role.SUPER_ADMIN, is_staff=True, is_superuser=True)


@pytest.fixture
def leitor(make_panel_user):
    return make_panel_user('nr_leitor', role=CustomUser.Role.READER)


def _article(site, title, status=Article.Status.DRAFT, category=None, author=None, **extra):
    """Artigo válido para revisões do Wagtail (full_clean exige autor e categoria)."""
    slug = title.lower().replace(' ', '-')
    if category is None:
        category, _ = Category.objects.get_or_create(slug='geral', defaults={'name': 'Geral'})
    if author is None:
        author, _ = CustomUser.objects.get_or_create(username='nr_autor', defaults={'email': 'autor@example.com'})
    return Article.objects.create(
        title=title, slug=slug, content='<p>.</p>', site=site, status=status,
        category=category, author=author, **extra,
    )


def _nav_keys(response):
    nav = response.context['nav']
    keys = [item['key'] for group in nav['groups'] for item in group['items']]
    keys += [item['key'] for section in nav['sections'] for item in section['items']]
    return keys


def _row_titles(response):
    return [row['title'] for row in response.context['listing']['rows']]


# ── Login e acesso à visão geral ───────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize('fixture_name', ['reporter', 'editor', 'komuniki_admin', 'root'])
def test_login_lands_on_dashboard_for_every_admin_role(client, request, fixture_name):
    user = request.getfixturevalue(fixture_name)

    response = client.post(reverse('panel:login'), {'username': user.username, 'password': SENHA})

    assert response.status_code == 302
    assert response.url == reverse('panel:dashboard')
    assert client.get(response.url).status_code == 200


@pytest.mark.django_db
def test_dashboard_requires_authentication(client):
    response = client.get(reverse('panel:dashboard'))

    assert response.status_code == 302
    assert response.url.startswith(reverse('panel:login'))
    assert 'next=/painel/' in response.url


@pytest.mark.django_db
def test_dashboard_refuses_user_without_admin_area(client, leitor):
    """Autenticação não é autorização: leitor logado não entra no painel."""
    client.force_login(leitor)

    response = client.get(reverse('panel:dashboard'))

    assert response.status_code == 302
    assert response.url == reverse('panel:no_access')


@pytest.mark.django_db
def test_dashboard_only_accepts_get(client, root):
    client.force_login(root)

    assert client.post(reverse('panel:dashboard')).status_code == 405


# ── Páginas iniciais antigas: redirecionam, mas atrás das portas originais ──


@pytest.mark.django_db
def test_cms_home_redirect_keeps_wagtail_gate(client, leitor, reporter):
    anonymous = client.get('/cms/')
    assert anonymous.status_code == 302
    assert anonymous.url.startswith(reverse('panel:login'))

    client.force_login(leitor)
    negado = client.get('/cms/')
    assert negado.status_code == 302
    assert negado.url != reverse('panel:dashboard')

    client.force_login(reporter)
    assert client.get('/cms/').url == reverse('panel:dashboard')


@pytest.mark.django_db
def test_admin_index_redirect_keeps_admin_gate(client, reporter, root):
    client.force_login(reporter)
    negado = client.get('/admin/')
    assert negado.status_code == 302
    assert negado.url.startswith(reverse('admin:login'))

    client.force_login(root)
    assert client.get('/admin/').url == reverse('panel:dashboard')


# ── Navegação por permissão ────────────────────────────────────────────────


@pytest.mark.django_db
def test_reporter_navigation_is_editorial_only(client, reporter):
    client.force_login(reporter)

    keys = _nav_keys(client.get(reverse('panel:dashboard')))

    assert {'overview', 'articles', 'review', 'images'} <= set(keys)
    # Repórter não modera comentários, não vê newsletter nem administração.
    for hidden in ('comments', 'newsletter', 'users', 'groups', 'site_settings', 'messages', 'testimonials'):
        assert hidden not in keys


@pytest.mark.django_db
def test_editor_reaches_comments_and_newsletter_through_wagtail(client, editor):
    """O editor tem as permissões de moderação, mas não é is_staff: antes nunca
    alcançava essas telas. Agora elas estão no Wagtail, atrás da porta dele."""
    client.force_login(editor)

    keys = _nav_keys(client.get(reverse('panel:dashboard')))

    assert {'comments', 'newsletter', 'newsletter_deliveries', 'categories', 'tags', 'news_home'} <= set(keys)
    # Nada do /admin/, cuja porta exige is_staff.
    for hidden in ('users', 'groups', 'messages', 'school_pages', 'newsletter_legacy',
                   'access_lockouts', 'wagtail-redirects'):
        assert hidden not in keys
    assert client.get(reverse('wagtailsnippets_news_comment:list')).status_code == 200


@pytest.mark.django_db
def test_komuniki_admin_navigation_is_school_only(client, komuniki_admin):
    client.force_login(komuniki_admin)

    keys = _nav_keys(client.get(reverse('panel:dashboard')))

    assert {'messages', 'school_pages', 'school_home', 'school_features', 'media_files'} <= set(keys)
    for hidden in ('articles', 'review', 'comments', 'images', 'users'):
        assert hidden not in keys
    # Depoimentos continuam "guardados" (só superusuário), como no menu anterior,
    # mesmo com o grupo tendo a permissão do modelo.
    assert 'testimonials' not in keys


@pytest.mark.django_db
def test_superuser_sees_administration_and_stored_resources(client, root):
    client.force_login(root)

    keys = _nav_keys(client.get(reverse('panel:dashboard')))

    assert {'users', 'groups', 'site_settings', 'testimonials', 'jobs', 'newsletter_legacy'} <= set(keys)
    # Telas do django-axes (desbloquear conta) e redirecionamentos do Wagtail,
    # antes alcançáveis só digitando a URL.
    assert {'access_lockouts', 'access_log', 'access_failures', 'wagtail-redirects'} <= set(keys)
    # Ferramentas de revisão do Wagtail vêm do próprio menu do Wagtail.
    assert 'wagtail-site-history' in keys
    # Telas de páginas do Wagtail (não usadas pelo projeto) ficam fora do menu.
    assert 'wagtail-locked-pages' not in keys


@pytest.mark.django_db
def test_nav_badges_use_real_counts(client, root, site):
    art = _article(site, 'Com comentarios', status=Article.Status.PUBLISHED)
    Comment.objects.create(article=art, user=root, content='pendente', is_active=False)
    Comment.objects.create(article=art, user=root, content='visível', is_active=True)
    client.force_login(root)

    nav = client.get(reverse('panel:dashboard')).context['nav']
    badges = {item['key']: item['badge'] for group in nav['groups'] for item in group['items']}

    assert badges['articles'] == {'count': 1, 'tone': ''}
    assert badges['comments'] == {'count': 1, 'tone': 'alert'}
    # Selo de alerta com zero some, em vez de mostrar "0 pendentes".
    assert badges['review'] is None


# ── Espaços de trabalho e isolamento ───────────────────────────────────────


@pytest.mark.django_db
def test_workspaces_offered_follow_permissions(client, editor, komuniki_admin, root):
    client.force_login(editor)
    assert [ws.key for ws in client.get(reverse('panel:dashboard')).context['nav']['workspaces']] == ['kelly']

    client.force_login(komuniki_admin)
    assert [ws.key for ws in client.get(reverse('panel:dashboard')).context['nav']['workspaces']] == ['komuniki']

    client.force_login(root)
    assert [ws.key for ws in client.get(reverse('panel:dashboard')).context['nav']['workspaces']] == ['kelly', 'komuniki']


@pytest.mark.django_db
def test_workspaces_isolate_dashboard_data(client, root, site):
    _article(site, 'Pauta secreta do blog')
    ContactInquiry.objects.create(site=site, name='Visitante Komuniki', email='v@example.com', message='Oi')
    client.force_login(root)

    blog = client.get(reverse('panel:dashboard')).content.decode()
    assert 'Pauta secreta do blog' in blog
    assert 'Visitante Komuniki' not in blog

    client.post(reverse('panel:workspace'), {'workspace': 'komuniki'})
    komuniki = client.get(reverse('panel:dashboard')).content.decode()
    assert 'Visitante Komuniki' in komuniki
    assert 'Pauta secreta do blog' not in komuniki


@pytest.mark.django_db
def test_workspace_switch_rejects_unavailable_workspace(client, editor):
    client.force_login(editor)

    response = client.post(reverse('panel:workspace'), {'workspace': 'komuniki'})

    assert response.status_code == 302
    assert 'newsroom_workspace' not in client.session
    assert client.get(reverse('panel:dashboard')).context['workspace'].key == 'kelly'


@pytest.mark.django_db
def test_workspace_switch_requires_post(client, root):
    client.force_login(root)

    assert client.get(reverse('panel:workspace')).status_code == 405


@pytest.mark.django_db
def test_screen_workspace_wins_over_session(client, root):
    """Abrir uma tela da Komuniki mostra a navegação da Komuniki, mesmo com o
    Blog da Kelly escolhido na sessão."""
    client.force_login(root)

    response = client.get(reverse('admin:contact_contactinquiry_changelist'))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'nr-workspace__title">Komuniki<' in content
    assert 'aria-current="page"' in content


@pytest.mark.django_db
def test_komuniki_admin_cannot_read_articles_through_dashboard(client, komuniki_admin, site):
    _article(site, 'Rascunho restrito')
    client.force_login(komuniki_admin)

    response = client.get(reverse('panel:dashboard'), {'status': 'draft', 'q': 'restrito'})

    assert 'Rascunho restrito' not in response.content.decode()
    assert response.context['listing']['kind'] == 'messages'


# ── Busca, filtros e paginação (no servidor) ───────────────────────────────


@pytest.mark.django_db
def test_articles_are_paginated_server_side(client, editor, site):
    for index in range(13):
        _article(site, f'Materia {index:02d}')
    client.force_login(editor)

    first = client.get(reverse('panel:dashboard'))
    second = client.get(reverse('panel:dashboard'), {'page': 2})

    assert len(_row_titles(first)) == 10
    assert len(_row_titles(second)) == 3
    assert set(_row_titles(first)).isdisjoint(_row_titles(second))
    assert first.context['listing']['next_url'] == '?page=2'
    assert 'Exibindo 1–10 de 13' in first.content.decode()


@pytest.mark.django_db
def test_search_filters_by_title(client, editor, site):
    _article(site, 'Educacao digital na escola')
    _article(site, 'Agenda cultural')
    client.force_login(editor)

    response = client.get(reverse('panel:dashboard'), {'q': 'digital'})

    assert _row_titles(response) == ['Educacao digital na escola']


@pytest.mark.django_db
def test_status_and_category_filters(client, editor, site):
    cultura = Category.objects.create(name='Cultura', slug='cultura')
    _article(site, 'Publicada cultura', status=Article.Status.PUBLISHED, category=cultura)
    _article(site, 'Rascunho cultura', category=cultura)
    _article(site, 'Arquivada', status=Article.Status.ARCHIVED)
    client.force_login(editor)

    published = client.get(reverse('panel:dashboard'), {'status': 'published'})
    drafts = client.get(reverse('panel:dashboard'), {'status': 'draft', 'categoria': cultura.pk})
    archived = client.get(reverse('panel:dashboard'), {'status': 'archived'})
    invalid = client.get(reverse('panel:dashboard'), {'status': 'qualquer', 'categoria': 'x'})

    assert _row_titles(published) == ['Publicada cultura']
    assert _row_titles(drafts) == ['Rascunho cultura']
    assert _row_titles(archived) == ['Arquivada']
    assert len(_row_titles(invalid)) == 3
    assert invalid.context['listing']['status'] == 'all'


@pytest.mark.django_db
def test_htmx_request_returns_only_results(client, editor, site):
    _article(site, 'Resultado parcial')
    client.force_login(editor)

    response = client.get(reverse('panel:dashboard'), {'q': 'parcial'}, HTTP_HX_REQUEST='true')

    content = response.content.decode()
    assert 'id="nr-results"' in content
    assert 'id="nr-tabs"' in content
    assert 'Resultado parcial' in content
    # Nem casca nem campo de busca: o foco e o texto digitado ficam intactos.
    assert 'nr-sidebar' not in content
    assert 'id="nr-search"' not in content


@pytest.mark.django_db
def test_listing_query_count_does_not_grow_with_rows(client, editor, site):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    def count_queries():
        client.get(reverse('panel:dashboard'), HTTP_HX_REQUEST='true')  # aquece caches por requisição
        with CaptureQueriesContext(connection) as context:
            client.get(reverse('panel:dashboard'), HTTP_HX_REQUEST='true')
        return len(context.captured_queries)

    client.force_login(editor)
    for index in range(2):
        _article(site, f'Carga {index}')
    few = count_queries()
    for index in range(2, 10):
        _article(site, f'Carga {index}')
    many = count_queries()

    assert many == few


@pytest.mark.django_db
def test_grid_view_uses_same_rows(client, editor, site):
    _article(site, 'Mesma fonte')
    client.force_login(editor)

    as_list = client.get(reverse('panel:dashboard'))
    as_grid = client.get(reverse('panel:dashboard'), {'view': 'grid'})

    assert _row_titles(as_list) == _row_titles(as_grid)
    assert 'nr-article-list is-grid' in as_grid.content.decode()
    assert 'nr-article-list is-grid' not in as_list.content.decode()


# ── Links de criação/edição e ações nativas ────────────────────────────────


@pytest.mark.django_db
def test_new_article_button_points_to_wagtail_create_view(client, reporter):
    client.force_login(reporter)

    response = client.get(reverse('panel:dashboard'))

    assert response.context['primary_action']['url'] == reverse('wagtailsnippets_news_article:add')
    assert client.get(reverse('wagtailsnippets_news_article:add')).status_code == 200


@pytest.mark.django_db
def test_row_actions_follow_permissions(client, reporter, editor, site):
    article = _article(site, 'Acoes da linha')
    article.save_revision().publish()
    client.force_login(reporter)
    row = client.get(reverse('panel:dashboard')).context['listing']['rows'][0]
    actions = {a['label']: a['url'] for a in row['actions']}

    # Notícia PUBLICADA de um colega: o repórter só vê a ficha, não edita.
    inspect_url = reverse('wagtailsnippets_news_article:inspect', args=[article.pk])
    assert 'Editar' not in actions
    assert actions['Ver'] == inspect_url
    assert row['edit_url'] == inspect_url
    assert actions['Histórico'] == reverse('wagtailsnippets_news_article:history', args=[article.pk])
    # Repórter não publica nem exclui: as ações nem aparecem.
    assert 'Despublicar' not in actions
    assert 'Excluir' not in actions

    client.force_login(editor)
    actions = {a['label']: a['url'] for a in client.get(reverse('panel:dashboard')).context['listing']['rows'][0]['actions']}
    assert actions['Editar'] == reverse('wagtailsnippets_news_article:edit', args=[article.pk])
    assert actions['Despublicar'] == reverse('wagtailsnippets_news_article:unpublish', args=[article.pk])
    assert actions['Excluir'] == reverse('wagtailsnippets_news_article:delete', args=[article.pk])


@pytest.mark.django_db
def test_listing_reflects_native_draft_review_and_publish_flows(client, editor, site):
    """A visão geral só LÊ o estado: rascunho, revisão e publicação acontecem
    pelos mecanismos do Wagtail (revisões e fluxo de trabalho)."""
    article = _article(site, 'Fluxo completo', author=editor)
    client.force_login(editor)

    def state():
        rows = client.get(reverse('panel:dashboard')).context['listing']['rows']
        return next(row['state'] for row in rows if row['pk'] == article.pk)

    article.save_revision(user=editor)
    assert state() == 'draft'

    article.get_default_workflow().start(article, editor)
    assert state() == 'review'
    review = client.get(reverse('panel:dashboard'), {'status': 'review'})
    assert _row_titles(review) == ['Fluxo completo']

    # Publicar (ação nativa) encerra o fluxo em andamento.
    article.refresh_from_db()
    article.get_latest_revision().publish(user=editor)
    assert state() == 'published'

    article.refresh_from_db()
    article.unpublish()
    assert state() == 'archived'


@pytest.mark.django_db
def test_scheduled_article_is_flagged(client, editor, site):
    # "Agendar publicação" no Wagtail = publicar uma revisão com data futura.
    scheduled = _article(site, 'Agendada', live=False, go_live_at=timezone.now() + timezone.timedelta(days=1))
    scheduled.save_revision().publish()
    # Só a data preenchida e o rascunho salvo não agendam nada.
    _article(site, 'Com data sem agendar', live=False, go_live_at=timezone.now() + timezone.timedelta(days=1)).save_revision()
    client.force_login(editor)

    response = client.get(reverse('panel:dashboard'), {'status': 'scheduled'})
    everything = client.get(reverse('panel:dashboard'), {'status': 'all'})

    assert _row_titles(response) == ['Agendada']
    assert response.context['listing']['rows'][0]['state_label'] == 'Agendada'
    labels = {row['title']: row['state_label'] for row in everything.context['listing']['rows']}
    assert labels['Com data sem agendar'] == 'Rascunho'


# ── Casca única nas telas dos dois frameworks ──────────────────────────────


@pytest.mark.django_db
def test_wagtail_screens_use_the_unified_sidebar(client, editor, settings):
    client.force_login(editor)

    content = client.get(reverse('wagtailsnippets_news_article:list')).content.decode()

    assert 'id="nr-sidebar"' in content
    assert 'data-wagtail-sidebar' not in content  # sidebar React do Wagtail substituída
    assert 'newsroom/css/newsroom-wagtail' in content
    assert '<a class="nr-nav__item is-active" href="/cms/snippets/news/article/" aria-current="page">' in content
    # O atalho para o portal público (antes "Visualizar Portais" no Unfold e
    # "Ver portal" no Wagtail) fica no seletor de espaço, presente em toda tela.
    assert f'href="{settings.KELLY_BLOG_PUBLIC_URL}"' in content


@pytest.mark.django_db
def test_bulk_actions_footer_has_no_select_all_checkbox(client, editor, site):
    """A caixa "Selecionar todos" fica só no cabeçalho da tabela; o rodapé de
    ações em massa mostra apenas as ações e a contagem."""
    _article(site, 'Para selecionar')
    client.force_login(editor)

    content = client.get(reverse('wagtailsnippets_news_article:list')).content.decode()
    footer = content[content.index('data-bulk-action-footer'):]
    footer = footer[:footer.index('</section>')]

    assert 'data-bulk-action-select-all-checkbox' in content  # cabeçalho
    assert 'data-bulk-action-select-all-checkbox' not in footer
    assert 'bulk-actions-buttons' in footer
    assert 'data-bulk-action-num-objects' in footer


@pytest.mark.django_db
def test_block_editor_loads_drag_to_reorder_script_only_on_forms(client, editor, site):
    article = _article(site, 'Blocos para arrastar')
    client.force_login(editor)

    edit = client.get(reverse('wagtailsnippets_news_article:edit', args=[article.pk]))
    add = client.get(reverse('wagtailsnippets_news_article:add'))
    listing = client.get(reverse('wagtailsnippets_news_article:list'))

    # Hook insert_editor_js: formulários de criação e edição, nunca listagens.
    assert edit.status_code == 200
    assert 'newsroom/js/newsroom-streamfield.js' in edit.content.decode()
    assert 'newsroom/js/newsroom-streamfield.js' in add.content.decode()
    assert 'newsroom/js/newsroom-streamfield.js' not in listing.content.decode()


@pytest.mark.django_db
def test_admin_screens_use_the_unified_sidebar_and_topbar(client, root):
    client.force_login(root)

    content = client.get(reverse('admin:accounts_customuser_changelist')).content.decode()

    assert 'id="nr-sidebar"' in content
    assert 'class="nr-topbar"' in content
    assert 'newsroom/css/newsroom-unfold' in content
    assert 'Equipe e usuários' in content


@pytest.mark.django_db
def test_shell_logout_posts_to_unified_logout(client, root):
    client.force_login(root)

    content = client.get(reverse('panel:dashboard')).content.decode()

    assert f'action="{reverse("panel:logout")}"' in content
    response = client.post(reverse('panel:logout'), {'next': reverse('panel:login')})
    assert response.url == reverse('panel:login')
    assert '_auth_user_id' not in client.session


# ── Comentários e newsletter no Wagtail ────────────────────────────────────


@pytest.mark.django_db
def test_comment_snippet_blocks_creation_even_for_superuser(client, root):
    client.force_login(root)

    response = client.get(reverse('wagtailsnippets_news_comment:add'))

    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_editor_moderates_comment_without_changing_its_text(client, editor, site):
    article = _article(site, 'Com moderacao', status=Article.Status.PUBLISHED)
    comment = Comment.objects.create(article=article, user=editor, content='Texto original', is_active=False)
    client.force_login(editor)

    response = client.post(
        reverse('wagtailsnippets_news_comment:edit', args=[comment.pk]),
        {'is_active': 'on', 'content': 'Texto adulterado'},
    )

    assert response.status_code == 302
    comment.refresh_from_db()
    assert comment.is_active is True
    assert comment.content == 'Texto original'


@pytest.mark.django_db
def test_bulk_approve_and_hide_comments(client, editor, reporter, site):
    article = _article(site, 'Em massa', status=Article.Status.PUBLISHED)
    first = Comment.objects.create(article=article, user=editor, content='um', is_active=False)
    second = Comment.objects.create(article=article, user=editor, content='dois', is_active=False)
    url = reverse('wagtail_bulk_action', args=('news', 'comment', 'approve_comments'))
    query = f'?id={first.pk}&id={second.pk}'

    client.force_login(reporter)
    client.post(url + query)
    assert Comment.objects.filter(is_active=True).count() == 0

    client.force_login(editor)
    response = client.post(url + query)
    assert response.status_code == 302
    assert Comment.objects.filter(is_active=True).count() == 2

    hide = reverse('wagtail_bulk_action', args=('news', 'comment', 'hide_comments'))
    client.post(hide + f'?id={first.pk}')
    first.refresh_from_db()
    assert first.is_active is False


@pytest.mark.django_db
def test_newsletter_deliveries_are_read_only_in_wagtail(client, editor):
    client.force_login(editor)

    assert client.get(reverse('wagtailsnippets_news_newsletterdelivery:list')).status_code == 200
    assert client.get(reverse('wagtailsnippets_news_newsletterdelivery:add')).status_code in (302, 403)


@pytest.mark.django_db
def test_bulk_deactivate_subscriptions(client, editor, site):
    subscription = NewsletterSubscription.objects.create(email='x@example.com', site=site)
    client.force_login(editor)

    url = reverse('wagtail_bulk_action', args=('news', 'newslettersubscription', 'deactivate_subscriptions'))
    client.post(url + f'?id={subscription.pk}')

    subscription.refresh_from_db()
    assert subscription.is_active is False


@pytest.mark.django_db
def test_editor_still_cannot_open_django_admin_copies(client, editor):
    """A migração não ampliou a porta do /admin/: o editor continua fora."""
    client.force_login(editor)

    response = client.get(reverse('admin:news_comment_changelist'))

    assert response.status_code == 302
    assert response.url.startswith(reverse('admin:login'))


# ── Nenhum dado inventado ──────────────────────────────────────────────────


@pytest.mark.django_db
def test_stats_come_from_the_database(client, root, site):
    _article(site, 'P1', status=Article.Status.PUBLISHED, published_at=timezone.now())
    _article(site, 'R1')
    client.force_login(root)

    stats = {stat['label']: stat for stat in client.get(reverse('panel:dashboard')).context['stats']}

    assert stats['Publicadas']['value'] == Article.objects.filter(status=Article.Status.PUBLISHED).count()
    assert stats['Rascunhos']['value'] == Article.objects.filter(status=Article.Status.DRAFT).count()
    assert stats['Publicadas']['note'] == '1 nos últimos 30 dias'
    assert '%' not in ''.join(stat['note'] for stat in stats.values())


@pytest.mark.django_db
def test_activity_feed_uses_wagtail_audit_log(client, editor, site):
    article = _article(site, 'Auditada')
    article.save_revision(user=editor).publish(user=editor)
    client.force_login(editor)

    activity = client.get(reverse('panel:dashboard')).context['activity']

    assert any('publicou “Auditada”' in event['title'] for event in activity)


# ── Rotas preservadas ──────────────────────────────────────────────────────


def test_existing_route_names_still_resolve():
    assert reverse('panel:login') == '/entrar/'
    assert reverse('panel:logout') == '/sair/'
    assert reverse('panel:no_access') == '/sem-acesso/'
    assert reverse('panel:picker') == reverse('panel:dashboard') == '/painel/'
    assert reverse('wagtailadmin_home') == '/cms/'
    assert reverse('admin:index') == '/admin/'
    assert reverse('news_workflow_report') == '/cms/reports/noticias-em-revisao/'
    assert reverse('wagtailsnippets_news_article:add') == '/cms/snippets/news/article/add/'


def test_painel_resolves_to_dashboard_view():
    from apps.common.newsroom import views

    assert resolve('/painel/').func is views.dashboard


@pytest.mark.django_db
def test_site_fixture_is_single_site(site):
    """Sanidade: os dois portais continuam no mesmo Site (SITE_ID = 1)."""
    assert Site.objects.count() == 1


@pytest.mark.django_db
def test_admin_popup_windows_have_no_shell(client, root):
    client.force_login(root)

    content = client.get(reverse('admin:accounts_customuser_changelist'), {'_popup': '1', '_to_field': 'id'}).content.decode()

    assert 'class="nr-topbar"' not in content
    assert 'id="nr-sidebar"' not in content
