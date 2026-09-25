"""Ações do leitor só alcançam notícia publicada do Site atual (IDOR-01, ISO-01).

Favoritar, curtir e comentar recebem só o ID da notícia. Antes, um leitor com
cadastro público favoritava rascunhos por ID e lia título e texto no painel.
"""

import pytest
from django.contrib.sites.models import Site
from django.urls import reverse

from apps.news.models import Article, ArticleBookmark, ArticleLike, Comment

SEGREDO = 'Conteúdo sob embargo que ainda não foi publicado'


@pytest.fixture
def reader(django_user_model):
    return django_user_model.objects.create_user(
        username='leitora', email='leitora@example.com', password='x', email_verified=True,
    )


@pytest.fixture
def other_site(db):
    return Site.objects.create(domain='outro.example', name='Outro portal')


def _article(site, slug, status=Article.Status.PUBLISHED):
    return Article.objects.create(
        title=f'Notícia {slug}', slug=slug, excerpt='', content=f'<p>{SEGREDO}</p>', site=site, status=status,
    )


@pytest.mark.django_db
@pytest.mark.parametrize('status', [Article.Status.DRAFT, Article.Status.ARCHIVED])
@pytest.mark.parametrize('route', ['news:toggle_bookmark', 'news:toggle_like', 'news:add_comment'])
def test_reader_actions_refuse_unpublished_articles(client, reader, current_site, route, status):
    article = _article(current_site, 'fora-do-ar', status=status)
    client.force_login(reader)

    response = client.post(reverse(route, args=[article.pk]), {'content': 'oi'}, HTTP_HX_REQUEST='true')

    assert response.status_code == 404
    assert not ArticleBookmark.objects.exists()
    assert not ArticleLike.objects.exists()
    assert not Comment.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize('route', ['news:toggle_bookmark', 'news:toggle_like', 'news:add_comment'])
def test_reader_actions_refuse_other_site_articles(client, reader, current_site, other_site, route):
    article = _article(other_site, 'de-outro-portal')
    client.force_login(reader)

    response = client.post(reverse(route, args=[article.pk]), {'content': 'oi'}, HTTP_HX_REQUEST='true')

    assert response.status_code == 404


@pytest.mark.django_db
def test_reader_actions_still_work_on_published_articles(client, reader, current_site):
    article = _article(current_site, 'no-ar')
    client.force_login(reader)

    assert client.post(reverse('news:toggle_bookmark', args=[article.pk]), HTTP_HX_REQUEST='true').status_code == 200
    assert client.post(reverse('news:toggle_like', args=[article.pk]), HTTP_HX_REQUEST='true').status_code == 200
    assert ArticleBookmark.objects.filter(user=reader, article=article).exists()
    assert ArticleLike.objects.filter(user=reader, article=article).exists()


@pytest.mark.django_db
def test_dashboard_hides_articles_that_are_not_public_here(client, reader, current_site, other_site):
    published = _article(current_site, 'publicada')
    draft = _article(current_site, 'rascunho', status=Article.Status.DRAFT)
    foreign = _article(other_site, 'estrangeira')
    for article in (published, draft, foreign):
        ArticleBookmark.objects.create(user=reader, article=article)
        ArticleLike.objects.create(user=reader, article=article)
    client.force_login(reader)

    html = client.get(reverse('news:user_dashboard')).content.decode()

    assert 'Notícia publicada' in html
    assert 'Notícia rascunho' not in html
    assert 'Notícia estrangeira' not in html
