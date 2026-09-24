"""Governança editorial: quem altera qual notícia, campos sensíveis, cópia,
aprovação do fluxo e redirecionamento ao trocar o endereço.

Regras decididas com a redação (apps/news/permissions.py):
* quem publica (Editor de Notícias, Administrador Geral, superusuário) altera
  qualquer notícia;
* o Repórter altera as próprias em qualquer estado e as dos colegas só
  enquanto forem rascunho;
* o Editor de Notícias aprova a etapa "Aprovação Editorial" (migração 0027);
* trocar o slug de uma notícia que já esteve no ar redireciona (301) o
  endereço antigo para o novo.
"""

import re
from html.parser import HTMLParser

import pytest
from django.urls import reverse
from wagtail.contrib.redirects.models import Redirect
from wagtail.models import GroupApprovalTask

from apps.accounts.models import CustomUser
from apps.news.models import Article, Category
from apps.news.permissions import can_edit_article

# ── Apoio ──────────────────────────────────────────────────────────────────


@pytest.fixture
def site(current_site):
    return current_site


@pytest.fixture
def category(db):
    return Category.objects.create(name='Geral', slug='geral')


@pytest.fixture
def users(make_panel_user):
    return {
        'reporter': make_panel_user('gv_reporter', role=CustomUser.Role.REPORTER),
        'colleague': make_panel_user('gv_colleague', role=CustomUser.Role.REPORTER),
        'editor': make_panel_user('gv_editor', role=CustomUser.Role.NEWS_EDITOR),
        'general_admin': make_panel_user('gv_admin', role=CustomUser.Role.SUPER_ADMIN, is_staff=True),
        'superuser': make_panel_user('gv_root', role=CustomUser.Role.SUPER_ADMIN, is_staff=True, is_superuser=True),
        'reader': make_panel_user('gv_reader', role=CustomUser.Role.READER),
    }


def _article(site, category, author, slug, state='draft'):
    article = Article.objects.create(
        title=f'Notícia {slug}', slug=slug, content='<p>.</p>', site=site,
        category=category, author=author,
    )
    if state in ('published', 'archived'):
        article.save_revision(user=author).publish()
    if state == 'archived':
        article.refresh_from_db()
        article.unpublish()
    article.refresh_from_db()
    return article


class _FormReader(HTMLParser):
    """Lê o formulário renderizado como o navegador enviaria (sem o JS)."""

    def __init__(self):
        super().__init__()
        self.data = {}
        self._select = None
        self._textarea = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        name = attrs.get('name')
        if tag == 'input' and name:
            kind = attrs.get('type', 'text')
            if kind in ('submit', 'file', 'radio'):
                return
            if kind == 'checkbox':
                if 'checked' in attrs:
                    self.data[name] = attrs.get('value') or 'on'
                return
            self.data.setdefault(name, attrs.get('value') or '')
        elif tag == 'select' and name:
            self._select = name
            if 'multiple' not in attrs:
                self.data.setdefault(name, '')
        elif tag == 'option' and self._select and 'selected' in attrs:
            self.data[self._select] = attrs.get('value') or ''
        elif tag == 'textarea' and name:
            self._textarea = name
            self.data.setdefault(name, '')

    def handle_endtag(self, tag):
        if tag == 'select':
            self._select = None
        elif tag == 'textarea':
            self._textarea = None

    def handle_data(self, data):
        if self._textarea:
            self.data[self._textarea] += data


def _form_data(response, **overrides):
    reader = _FormReader()
    reader.feed(response.content.decode())
    data = {key: value for key, value in reader.data.items() if key}
    # O StreamField monta este contador no navegador; sem blocos, zero.
    data.setdefault('body-count', '0')
    data.update(overrides)
    return data


ADD_URL = 'wagtailsnippets_news_article:add'


def _edit_url(article):
    return reverse('wagtailsnippets_news_article:edit', args=[article.pk])


# ── Matriz: quem altera qual notícia ───────────────────────────────────────

