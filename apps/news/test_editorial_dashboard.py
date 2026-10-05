"""Visão geral editorial do painel unificado (/painel/): indicadores, permissões e atalhos do editor."""

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.news.models import Article
from apps.news.testing import make_article_full, make_site


def make_user(username='editor', role='news_editor', password='x', user_model=None):
    """Cria um CustomUser com o role indicado."""
    from django.contrib.auth import get_user_model
    user_model = user_model or get_user_model()
    return user_model.objects.create_user(username=username, password=password, role=role)


# ── Visão geral editorial (antigo "Painel da Redação" do /cms/) ─────────────
#
# Os painéis que viviam na página inicial do Wagtail foram absorvidos pela
# visão geral do painel unificado (/painel/). Os testes abaixo cobrem as mesmas
# garantias, agora no endereço novo; /cms/ redireciona para lá.


def _make_wagtail_editor(django_user_model, username='editor-dashboard', role='news_editor'):
    """Cria um usuário com acesso ao Wagtail admin e permissões de editor de notícias."""
    from apps.accounts.admin_roles import ensure_admin_role_groups, sync_user_role_group

    ensure_admin_role_groups()
    user = django_user_model.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password='SenhaTeste#2026',
        is_staff=True,
        role=role,
    )
    sync_user_role_group(user)
    return user


@pytest.mark.django_db
def test_wagtail_home_redirects_to_unified_overview(client, django_user_model):
    user = _make_wagtail_editor(django_user_model)
    client.force_login(user)

    response = client.get(reverse('wagtailadmin_home'))

    assert response.status_code == 302
    assert response.url == reverse('panel:dashboard')


@pytest.mark.django_db
def test_wagtail_dashboard_redacao_panels_render(client, django_user_model):
    """Editor de Notícias vê a parte editorial da visão geral."""
    site = make_site()
    user = _make_wagtail_editor(django_user_model)
    make_article_full(site, slug='dashboard-render-teste', status=Article.Status.PUBLISHED)
    client.force_login(user)

    response = client.get(reverse('panel:dashboard'))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'Visão geral' in content
    assert 'Nova notícia' in content
    assert reverse('wagtailsnippets_news_article:add') in content
    assert 'Publicadas' in content
    assert 'Rascunhos' in content
    assert 'Em revisão' in content
    assert 'Agendadas' in content
    assert 'Categorias' in content
    assert 'Tags' in content
    assert 'Home do portal' in content
    assert 'Seus conteúdos' in content
    assert 'Artigo dashboard-render-teste' in content


@pytest.mark.django_db
def test_wagtail_dashboard_panels_hidden_without_permission(client, django_user_model):
    """Usuário sem news.view_article não vê a parte editorial da visão geral."""
    from django.contrib.auth.models import Permission

    user = django_user_model.objects.create_user(
        username='no-news-perm',
        email='no-news-perm@example.com',
        password='SenhaTeste#2026',
        is_staff=True,
    )
    # Concede acesso ao Wagtail admin mas NÃO permissões de news
    access_admin_perm = Permission.objects.get(
        content_type__app_label='wagtailadmin',
        codename='access_admin',
    )
    user.user_permissions.add(access_admin_perm)
    client.force_login(user)

    response = client.get(reverse('panel:dashboard'))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'Seus conteúdos' not in content
    assert 'Nova notícia' not in content
    assert 'nr-stat__value' not in content


@pytest.mark.django_db
def test_wagtail_dashboard_status_cards_visible_for_editor(client, django_user_model):
    """Indicadores e abas de estado (publicadas/rascunhos/em revisão/agendadas)."""
    user = _make_wagtail_editor(django_user_model)
    client.force_login(user)

    response = client.get(reverse('panel:dashboard'))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'Publicadas' in content
    assert 'Rascunhos' in content
    assert 'Em revisão' in content
    assert 'Agendadas' in content


