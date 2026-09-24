"""Listagem de notícias no Wagtail (ArticleIndexView e news/wagtail/*.html).

Cobrem: o cabeçalho do painel no lugar do slim_header (título, contagem,
"Nova notícia"), as abas por estado editorial com contagem e filtro, a aba
mantida na busca ao vivo, o selo de estado de cada linha, as mensagens de
lista vazia e as mensagens de sucesso no feminino. O desenho (cartão, botão
"Filtros", barra de seleção encaixada na faixa da busca) foi validado no
navegador.
"""

import re

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.news.models import Article, Category
from apps.news.test_governance import _form_data

LIST_URL = 'wagtailsnippets_news_article:list'
RESULTS_URL = 'wagtailsnippets_news_article:list_results'


@pytest.fixture
def category(db):
    return Category.objects.create(name='Geral', slug='geral')


@pytest.fixture
def editor(make_panel_user):
    return make_panel_user('wl_editor', role=CustomUser.Role.NEWS_EDITOR)


def _article(site, category, author, slug, **extra):
    return Article.objects.create(
        title=f'Notícia {slug}', slug=slug, content='<p>.</p>', site=site,
        category=category, author=author, **extra,
    )


@pytest.fixture
def newsroom(current_site, category, editor):
    """Uma notícia em cada estado que a listagem distingue."""
    published = _article(current_site, category, editor, 'no-ar')
    published.save_revision(user=editor).publish(user=editor)
    _article(current_site, category, editor, 'rascunho', live=False).save_revision(user=editor)
    scheduled = _article(current_site, category, editor, 'agendada', live=False,
                         go_live_at=timezone.now() + timezone.timedelta(days=2))
    scheduled.save_revision(user=editor).publish(user=editor)
    _article(current_site, category, editor, 'arquivada', live=False, status=Article.Status.ARCHIVED)
    return {'published': published, 'scheduled': scheduled}


def _tabs(html):
    return re.findall(r'class="nr-tab( is-active)?" href="([^"]+)"[^>]*>\s*([^<]+?)<span class="nr-tab__count">(\d+)</span>', html)


@pytest.mark.django_db
def test_model_is_called_noticia():
    assert Article._meta.verbose_name == 'Notícia'
    assert Article._meta.verbose_name_plural == 'Notícias'
    assert Article.Status.PUBLISHED.label == 'Publicada'


@pytest.mark.django_db
def test_listing_uses_the_panel_header(client, editor, newsroom):
    client.force_login(editor)

    html = client.get(reverse(LIST_URL)).content.decode()

    assert '<header class="w-slim-header' not in html
    assert re.search(r'<h1 class="nr-listhead__title">\s*Notícias\s*<span class="nr-listhead__count">4</span>', html)
    assert '<span>Nova notícia</span>' in html
    assert 'data-nr-selection-dock' in html
    tabs = [(bool(active), label.strip(), int(count)) for active, _url, label, count in _tabs(html)]
    assert tabs == [
        (True, 'Todas', 4), (False, 'Publicadas', 1), (False, 'Rascunhos', 1),
        (False, 'Em revisão', 0), (False, 'Agendadas', 1), (False, 'Arquivadas', 1),
    ]


@pytest.mark.django_db
def test_tab_filters_the_rows_and_travels_with_the_search(client, editor, newsroom):
    client.force_login(editor)

    html = client.get(reverse(LIST_URL), {'estado': 'scheduled'}).content.decode()

    assert 'Notícia agendada' in html
    assert 'Notícia no-ar' not in html
    assert '<input type="hidden" name="estado" value="scheduled">' in html
    # A busca ao vivo (resultados) também respeita a aba.
    results = client.get(reverse(RESULTS_URL), {'estado': 'published', 'q': 'Notícia'}).content.decode()
    assert 'Notícia no-ar' in results
    assert 'Notícia rascunho' not in results


@pytest.mark.django_db
def test_rows_show_the_editorial_badge(client, editor, newsroom):
    client.force_login(editor)

    html = client.get(reverse(LIST_URL)).content.decode()

    assert '<span class="nr-status nr-status--published">Publicada</span>' in html
    assert '<span class="nr-status nr-status--scheduled">Agendada</span>' in html
    assert '<span class="nr-status nr-status--archived">Arquivada</span>' in html


@pytest.mark.django_db
def test_empty_messages_agree_with_noticia(client, editor, newsroom):
    client.force_login(editor)

    review = client.get(reverse(LIST_URL), {'estado': 'review'}).content.decode()
    search = client.get(reverse(RESULTS_URL), {'q': 'nada-com-isso'}).content.decode()

    assert 'Nenhuma notícia em revisão no momento.' in review
    assert 'Por que não adicionar um' not in review
    assert 'Nenhuma notícia encontrada com essa busca ou esses filtros.' in search


@pytest.mark.django_db
def test_scheduling_does_not_publish_before_the_time(client, editor, current_site, category):
    """O Wagtail manda o sinal `published` também ao agendar. O site público só
    olha `status`: se o sinal o marcasse, a notícia agendada iria ao ar na hora
    (e para a fila da newsletter). Ela só vira publicada quando o
    `publish_scheduled` a publica, na data marcada."""
    go_live = timezone.now() + timezone.timedelta(days=2)
    article = _article(current_site, category, editor, 'so-na-hora', live=False, go_live_at=go_live)
    revision = article.save_revision(user=editor)
    revision.publish(user=editor)
    article.refresh_from_db()

    assert article.live is False
    assert article.status == Article.Status.DRAFT
    assert client.get(reverse('news:article_detail', args=[article.slug])).status_code == 404

    # Chegou a hora (a data, na revisão e na aprovação, passa a ser o passado)
    # e o cron roda o publish_scheduled.
    past = timezone.now() - timezone.timedelta(minutes=1)
    revision.refresh_from_db()
    revision.content['go_live_at'] = past.isoformat()
    revision.approved_go_live_at = past
    revision.save(update_fields=['content', 'approved_go_live_at'])
    call_command('publish_scheduled')
    article.refresh_from_db()

    assert article.live is True
    assert article.status == Article.Status.PUBLISHED


@pytest.mark.django_db
def test_success_message_agrees_with_noticia(client, editor, current_site, category):
    article = _article(current_site, category, editor, 'mensagem', live=False)
    article.save_revision(user=editor)
    client.force_login(editor)
    url = reverse('wagtailsnippets_news_article:edit', args=[article.pk])

    response = client.post(url, _form_data(client.get(url), title='Título salvo'), follow=True)

    messages = [str(message) for message in response.context['messages']]
    # O Wagtail escapa o texto e acrescenta o botão "Editar" à mensagem.
    assert len(messages) == 1
    assert messages[0].startswith('Notícia &#x27;Título salvo&#x27; atualizada.')