STATES = ('draft', 'published', 'archived')
EXPECTED = {
    # (cargo, dono da notícia): estados em que pode alterar
    ('reporter', 'own'): {'draft', 'published', 'archived'},
    ('reporter', 'colleague'): {'draft'},
    ('editor', 'own'): set(STATES),
    ('editor', 'colleague'): set(STATES),
    ('general_admin', 'own'): set(STATES),
    ('general_admin', 'colleague'): set(STATES),
    ('superuser', 'own'): set(STATES),
    ('superuser', 'colleague'): set(STATES),
}


@pytest.mark.django_db
@pytest.mark.parametrize('role,owner', list(EXPECTED))
@pytest.mark.parametrize('state', STATES)
def test_permission_matrix(client, users, site, category, role, owner, state):
    user = users[role]
    author = user if owner == 'own' else users['colleague']
    article = _article(site, category, author, f'm-{role}-{owner}-{state}', state)
    allowed = state in EXPECTED[(role, owner)]

    # A regra…
    assert can_edit_article(user, article) is allowed
    # …a política do snippet (listagem, botões, cópia)…
    policy = Article.snippet_viewset.permission_policy
    assert policy.user_has_permission_for_instance(user, 'change', article) is allowed

    # …e a porta da edição do Wagtail dizem a mesma coisa.
    client.force_login(user)
    response = client.get(_edit_url(article))
    if allowed:
        assert response.status_code == 200
    else:
        assert response.status_code == 302


@pytest.mark.django_db
def test_denied_edit_post_does_not_change_the_article(client, users, site, category):
    """Ocultar o botão não basta: o POST direto também é barrado no servidor."""
    article = _article(site, category, users['colleague'], 'publicada-do-colega', 'published')
    client.force_login(users['reporter'])

    response = client.post(_edit_url(article), {'title': 'Sequestrada', 'slug': 'sequestrada'})

    # Volta para a ficha somente leitura, explicando a regra.
    assert response.status_code == 302
    assert response['Location'] == reverse('wagtailsnippets_news_article:inspect', args=[article.pk])
    article.refresh_from_db()
    assert (article.title, article.slug) == ('Notícia publicada-do-colega', 'publicada-do-colega')
    assert article.revisions.count() == 1


@pytest.mark.django_db
def test_restoring_a_revision_follows_the_same_rule(client, users, site, category):
    """Restaurar revisão é outra porta de escrita (herda da edição)."""
    article = _article(site, category, users['colleague'], 'retirada-do-colega', 'archived')
    revision = article.get_latest_revision()
    revert_url = reverse('wagtailsnippets_news_article:revisions_revert', args=[article.pk, revision.pk])

    client.force_login(users['reporter'])
    assert client.get(revert_url).status_code == 302
    client.force_login(users['editor'])
    assert client.get(revert_url).status_code == 200


@pytest.mark.django_db
def test_listing_marks_only_featured_articles(client, users, site, category):
    _article(site, category, users['editor'], 'destaque', 'published')
    _article(site, category, users['editor'], 'comum', 'published')
    Article.objects.filter(slug='destaque').update(is_featured=True)
    client.force_login(users['editor'])

    content = client.get(reverse('wagtailsnippets_news_article:list')).content.decode()

    assert not re.search(r'<td[^>]*>\s*(True|False)\s*</td>', content)
    assert content.count('Em destaque') == 1


@pytest.mark.django_db
def test_reader_role_has_no_write_access(users, site, category):
    article = _article(site, category, users['colleague'], 'para-leitor')
    assert can_edit_article(users['reader'], article) is False


@pytest.mark.django_db
def test_listing_links_follow_the_per_article_rule(client, users, site, category):
    own = _article(site, category, users['reporter'], 'minha', 'published')
    colleague_draft = _article(site, category, users['colleague'], 'rascunho-colega')
    colleague_live = _article(site, category, users['colleague'], 'no-ar-colega', 'published')
    client.force_login(users['reporter'])

    content = client.get(reverse('wagtailsnippets_news_article:list')).content.decode()

    assert _edit_url(own) in content
    assert _edit_url(colleague_draft) in content
    assert _edit_url(colleague_live) not in content
    assert reverse('wagtailsnippets_news_article:inspect', args=[colleague_live.pk]) in content