@pytest.mark.django_db
def test_wagtail_dashboard_panel_shows_article_counts(client, django_user_model):
    """Os indicadores mostram as contagens reais do banco."""
    site = make_site()
    user = _make_wagtail_editor(django_user_model)

    Article.objects.create(
        title='Publicado 1', slug='pub-1', content='.', site=site,
        status=Article.Status.PUBLISHED,
    )
    Article.objects.create(
        title='Publicado 2', slug='pub-2', content='.', site=site,
        status=Article.Status.PUBLISHED,
    )
    Article.objects.create(
        title='Rascunho 1', slug='draft-1', content='.', site=site,
        status=Article.Status.DRAFT,
    )

    client.force_login(user)
    response = client.get(reverse('panel:dashboard'))

    assert response.status_code == 200
    values = response.context['stats']
    assert [(stat['label'], stat['value']) for stat in values][:3] == [
        ('Publicadas', 2), ('Rascunhos', 1), ('Em revisão', 0),
    ]
    assert '<span class="nr-stat__value">02</span>' in response.content.decode()


@pytest.mark.django_db
def test_wagtail_dashboard_panel_recent_articles(client, django_user_model):
    """A visão geral lista as notícias com o link oficial de edição do snippet."""
    site = make_site()
    user = _make_wagtail_editor(django_user_model)

    article = Article.objects.create(
        title='Artigo Recente Teste', slug='recent-test', content='.', site=site,
        status=Article.Status.PUBLISHED,
    )

    client.force_login(user)
    response = client.get(reverse('panel:dashboard'))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'Artigo Recente Teste' in content
    edit_url = reverse('wagtailsnippets_news_article:edit', args=[article.pk])
    assert edit_url in content


@pytest.mark.django_db
def test_article_status_counts_all_categories(django_user_model):
    """_article_status_counts() conta publicadas, rascunhos, agendadas e em revisão corretamente."""
    from apps.news.wagtail_hooks import _article_status_counts

    site = make_site()
    make_article_full(site, slug='status-pub', status=Article.Status.PUBLISHED)
    make_article_full(site, slug='status-draft', status=Article.Status.DRAFT)

    # Agendar = publicar uma revisão com data futura (o Wagtail guarda a data
    # aprovada na revisão). O status só vira PUBLISHED quando ela entra no ar.
    scheduled = make_article_full(site, slug='status-scheduled', status=Article.Status.DRAFT)
    scheduled.live = False
    scheduled.go_live_at = timezone.now() + timezone.timedelta(days=1)
    scheduled.save()
    scheduled.save_revision().publish()
    # Data preenchida sem agendar: continua rascunho e não conta como agendada.
    dated = make_article_full(site, slug='status-dated', status=Article.Status.DRAFT)
    dated.live = False
    dated.go_live_at = timezone.now() + timezone.timedelta(days=1)
    dated.save()

    in_review = make_article_full(site, slug='status-review', status=Article.Status.DRAFT)
    in_review.save_revision()
    workflow = in_review.get_default_workflow()
    reviewer = make_user(username='review-author-status')
    workflow.start(in_review, reviewer)

    counts = _article_status_counts()
    assert counts['published'] == 1  # só status-pub: a agendada ainda não está no ar
    assert counts['draft'] == 3  # status-draft + status-dated + status-review (a agendada tem aba própria)
    assert counts['scheduled'] == 1
    assert counts['in_review'] == 1


@pytest.mark.django_db
def test_continue_working_panel_scoped_to_editing_user(client, django_user_model):
    """"Continuar editando seu último rascunho" só aparece para quem editou o
    próprio rascunho por último."""
    site = make_site()
    user_a = _make_wagtail_editor(django_user_model, username='editor-continue-a')
    user_b = _make_wagtail_editor(django_user_model, username='editor-continue-b')

    article = make_article_full(site, slug='continuar-teste', status=Article.Status.DRAFT)
    article.live = False
    article.save()
    article.save_revision(user=user_a)

    client.force_login(user_a)
    response = client.get(reverse('panel:dashboard'))
    assert 'Continuar editando seu último rascunho' in response.content.decode()

    client.force_login(user_b)
    response = client.get(reverse('panel:dashboard'))
    content = response.content.decode()
    assert 'Continuar editando seu último rascunho' not in content
    assert 'Continuar editando rascunhos' in content
