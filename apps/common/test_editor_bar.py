"""Barra única do editor do Wagtail (apps/common/newsroom/editor.py e
templates/newsroom/editor/).

Cobrem: a barra no lugar do cabeçalho nativo, o que ela mostra (voltar,
título, status, ferramentas, menu "Mais opções"), os botões de publicação que
continuam dentro do formulário, o status lido do banco (e não da revisão), a
tela de criação, um cadastro sem rascunho e a barra reenviada pelo
salvamento automático. Os botões que clicam nos nativos são montados em
JavaScript (static/newsroom/js/newsroom-editor.js) e foram validados no
navegador.
"""

import re
from types import SimpleNamespace

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.common.newsroom.editor import editor_bar
from apps.news.models import Article, Category
from apps.news.test_governance import _form_data


@pytest.fixture
def site(current_site):
    return current_site


@pytest.fixture
def category(db):
    return Category.objects.create(name='Geral', slug='geral')


@pytest.fixture
def editor(make_panel_user):
    return make_panel_user('eb_editor', role=CustomUser.Role.NEWS_EDITOR)


@pytest.fixture
def root(make_panel_user):
    return make_panel_user('eb_root', role=CustomUser.Role.SUPER_ADMIN, is_staff=True, is_superuser=True)


def _article(site, category, author, slug, **extra):
    return Article.objects.create(
        title=f'Notícia {slug}', slug=slug, content='<p>.</p>', site=site,
        category=category, author=author, **extra,
    )


def _edit_url(article):
    return reverse('wagtailsnippets_news_article:edit', args=[article.pk])


def _status(article):
    """Status da barra para um artigo, como a view de edição o entregaria."""
    view = SimpleNamespace(view_name='edit', header_more_buttons=[])
    return editor_bar({'model': Article, 'object': article, 'view': view})['status']


def _form(html):
    return re.search(r'<form\s+id="w-editor-form".*?</form>', html, re.S).group(0)


def _bar(html):
    return re.search(r'<header class="nr-editorbar".*?</header>', html, re.S).group(0)


# ── A barra no lugar do cabeçalho ──────────────────────────────────────────


@pytest.mark.django_db
def test_article_editor_has_a_single_bar(client, editor, site, category):
    article = _article(site, category, editor, 'barra')
    client.force_login(editor)

    html = client.get(_edit_url(article)).content.decode()
    bar = _bar(html)

    # O cabeçalho nativo do Wagtail sai; o formulário continua o nativo.
    assert 'w-slim-header w-bg-surface-header' not in html
    assert '>Notícias</a>' in bar
    assert '<h1 class="nr-editorbar__title" id="nr-editorbar-title">Notícia barra</h1>' in bar
    # Controle "Publicação" no lugar do selo; o botão nativo do painel "Status"
    # continua na barra (oculto), acionado por "Ver todos os detalhes".
    assert 'class="nr-pub__button nr-pub--draft"' in bar
    assert 'nr-editorbar__status' not in bar
    assert bar.count('data-side-panel-toggle="status"') == 2
    assert 'data-nr-proxy-click=\'[data-nr-editorbar] [data-side-panel-toggle="status"]\'' in bar
    assert 'data-side-panel-toggle="preview"' in bar
    assert 'data-side-panel-toggle="checks"' in bar
    assert 'aria-label="Histórico"' in bar
    # "Estrutura" abre o minimapa do Wagtail; nasce oculta até o React montá-lo.
    assert re.search(r'class="w-side-panel-toggle nr-editorbar__outline"[^>]*data-nr-proxy-click="#w-minimap-toggle"[^>]*hidden>', bar, re.S)
    assert 'data-minimap-container' in html
    assert 'newsroom/js/newsroom-editor.js' in html


