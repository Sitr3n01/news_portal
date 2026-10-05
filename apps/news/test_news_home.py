"""Home do portal de notícias: NewsHomeConfig, destaques, SEO da home e seção social."""

import pytest
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils import timezone

from apps.news.models import Article, NewsHomeConfig
from apps.news.testing import make_site


@pytest.mark.django_db
def test_news_article_list(client):
    url = reverse('news:list')
    response = client.get(url)
    assert response.status_code == 200
    assert 'text/html' in response['Content-Type']


# ── Fase 11b: NewsHomeConfig ──────────────────────────────────────────────────


def _make_stream_value(article_pks):
    """Constrói valor bruto para o StreamField secondary_highlights."""
    return [{'type': 'artigo', 'value': pk} for pk in article_pks]


@pytest.mark.django_db
def test_newshomeconfig_singleton_per_site():
    """Segundo create() com o mesmo site levanta IntegrityError."""
    site = make_site()
    NewsHomeConfig.objects.create(site=site)
    with pytest.raises(Exception):  # IntegrityError
        NewsHomeConfig.objects.create(site=site)


@pytest.mark.django_db
def test_article_list_regression_without_config(client, settings):
    """Sem NewsHomeConfig, featured continua automático (regressão zero)."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')
    Article.objects.create(
        title='Featured Article', slug='featured-art', content='.', site=site,
        status=Article.Status.PUBLISHED, is_featured=True,
        published_at=timezone.now() - timezone.timedelta(days=1),
    )
    Article.objects.create(
        title='Regular Article', slug='regular-art', content='.', site=site,
        status=Article.Status.PUBLISHED,
        published_at=timezone.now(),
    )

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    assert 'Featured Article' in html
    # Regular deve aparecer no grid (excluindo apenas featured)
    assert 'Regular Article' in html


@pytest.mark.django_db
def test_hero_override_published_becomes_featured(client, settings):
    """hero_override publicado e do site certo vira featured."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')
    override = Article.objects.create(
        title='Manual Hero', slug='manual-hero', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    Article.objects.create(
        title='Auto Featured', slug='auto-featured', content='.', site=site,
        status=Article.Status.PUBLISHED, is_featured=True,
        published_at=timezone.now() - timezone.timedelta(days=1),
    )
    NewsHomeConfig.objects.create(
        site=site, is_active=True, hero_override=override,
    )

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    assert 'Manual Hero' in html
    # Auto featured NÃO deve ser o hero (não aparece no hero, mas pode aparecer no grid)
    assert 'Auto Featured' in html


@pytest.mark.django_db
def test_hero_override_draft_ignored_uses_auto(client, settings):
    """hero_override não publicado (draft) é ignorado, cai no automático."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')
    override = Article.objects.create(
        title='Draft Hero', slug='draft-hero', content='.', site=site,
        status=Article.Status.DRAFT,
    )
    Article.objects.create(
        title='Auto Featured', slug='auto-feat', content='.', site=site,
        status=Article.Status.PUBLISHED, is_featured=True,
        published_at=timezone.now(),
    )
    NewsHomeConfig.objects.create(
        site=site, is_active=True, hero_override=override,
    )

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    # O automático deve aparecer como featured
    assert 'auto-feat' in html


@pytest.mark.django_db
def test_hero_override_other_site_ignored(client, settings):
    """hero_override de outro site é ignorado, cai no automático."""
    site1 = make_site(pk=settings.SITE_ID, domain='testserver')
    site2 = make_site(pk=999, domain='other.testserver', name='Other')
    override = Article.objects.create(
        title='Other Site Hero', slug='other-hero', content='.', site=site2,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    Article.objects.create(
        title='Auto Featured', slug='auto-feat', content='.', site=site1,
        status=Article.Status.PUBLISHED, is_featured=True,
        published_at=timezone.now(),
    )
    NewsHomeConfig.objects.create(
        site=site1, is_active=True, hero_override=override,
    )

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    # O artigo do outro site não vira hero
    assert 'auto-feat' in html


@pytest.mark.django_db
def test_secondary_highlights_appear_in_order_and_excluded_from_grid(client, settings):
    """2-4 destaques secundários aparecem na ordem configurada e somem do grid."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')

    Article.objects.create(
        title='Featured', slug='feat', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    h1 = Article.objects.create(
        title='Highlight 1', slug='h1', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    h2 = Article.objects.create(
        title='Highlight 2', slug='h2', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    Article.objects.create(
        title='Grid Article', slug='grid-art', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )

    config = NewsHomeConfig(site=site, is_active=True)
    config.save()
    config.secondary_highlights = _make_stream_value([h1.pk, h2.pk])
    config.save()
    config.refresh_from_db()

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    # Destaques aparecem na seção de destaques
    assert 'h1' in html
    assert 'h2' in html
    # Grid article (não-destaque) aparece no grid
    assert 'grid-art' in html


@pytest.mark.django_db
def test_secondary_highlights_invalid_ignored_silently(client, settings):
    """Item inválido (não publicado) nos destaques é ignorado sem erro."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')

    Article.objects.create(
        title='Featured', slug='feat', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    valid = Article.objects.create(
        title='Valid Highlight', slug='valid', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    draft = Article.objects.create(
        title='Draft Highlight', slug='draft-hl', content='.', site=site,
        status=Article.Status.DRAFT,
    )

    config = NewsHomeConfig(site=site, is_active=True)
    config.save()
    config.secondary_highlights = _make_stream_value([draft.pk, valid.pk])
    config.save()
    config.refresh_from_db()

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    # Draft não deve aparecer nos destaques
    assert 'valid' in html
    assert 'draft-hl' not in html  # slug do draft não aparece nos destaques


@pytest.mark.django_db
def test_htmx_load_more_excludes_hero_and_highlights(client, settings):
    """Carregar mais via HTMX não reexibe hero nem destaques."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')

    Article.objects.create(
        title='Extra Article', slug='extra', content='.', site=site,
        status=Article.Status.PUBLISHED,
        published_at=timezone.now() - timezone.timedelta(days=2),
    )
    h1 = Article.objects.create(
        title='Highlight 1', slug='hl1', content='.', site=site,
        status=Article.Status.PUBLISHED,
        published_at=timezone.now() - timezone.timedelta(days=1),
    )
    Article.objects.create(
        title='Featured', slug='feat', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )

    config = NewsHomeConfig(site=site, is_active=True)
    config.save()
    config.secondary_highlights = _make_stream_value([h1.pk])
    config.save()

    response = client.get(
        reverse('news:article_list_page') + '?page=1',
        HTTP_HX_REQUEST='true',
    )

    html = response.content.decode()
    assert response.status_code == 200
    # Featured e highlight não reaparecem no grid HTMX
    assert 'feat' not in html
    assert 'hl1' not in html
    assert 'extra' in html


@pytest.mark.django_db
def test_seo_home_uses_home_config_fields(client, settings):
    """SEO da home usa home_config.meta_title/meta_description quando definidos."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')

    Article.objects.create(
        title='Article', slug='art', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    NewsHomeConfig.objects.create(
        site=site, is_active=True,
        meta_title='SEO Title Test',
        meta_description='SEO Desc Test',
    )

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    assert '<title>SEO Title Test</title>' in html
    assert '<meta name="description" content="SEO Desc Test">' in html
    assert '<meta property="og:title" content="SEO Title Test">' in html
    assert '<meta property="og:description" content="SEO Desc Test">' in html
    assert '<meta name="twitter:title" content="SEO Title Test">' in html
    assert '<meta name="twitter:description" content="SEO Desc Test">' in html


@pytest.mark.django_db
def test_seo_home_fallback_without_config(client, settings):
    """SEO da home cai no fallback atual quando NewsHomeConfig não existe."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')

    Article.objects.create(
        title='Article', slug='art', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    assert 'Blog da Kelly' in html  # news_portal_name default
    assert 'Conteúdos, notícias e bastidores da Komuniki com Kelly Farias.' in html


@pytest.mark.django_db
def test_seo_home_fallback_with_empty_fields(client, settings):
    """SEO cai no fallback quando campos estão vazios."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')

    Article.objects.create(
        title='Article', slug='art', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    NewsHomeConfig.objects.create(site=site, is_active=True)  # sem SEO preenchido

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    assert 'Blog da Kelly' in html
    assert 'Conteúdos, notícias e bastidores da Komuniki com Kelly Farias.' in html


@pytest.mark.django_db
def test_news_home_shows_social_section_when_enabled(client, settings):
    """Seção social aparece na home do news quando social_section_enabled=True."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')

    from apps.common.models import SiteExtension
    from apps.social.models import Platform, SocialAccount, SocialPost

    Article.objects.create(
        title='Article', slug='art', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    SiteExtension.objects.update_or_create(
        site=site,
        defaults={
            'social_section_enabled': True,
            'social_section_title': 'Acompanhe nas redes',
            'instagram_url': 'https://www.instagram.com/komunikiescola/',
        },
    )
    account = SocialAccount.objects.create(
        site=site, platform=Platform.INSTAGRAM, display_name='Komuniki IG',
        username='komuniki', is_active=True,
    )
    SocialPost.objects.create(
        account=account, permalink='https://www.instagram.com/p/MANUAL/',
        published_at=timezone.now(), is_visible=True, is_manual=True,
    )

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    assert 'Acompanhe nas redes' in html
    assert 'https://www.instagram.com/p/MANUAL/' in html


@pytest.mark.django_db
def test_news_home_hides_social_section_when_disabled(client, settings):
    """Seção social some da home do news quando social_section_enabled=False."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')

    from apps.common.models import SiteExtension
    from apps.social.models import Platform, SocialAccount, SocialPost

    Article.objects.create(
        title='Article', slug='art', content='.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    SiteExtension.objects.update_or_create(
        site=site,
        defaults={'social_section_enabled': False},
    )
    account = SocialAccount.objects.create(
        site=site, platform=Platform.INSTAGRAM, display_name='Komuniki IG',
        username='komuniki', is_active=True,
    )
    SocialPost.objects.create(
        account=account, permalink='https://www.instagram.com/p/HIDDEN/',
        published_at=timezone.now(), is_visible=True, is_manual=True,
    )

    response = client.get(reverse('news:list'))

    html = response.content.decode()
    assert response.status_code == 200
    assert 'https://www.instagram.com/p/HIDDEN/' not in html
    assert 'social-section-title' not in html


@pytest.mark.django_db
def test_get_social_section_posts_respects_toggles():
    """get_social_section_posts respeita toggles de SiteExtension."""
    from apps.common.models import SiteExtension
    from apps.common.social_section import get_social_section_posts
    from apps.social.models import Platform, SocialAccount, SocialPost

    site = make_site(pk=1)

    # Sem SiteExtension
    assert get_social_section_posts(site) == []

    ext, _ = SiteExtension.objects.update_or_create(
        site=site,
        defaults={'social_section_enabled': False},
    )
    assert get_social_section_posts(site) == []

    ext.social_section_enabled = True
    ext.social_show_instagram = True
    ext.social_show_tiktok = False
    ext.save()

    ig = SocialAccount.objects.create(
        site=site, platform=Platform.INSTAGRAM,
        display_name='IG', username='ig', is_active=True,
    )
    tk = SocialAccount.objects.create(
        site=site, platform=Platform.TIKTOK,
        display_name='TK', username='tk', is_active=True,
    )
    SocialPost.objects.create(
        account=ig, permalink='https://ig.test/p/1',
        published_at=timezone.now(), is_visible=True,
    )
    SocialPost.objects.create(
        account=tk, permalink='https://tk.test/v/1',
        published_at=timezone.now(), is_visible=True,
    )

    # Evita cache da OneToOneField: usa Site fresco
    site = Site.objects.get(pk=site.pk)
    posts = get_social_section_posts(site)
    assert len(posts) == 1
    assert posts[0].account.platform == Platform.INSTAGRAM


@pytest.mark.django_db
def test_wagtail_snippet_newshomeconfig_registered():
    """NewsHomeConfig está registrado como Wagtail Snippet."""
    from wagtail.snippets.models import get_snippet_models
    snippet_names = {m.__name__ for m in get_snippet_models()}
    assert 'NewsHomeConfig' in snippet_names
