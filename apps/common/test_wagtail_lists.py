"""Cabeçalho do painel em todas as listagens do Wagtail (apps/common/newsroom/wagtail_lists.py,
templates/wagtailadmin/generic/listing.html e templates/newsroom/wagtail/).

Cobrem: cada seção da sidebar com o cabeçalho do painel no lugar do
slim_header, com o título da sidebar, a contagem e o botão principal no gênero
certo; o menu ⋯ do Wagtail preservado; a busca da biblioteca de imagens com a
ordenação; e as frases de lista vazia. O desenho foi validado no navegador.
"""

import re

import pytest
from django.urls import reverse

from apps.accounts.models import CustomUser
from apps.common.newsroom.wagtail_lists import LISTS

SECTIONS = [
    ('news_workflow_report', {}),
    ('wagtailimages:index', {}),
    ('wagtaildocs:index', {}),
    ('wagtailsnippets_news_comment:list', {}),
    ('wagtailsnippets_news_newslettersubscription:list', {}),
    ('wagtailsnippets_news_newsletterdelivery:list', {}),
    ('wagtailsnippets_news_category:list', {}),
    ('wagtailsnippets_news_tag:list', {}),
    ('wagtailsnippets_news_newshomeconfig:list', {}),
    ('wagtailsnippets_common_siteextension:list', {}),
    ('wagtailadmin_reports:workflow', {}),
    ('wagtailadmin_reports:workflow_tasks', {}),
    ('wagtailadmin_reports:site_history', {}),
    ('wagtailadmin_workflows:index', {}),
    ('wagtailadmin_workflows:task_index', {}),
    ('wagtailusers_groups:index', {}),
    ('wagtailadmin_collections:index', {}),
    ('wagtailredirects:index', {}),
]


@pytest.fixture
def root(make_panel_user):
    return make_panel_user('wl_root', role=CustomUser.Role.SUPER_ADMIN, is_staff=True, is_superuser=True)


@pytest.mark.django_db
@pytest.mark.parametrize('name, kwargs', SECTIONS, ids=[name for name, _ in SECTIONS])
def test_every_wagtail_listing_uses_the_panel_header(client, root, name, kwargs):
    client.force_login(root)

    response = client.get(reverse(name, kwargs=kwargs))
    html = response.content.decode()
    config = LISTS[name]

    assert response.status_code == 200
    assert '<header class="w-slim-header' not in html
    assert re.search(r'<h1 class="nr-listhead__title">\s*' + re.escape(config['title']), html)
    assert config['description'] in html
    if 'add' in config:
        assert f'<span>{config["add"]}</span>' in html


@pytest.mark.django_db
def test_header_keeps_the_wagtail_more_menu(client, root):
    client.force_login(root)

    html = client.get(reverse('wagtailadmin_reports:site_history')).content.decode()

    # Exportar (XLSX/CSV) continua no ⋯ do Wagtail, agora dentro do cabeçalho.
    head = re.search(r'<div class="nr-listhead__actions">.*?</div>\s*</div>\s*</div>', html, re.S).group(0)
    assert 'class="nr-listhead__more"' in head
    assert 'w-dropdown' in head


@pytest.mark.django_db
def test_image_library_keeps_ordering_and_layout(client, root):
    client.force_login(root)

    html = client.get(reverse('wagtailimages:index')).content.decode()
    toolbar = re.search(r'<div class="nr-wlist__toolbar".*?</form>', html, re.S).group(0)

    assert 'id="order_images_by"' in toolbar
    assert 'w-layout-switch-control' in toolbar
    assert 'data-controller="w-swap"' in toolbar


@pytest.mark.django_db
@pytest.mark.parametrize('name', [
    'wagtailsnippets_news_comment:list',
    'wagtailadmin_reports:workflow',
    'wagtailadmin_collections:index',
    'wagtailredirects:index',
    'wagtaildocs:index',
])
def test_empty_lists_speak_portuguese(client, root, name):
    client.force_login(root)

    html = client.get(reverse(name)).content.decode()

    assert f'<span>{LISTS[name]["empty"]}</span>' in html
    assert 'Por que não' not in html
    assert 'Porque não' not in html


@pytest.mark.django_db
def test_empty_search_says_nothing_was_found(client, root):
    client.force_login(root)

    html = client.get(reverse('wagtaildocs:index_results'), {'q': 'nada-com-isso'}).content.decode()

    assert 'Nada encontrado com essa busca ou esses filtros.' in html