@pytest.mark.django_db
def test_secondary_actions_are_tool_icons_and_a_remove_button(client, editor, site, category):
    article = _article(site, category, editor, 'menu')
    client.force_login(editor)

    bar = _bar(client.get(_edit_url(article)).content.decode())
    tools = bar[bar.index('class="nr-editorbar__tools"'):bar.index('id="nr-editorbar-danger"')]
    icons = re.findall(r'href="([^"]+)"\s+class="w-side-panel-toggle[^"]*"\s+aria-label="([^"]+)"', tools)

    # Copiar e inspecionar: ícones nas ferramentas, depois do histórico.
    assert [label for _, label in icons] == ['Histórico', 'Copiar', 'Inspecionar']
    assert icons[1][0] == f'/cms/snippets/news/article/copy/{article.pk}/'
    assert icons[2][0] == f'/cms/snippets/news/article/inspect/{article.pk}/'
    # Remover: botão próprio, antes das ações de publicação.
    assert re.search(r'class="nr-btn nr-btn--secondary nr-editorbar__remove" href="/cms/snippets/news/article/delete/', bar)
    assert bar.index('nr-editorbar__remove') < bar.index('data-nr-editor-actions')
    # Nada sobrou para o menu "Mais opções".
    assert 'nr-editorbar__more' not in bar[bar.index('id="nr-editorbar-more"'):]


@pytest.mark.django_db
def test_publishing_buttons_stay_inside_the_form(client, editor, site, category):
    """A proteção de edição simultânea do Wagtail só vigia botões do formulário:
    a barra clica neles, não os tira de lá."""
    article = _article(site, category, editor, 'form')
    client.force_login(editor)

    html = client.get(_edit_url(article)).content.decode()
    form = _form(html)

    assert 'name="action-publish"' in form
    assert 'name="action-submit"' in form
    assert 'data-w-kbd-key-value="mod+s"' in form
    assert 'name="action-publish"' not in _bar(html)
    assert 'data-nr-editor-actions' in _bar(html)


# ── Status: sempre o do banco ──────────────────────────────────────────────


@pytest.mark.django_db
def test_status_of_a_draft(editor, site, category):
    article = _article(site, category, editor, 'rascunho')

    assert _status(article) == {'key': 'draft', 'label': 'Rascunho', 'note': ''}


@pytest.mark.django_db
def test_status_of_a_published_article_with_pending_edits(editor, site, category):
    article = _article(site, category, editor, 'publicada')
    article.save_revision(user=editor).publish(user=editor)
    article.refresh_from_db()
    article.title = 'Título novo ainda não publicado'
    article.save_revision(user=editor)

    status = _status(article)

    assert status['key'] == 'published'
    assert status['label'] == 'Publicada'
    assert status['note'] == 'Alterações não publicadas'


def _when(value):
    return timezone.localtime(value).strftime('%d/%m às %H:%M')


@pytest.mark.django_db
def test_status_of_a_scheduled_article(editor, site, category):
    """Agendar = "Agendar publicação": publicar uma revisão com data futura."""
    go_live = timezone.now() + timezone.timedelta(days=2)
    article = _article(site, category, editor, 'agendada', live=False, go_live_at=go_live)
    article.save_revision(user=editor).publish(user=editor)
    article.refresh_from_db()

    status = _status(article)

    assert article.live is False
    assert status['key'] == 'scheduled'
    assert status['note'] == f'Publica em {_when(go_live)}'


@pytest.mark.django_db
def test_date_without_scheduling_is_still_a_draft(editor, site, category):
    """Preencher a data e salvar o rascunho não agenda: o Wagtail não vai publicar."""
    go_live = timezone.now() + timezone.timedelta(days=2)
    article = _article(site, category, editor, 'so-data', live=False, go_live_at=go_live)
    article.save_revision(user=editor)

    status = _status(article)

    assert status['key'] == 'draft'
    assert status['label'] == 'Rascunho'
    assert status['note'] == f'Data marcada para {_when(go_live)}, ainda não agendada'