# ── Campos sensíveis e autoria ─────────────────────────────────────────────

SENSITIVE_FIELDS = ('is_featured', 'site', 'author', 'go_live_at', 'expire_at')


@pytest.mark.django_db
def test_reporter_form_has_no_sensitive_fields(client, users, site, category):
    client.force_login(users['reporter'])
    form = client.get(reverse(ADD_URL)).context['form']

    for field in SENSITIVE_FIELDS:
        assert field not in form.fields
    # Tudo o que é conteúdo continua lá (nenhum bloco ou recurso cortado).
    for field in ('title', 'slug', 'excerpt', 'category', 'tags', 'body', 'featured_image_wagtail'):
        assert field in form.fields


@pytest.mark.django_db
def test_publisher_form_keeps_sensitive_fields(client, users, site, category):
    client.force_login(users['editor'])
    form = client.get(reverse(ADD_URL)).context['form']

    for field in SENSITIVE_FIELDS:
        assert field in form.fields


@pytest.mark.django_db
def test_author_choices_are_the_editorial_team(client, users, site, category):
    client.force_login(users['editor'])
    authors = set(client.get(reverse(ADD_URL)).context['form'].fields['author'].queryset)

    assert {users['reporter'], users['colleague'], users['editor'], users['superuser']} <= authors
    assert users['reader'] not in authors


@pytest.mark.django_db
def test_reporter_cannot_forge_sensitive_fields(client, users, site, category):
    """Campos fora do formulário são ignorados no servidor mesmo se enviados."""
    client.force_login(users['reporter'])
    data = _form_data(
        client.get(reverse(ADD_URL)),
        title='Pauta nova', slug='pauta-nova', category=str(category.pk),
        is_featured='on', author=str(users['editor'].pk), go_live_at='2030-01-01 10:00',
    )
    data.pop('tags', None)

    response = client.post(reverse(ADD_URL), data)

    assert response.status_code == 302
    article = Article.objects.get(slug='pauta-nova')
    assert article.author == users['reporter']
    assert article.site == site
    assert article.is_featured is False
    assert article.go_live_at is None
    assert article.status == Article.Status.DRAFT
    assert article.live is False


@pytest.mark.django_db
def test_publisher_new_article_defaults_to_self_as_author(client, users, site, category):
    client.force_login(users['editor'])
    form = client.get(reverse(ADD_URL)).context['form']
    assert form.initial.get('author') == users['editor'].pk
    assert form.initial.get('site') == site.pk


# ── Copiar ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_copy_url_never_writes_over_the_original(client, users, site, category):
    """O CopyView do Wagtail salvaria um POST sobre a notícia de origem."""
    original = _article(site, category, users['colleague'], 'original', 'published')
    copy_url = reverse('wagtailsnippets_news_article:copy', args=[original.pk])
    client.force_login(users['reporter'])
    data = _form_data(client.get(copy_url), title='Cópia', slug='copia')
    data.pop('tags', None)

    assert client.post(copy_url, data).status_code == 405
    original.refresh_from_db()
    assert (original.slug, original.status, original.live) == ('original', Article.Status.PUBLISHED, True)
    assert Article.objects.count() == 1


@pytest.mark.django_db
def test_copy_creates_a_new_draft_signed_by_the_reporter(client, users, site, category):
    original = _article(site, category, users['colleague'], 'base', 'published')
    client.force_login(users['reporter'])
    copy_form = client.get(reverse('wagtailsnippets_news_article:copy', args=[original.pk]))
    data = _form_data(copy_form, title='Cópia', slug='copia')
    data.pop('tags', None)

    # O formulário da cópia é enviado para a adição.
    assert copy_form.context['action_url'] == reverse(ADD_URL)
    response = client.post(reverse(ADD_URL), data)

    assert response.status_code == 302
    copy = Article.objects.get(slug='copia')
    assert copy.pk != original.pk
    assert (copy.status, copy.live, copy.author) == (Article.Status.DRAFT, False, users['reporter'])
    original.refresh_from_db()
    assert (original.slug, original.live) == ('base', True)


