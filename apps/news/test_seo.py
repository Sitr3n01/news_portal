"""SEO e distribuição: sitemaps, feeds RSS, JSON-LD, Open Graph e Twitter Card."""

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.news.models import Article, Category
from apps.news.testing import make_article, make_site

# ── Fase 10: SEO coverage ──────────────────────────────────────────────────


@pytest.mark.django_db
def test_sitemap_items_and_lastmod():
    """ArticleSitemap retorna artigos publicados com lastmod em updated_at."""
    site = make_site()
    art = Article.objects.create(
        title='Artigo Sitemap', slug='sitemap-test',
        content='Conteúdo.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    from apps.news.sitemaps import ArticleSitemap

    sitemap = ArticleSitemap()
    items = sitemap.items()
    assert art in items
    assert sitemap.lastmod(art) == art.updated_at


@pytest.mark.django_db
def test_sitemap_tem_limite_por_pagina():
    """ArticleSitemap pagina em 1000.

    Sem `limit`, o default do Django e 50.000 e cada request materializava esse
    tanto de Article completo — com `content` e `body` — na RAM do worker.
    """
    from apps.news.sitemaps import ArticleSitemap

    assert ArticleSitemap.limit == 1000


@pytest.mark.django_db
def test_sitemap_latest_lastmod_nao_materializa_queryset(django_assert_num_queries):
    """get_latest_lastmod resolve por aggregate, nao iterando os items.

    A implementacao base do Django faz max([lastmod(i) for i in items()]), o que
    desfaz a protecao do `limit` justamente ao montar o indice.
    """
    site = make_site()
    art = Article.objects.create(
        title='Artigo Lastmod', slug='lastmod-test',
        content='Conteúdo.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    from apps.news.sitemaps import ArticleSitemap

    with django_assert_num_queries(1):
        assert ArticleSitemap().get_latest_lastmod() == art.updated_at


@pytest.mark.django_db
def test_sitemap_index_e_secao_respondem(client):
    """/sitemap.xml e um indice e /sitemap-news.xml traz a URL do artigo."""
    site = make_site()
    art = Article.objects.create(
        title='Artigo Index', slug='index-test',
        content='Conteúdo.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )

    index = client.get('/sitemap.xml')
    assert index.status_code == 200
    assert b'sitemap-news.xml' in index.content
    # Cache no CDN, nao no DatabaseCache — ver o comentario em config/urls.py.
    assert 'max-age=21600' in index['Cache-Control']
    assert 'public' in index['Cache-Control']

    secao = client.get('/sitemap-news.xml')
    assert secao.status_code == 200
    assert art.get_absolute_url().encode() in secao.content


@pytest.mark.django_db
def test_sitemap_nao_quebra_com_pagina_da_escola_publicada(client):
    """Regressao: PageSitemap sem location() derrubava /sitemap.xml.

    school.Page nao define get_absolute_url e o default de Sitemap.location chama
    exatamente isso, entao qualquer pagina publicada virava AttributeError -> 500.
    """
    from apps.school.models import Page

    site = make_site()
    pagina = Page.objects.create(site=site, title='Sobre', slug='sobre-sitemap', is_published=True)

    secao = client.get('/sitemap-school.xml')
    assert secao.status_code == 200
    assert f'/{pagina.slug}/'.encode() in secao.content


@pytest.mark.django_db
def test_sitemap_nao_cria_entrada_de_cache_por_query_string(client):
    """Query string arbitrária no sitemap não pode inflar o `django_cache`.

    `cache_page` chaveia por `build_absolute_uri()`, então `?x=1`, `?x=2`, ...
    criariam uma linha por variação. Ao passar de MAX_ENTRIES, o cull do Django
    apaga as chaves lexicograficamente menores — e `pwd_reset:*`, o rate limit de
    recuperação de senha, ordena abaixo de `viewed:*`. Inundar o sitemap
    despejaria um controle de segurança. Por isso o cache é só de header.
    """
    from django.core.cache import cache

    site = make_site()
    make_article(site, slug='sitemap-sem-cache')

    cache.set('pwd_reset:code:ip:sentinela', 'nao-pode-sumir', timeout=600)

    for i in range(30):
        assert client.get('/sitemap.xml', {'x': i}).status_code == 200
        assert client.get('/sitemap-news.xml', {'x': i}).status_code == 200

    assert cache.get('pwd_reset:code:ip:sentinela') == 'nao-pode-sumir'


@pytest.mark.django_db
def test_latest_articles_feed_title_and_items(client):
    """LatestArticlesFeed tem título, descrição e items publicados."""
    site = make_site(pk=1, domain='testserver')
    art = Article.objects.create(
        title='Feed Article', slug='feed-article',
        content='Feed content.', site=site,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    response = client.get(reverse('news:feed'))
    assert response.status_code == 200
    content = response.content.decode()
    assert 'Feed Article' in content
    assert art.get_absolute_url() in content


@pytest.mark.django_db
def test_category_feed_title_and_items(client):
    """CategoryFeed retorna artigos filtrados por categoria."""
    site = make_site(pk=1, domain='testserver')
    cat = Category.objects.create(name='Categoria Feed', slug='cat-feed')
    Article.objects.create(
        title='Category Feed Article', slug='cat-feed-article',
        content='Cat feed.', site=site, category=cat,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )
    response = client.get(reverse('news:category_feed', args=['cat-feed']))
    assert response.status_code == 200
    content = response.content.decode()
    assert 'Category Feed Article' in content


@pytest.mark.django_db
def test_article_detail_json_ld_publisher_has_logo(client, settings, tmp_path):
    """JSON-LD inclui publisher.logo quando site_settings.logo está definido."""
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site(pk=settings.SITE_ID, domain='testserver')
    from io import BytesIO

    from django.core.files.base import ContentFile
    from PIL import Image as PILImage

    from apps.common.models import SiteExtension

    buf = BytesIO()
    PILImage.new('RGB', (100, 100), (30, 90, 180)).save(buf, format='PNG')
    buf.seek(0)

    ext, _ = SiteExtension.objects.get_or_create(site=site)
    ext.logo.save('logo.png', ContentFile(buf.read()))
    ext.save()

    art = make_article(site, slug='jsonld-logo', status=Article.Status.PUBLISHED)
    art.published_at = __import__('django').utils.timezone.now()
    art.save()

    response = client.get(reverse('news:article_detail', args=['jsonld-logo']))
    html = response.content.decode()

    assert response.status_code == 200
    assert '"logo"' in html
    assert 'logo.png' in html


@pytest.mark.django_db
def test_article_detail_json_ld_no_logo_when_not_set(client):
    """JSON-LD NÃO inclui logo quando site_settings não tem logo."""
    site = make_site(pk=1, domain='testserver')
    from apps.common.models import SiteExtension
    SiteExtension.objects.filter(site=site).delete()

    art = make_article(site, slug='jsonld-no-logo', status=Article.Status.PUBLISHED)
    art.published_at = __import__('django').utils.timezone.now()
    art.save()

    response = client.get(reverse('news:article_detail', args=['jsonld-no-logo']))
    html = response.content.decode()

    assert response.status_code == 200
    assert '"logo"' not in html


@pytest.mark.django_db
def test_article_detail_og_tags(client):
    """Página de artigo tem meta tags Open Graph."""
    site = make_site(pk=1, domain='testserver')
    art = make_article(site, slug='og-test', status=Article.Status.PUBLISHED)
    art.published_at = __import__('django').utils.timezone.now()
    art.meta_title = 'OG Title'
    art.meta_description = 'OG Desc'
    art.save()

    response = client.get(reverse('news:article_detail', args=['og-test']))
    html = response.content.decode()

    assert response.status_code == 200
    assert '<meta property="og:title" ' in html
    assert '<meta property="og:description" ' in html
    assert '<meta property="og:type" content="article"' in html
    assert '<meta property="og:url" ' in html
    assert 'OG Title' in html


@pytest.mark.django_db
def test_article_detail_twitter_card(client):
    """Página de artigo tem Twitter Card meta tags."""
    site = make_site(pk=1, domain='testserver')
    art = make_article(site, slug='tw-test', status=Article.Status.PUBLISHED)
    art.published_at = __import__('django').utils.timezone.now()
    art.save()

    response = client.get(reverse('news:article_detail', args=['tw-test']))
    html = response.content.decode()

    assert response.status_code == 200
    assert '<meta name="twitter:card"' in html
    assert '<meta name="twitter:title"' in html
    assert '<meta name="twitter:description"' in html


@pytest.mark.django_db
def test_article_detail_article_section_in_og(client):
    """Meta tag article:section aparece para artigo com categoria."""
    site = make_site(pk=1, domain='testserver')
    cat = Category.objects.create(name='Test Cat OG', slug='test-cat-og')
    Article.objects.create(
        title='Artigo section meta', slug='art-section-meta',
        content='Conteúdo.', site=site, category=cat,
        status=Article.Status.PUBLISHED, published_at=timezone.now(),
    )

    response = client.get(reverse('news:article_detail', args=['art-section-meta']))
    html = response.content.decode()

    assert response.status_code == 200
    assert 'article:section' in html
    assert 'Test Cat OG' in html