@pytest.mark.django_db
def test_live_article_with_a_scheduled_new_version(editor, site, category):
    article = _article(site, category, editor, 'no-ar-com-agenda')
    article.save_revision(user=editor).publish(user=editor)
    article.refresh_from_db()
    go_live = timezone.now() + timezone.timedelta(days=5)
    article.title = 'Versão nova agendada'
    article.go_live_at = go_live
    article.save_revision(user=editor).publish(user=editor)
    article.refresh_from_db()

    status = _status(article)

    assert article.live is True
    assert status['key'] == 'published'
    assert status['note'] == f'Nova versão agendada para {_when(go_live)}'


# ── Controle "Publicação" ─────────────────────────────────────────────────


def _publication(client, article):
    bar = _bar(client.get(_edit_url(article)).content.decode())
    return re.search(r'<details class="nr-pub".*?</details>', bar, re.S).group(0)


@pytest.mark.django_db
def test_publication_control_without_schedule(client, editor, site, category):
    article = _article(site, category, editor, 'pub-livre', live=False)
    article.save_revision(user=editor)
    client.force_login(editor)

    pub = _publication(client, article)

    assert 'nr-pub__flag' not in pub
    assert 'Assim que publicar' in pub
    assert 'Não sai' in pub
    assert 'nr-pub__alert' not in pub
    assert re.search(r'Última edição agora por \S', pub)
    # Os botões clicam nos controles nativos do painel "Status".
    assert '[data-a11y-dialog-show="schedule-publishing-dialog"]' in pub
    assert 'Edição livre' in pub
    assert '>Travar</button>' in pub
    assert f'href="/cms/snippets/news/article/history/{article.pk}/"' in pub


@pytest.mark.django_db
def test_publication_control_warns_about_a_date_not_yet_scheduled(client, editor, site, category):
    go_live = timezone.now() + timezone.timedelta(days=2)
    article = _article(site, category, editor, 'pub-so-data', live=False, go_live_at=go_live)
    article.save_revision(user=editor)
    client.force_login(editor)

    pub = _publication(client, article)

    assert 'datas ainda não agendadas' in pub  # rótulo acessível do botão
    assert 'nr-pub__flag nr-pub__flag--warning' in pub
    assert f'{_when(go_live)}' in pub
    assert 'Não agendada' in pub
    assert 'só valem depois de "Agendar publicação"' in pub


@pytest.mark.django_db
def test_publication_control_shows_an_active_schedule(client, editor, site, category):
    go_live = timezone.now() + timezone.timedelta(days=2)
    article = _article(site, category, editor, 'pub-agendada', live=False, go_live_at=go_live)
    article.save_revision(user=editor).publish(user=editor)
    client.force_login(editor)

    pub = _publication(client, article)

    assert 'class="nr-pub__button nr-pub--scheduled"' in pub
    assert ', com agendamento' in pub
    assert 'nr-pub__flag--warning' not in pub
    assert 'Não agendada' not in pub
    assert _when(go_live) in pub


@pytest.mark.django_db
def test_reporter_sees_the_dates_but_cannot_set_them(client, make_panel_user, site, category):
    """A governança tira as datas do formulário de quem não publica
    (RestrictedPublishingPanel): o controle mostra, mas não oferece "Definir"."""
    reporter = make_panel_user('eb_reporter', role=CustomUser.Role.REPORTER)
    article = _article(site, category, reporter, 'pub-reporter', live=False)
    article.save_revision(user=reporter)
    client.force_login(reporter)

    pub = _publication(client, article)

    assert 'Agendamento' in pub
    assert 'Definir datas' not in pub


@pytest.mark.django_db
def test_publication_control_shows_the_lock(client, editor, site, category):
    article = _article(site, category, editor, 'pub-travada', locked=True, locked_by=editor, locked_at=timezone.now())
    article.save_revision(user=editor)
    client.force_login(editor)

    pub = _publication(client, article)

    assert ', travada' in pub
    assert '>Destravar</button>' in pub