# ── Fluxo de revisão: Editor de Notícias aprova ────────────────────────────


@pytest.mark.django_db
def test_editorial_task_approvers():
    task = GroupApprovalTask.objects.get(name='Aprovação Editorial')
    assert set(task.groups.values_list('name', flat=True)) >= {'Administrador Geral', 'Editor de Notícias'}


@pytest.mark.django_db
def test_editor_approves_and_publishes_reporter_submission(users, site, category):
    article = _article(site, category, users['reporter'], 'enviada')
    article.save_revision(user=users['reporter'])
    workflow_state = article.get_default_workflow().start(article, users['reporter'])
    task_state = workflow_state.current_task_state
    task = task_state.task.specific

    # O repórter envia, mas não aprova nem destrava.
    assert task.get_actions(article, users['reporter']) == []
    assert task.locked_for_user(article, users['reporter']) is True
    # O editor aprova.
    assert 'approve' in {name for name, _label, _extra in task.get_actions(article, users['editor'])}
    assert task.locked_for_user(article, users['editor']) is False

    task_state.approve(user=users['editor'])

    article.refresh_from_db()
    assert article.live is True
    assert article.status == Article.Status.PUBLISHED


# ── Redirecionamento ao trocar o endereço ──────────────────────────────────


def _rename(article, slug, user):
    article.slug = slug
    article.save_revision(user=user).publish(user=user)
    article.refresh_from_db()


def _redirects():
    return dict(Redirect.objects.values_list('old_path', 'redirect_link'))


@pytest.mark.django_db
def test_renaming_a_published_article_redirects_the_old_address(client, users, site, category):
    article = _article(site, category, users['editor'], 'endereco-antigo', 'published')

    _rename(article, 'endereco-novo', users['editor'])

    assert _redirects() == {'/news/endereco-antigo': '/news/endereco-novo/'}
    response = client.get('/news/endereco-antigo/')
    assert response.status_code == 301
    assert response['Location'] == '/news/endereco-novo/'
    assert client.get('/news/endereco-novo/').status_code == 200


@pytest.mark.django_db
def test_editing_a_live_article_redirects_only_when_published(users, site, category):
    """Rascunho sobre notícia no ar não mexe no endereço público."""
    article = _article(site, category, users['editor'], 'no-ar', 'published')

    article.slug = 'rascunho-de-endereco'
    article.save_revision(user=users['editor'])

    assert Redirect.objects.count() == 0
    article.refresh_from_db()
    assert article.slug == 'no-ar'


@pytest.mark.django_db
def test_renaming_a_draft_creates_no_redirect(users, site, category):
    article = _article(site, category, users['reporter'], 'rascunho')

    article.slug = 'rascunho-renomeado'
    article.save()

    assert Redirect.objects.count() == 0


@pytest.mark.django_db
def test_renaming_an_archived_article_keeps_old_links(users, site, category):
    article = _article(site, category, users['editor'], 'retirada', 'archived')

    article.slug = 'retirada-renomeada'
    article.save()

    assert _redirects() == {'/news/retirada': '/news/retirada-renomeada/'}


@pytest.mark.django_db
def test_redirect_chains_collapse_and_renaming_back_removes_the_loop(users, site, category):
    article = _article(site, category, users['editor'], 'a', 'published')

    _rename(article, 'b', users['editor'])
    _rename(article, 'c', users['editor'])
    assert _redirects() == {'/news/a': '/news/c/', '/news/b': '/news/c/'}

    _rename(article, 'a', users['editor'])
    assert _redirects() == {'/news/b': '/news/a/', '/news/c': '/news/a/'}