@pytest.mark.django_db
def test_schedule_button_is_in_portuguese(client, editor, site, category):
    """O catálogo pt-BR do Wagtail 7.4.2 não traduz "Schedule to publish"."""
    go_live = timezone.now() + timezone.timedelta(days=2)
    article = _article(site, category, editor, 'botao-agendar', live=False, go_live_at=go_live)
    article.save_revision(user=editor)
    client.force_login(editor)

    form = _form(client.get(_edit_url(article)).content.decode())

    assert 'Agendar publicação' in form
    assert 'data-w-progress-active-value="Agendando…"' in form
    assert 'Schedule to publish' not in form


@pytest.mark.django_db
def test_status_of_an_article_in_review_names_the_step(editor, site, category):
    article = _article(site, category, editor, 'revisao')
    article.save_revision(user=editor)
    article.get_default_workflow().start(article, editor)

    status = _status(article)

    assert status['key'] == 'review'
    assert status['note'] == 'Etapa: Aprovação Editorial'


@pytest.mark.django_db
def test_status_ignores_the_stale_status_stored_in_the_revision(editor, site, category):
    """A view entrega a última revisão, que guarda o `status` de quando foi salva."""
    article = _article(site, category, editor, 'antiga')
    article.status = Article.Status.PUBLISHED  # como viria de uma revisão antiga

    assert _status(article)['key'] == 'draft'


# ── Criação e cadastros sem rascunho ───────────────────────────────────────


@pytest.mark.django_db
def test_create_view_bar(client, editor):
    client.force_login(editor)

    bar = _bar(client.get(reverse('wagtailsnippets_news_article:add')).content.decode())

    assert 'id="nr-editorbar-title">Nova notícia</h1>' in bar
    assert 'Ainda não salvo' in bar
    assert 'nr-menu__item' not in bar  # sem copiar/remover antes de existir
    assert 'aria-label="Histórico"' not in bar


@pytest.mark.django_db
def test_category_editor_has_the_bar_without_status(client, root, category):
    client.force_login(root)

    html = client.get(reverse('wagtailsnippets_news_category:edit', args=[category.pk])).content.decode()
    bar = _bar(html)

    assert '>Categorias</a>' in bar
    assert 'nr-editorbar__status' not in bar
    assert 'nr-pub' not in bar
    assert 'name="action-publish"' not in html


# ── Salvamento automático ──────────────────────────────────────────────────


@pytest.mark.django_db
def test_autosave_response_refreshes_the_bar(client, editor, site, category):
    article = _article(site, category, editor, 'autosave')
    article.save_revision(user=editor).publish(user=editor)
    client.force_login(editor)
    url = _edit_url(article)
    data = _form_data(client.get(url), title='Título salvo sozinho')

    response = client.post(url, data, HTTP_ACCEPT='application/json')
    partials = response.json()['html']

    assert response.json()['success'] is True
    assert 'data-w-teleport-target-value="#nr-editorbar-title"' in partials
    assert 'Título salvo sozinho' in partials
    assert 'data-w-teleport-target-value="#nr-editorbar-state"' in partials
    assert 'Alterações não publicadas' in partials
    assert 'data-w-teleport-target-value="#nr-editorbar-publication"' in partials
    assert 'class="nr-pub__button nr-pub--published"' in partials
    assert 'data-w-teleport-target-value="#nr-editorbar-quick"' in partials
    assert 'data-w-teleport-target-value="#nr-editorbar-danger"' in partials
    assert 'data-w-teleport-target-value="#nr-editorbar-more"' in partials


@pytest.mark.django_db
def test_validation_error_button_is_in_portuguese(client, editor, site, category):
    """O catálogo pt-BR do Wagtail 7.4.2 não traduz "Go to the first error"."""
    article = _article(site, category, editor, 'erro')
    article.save_revision(user=editor)
    client.force_login(editor)
    url = _edit_url(article)
    data = _form_data(client.get(url), title='', **{'action-publish': 'action-publish'})

    html = client.post(url, data).content.decode()

    assert 'Ir para o primeiro erro' in html
    assert 'Go to the first error' not in html
