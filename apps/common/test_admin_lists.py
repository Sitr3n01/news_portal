"""Listas do Django admin (Unfold) no padrão do painel.

Cobrem: o cabeçalho (título, contagem, ação principal, guia e abas com
contagem e estado ativo), a barra de seleção no topo com um botão por ação e
o mesmo envio do Django (`index`, `action`, `select_across`), o menu ⋯ de cada
linha conforme as permissões, as colunas em português e o cabeçalho da tabela
traduzido. O comportamento no navegador (barra aparecendo com a seleção,
menu ⋯ posicionado, cartões compactos no celular) foi validado à parte.
"""

import re

import pytest
from django.contrib.auth.models import Permission
from django.template import Context, Template
from django.urls import reverse

from apps.accounts.models import CustomUser
from apps.contact.models import ContactInquiry

CHANGELIST = 'admin:contact_contactinquiry_changelist'


@pytest.fixture
def root(make_panel_user):
    return make_panel_user('al_root', role=CustomUser.Role.SUPER_ADMIN, is_staff=True, is_superuser=True)


@pytest.fixture
def inquiries(current_site):
    return [
        ContactInquiry.objects.create(site=current_site, name=f'Visitante {i}', email=f'v{i}@example.com', message='Oi', status=status)
        for i, status in enumerate(['new', 'new', 'read'])
    ]


def _section(content, start, end):
    begin = content.index(start)
    return content[begin:content.index(end, begin)]


@pytest.mark.django_db
def test_list_header_has_title_count_actions_and_tabs(client, root, inquiries):
    client.force_login(root)

    content = client.get(reverse(CHANGELIST)).content.decode()
    header = _section(content, '<header class="nr-listhead"', '</header>')

    assert 'Mensagens de contato' in header
    assert re.search(r'nr-listhead__count">\s*3\s*<', header)
    assert 'Guia Komuniki' in header
    assert 'nr-listhead__primary' in header
    tabs = re.findall(r'class="nr-tab( is-active)?"[^>]*>\s*([^<]+?)\s*<span class="nr-tab__count">(\d*)</span>', header)
    assert [(label, count) for _active, label, count in tabs][:3] == [('Todas', '3'), ('Novas', '2'), ('Lidas', '1')]
    assert tabs[0][0] == ' is-active'
    assert 'Rotina da tela' not in content


@pytest.mark.django_db
def test_list_header_marks_the_filtered_tab(client, root, inquiries):
    client.force_login(root)

    content = client.get(reverse(CHANGELIST), {'status__exact': 'new'}).content.decode()

    active = re.findall(r'class="nr-tab is-active"[^>]*>\s*([^<]+?)\s*<', content)
    assert active == ['Novas']


@pytest.mark.django_db
def test_selection_bar_has_one_button_per_action(client, root, inquiries):
    client.force_login(root)

    content = client.get(reverse(CHANGELIST)).content.decode()
    bar = _section(content, 'data-nr-selectionbar', '</form>')

    assert 'data-nr-action="mark_resolved"' in bar
    assert '>Arquivar mensagens</button>' in bar  # sem o "selecionadas"
    assert 'title="Arquivar mensagens selecionadas"' in bar
    assert 'data-nr-action="delete_selected"' in bar
    assert 'name="action" value="" data-nr-action-input' in bar
    assert 'name="select_across" value="0" class="select-across"' in bar
    assert 'x-model' not in bar.split('<table', 1)[0]
    assert 'data-actions-icnt="3"' in bar
    # O seletor de ação e o botão "Run" do Unfold não aparecem mais.
    assert 'name="action" x-model' not in content


@pytest.mark.django_db
def test_selection_bar_submits_like_the_django_action_form(client, root, inquiries):
    client.force_login(root)
    first, second, third = inquiries

    response = client.post(reverse(CHANGELIST), {
        'index': '0',
        'action': 'mark_resolved',
        'select_across': '0',
        '_selected_action': [first.pk, second.pk],
    })

    assert response.status_code == 302
    statuses = dict(ContactInquiry.objects.values_list('pk', 'status'))
    assert statuses == {first.pk: 'archived', second.pk: 'archived', third.pk: 'read'}


@pytest.mark.django_db
def test_row_menu_follows_permissions(client, make_panel_user, root, inquiries):
    client.force_login(root)
    content = client.get(reverse(CHANGELIST)).content.decode()
    menus = re.findall(r'<details class="nr-more nr-rowmenu".*?</details>', content, re.S)

    assert len(menus) == 3
    assert 'Mais ações: Visitante' in menus[0]
    assert '<span>Editar</span>' in menus[0]
    assert 'Remover' in menus[0]
    assert 'data-nr-row-actions' in menus[0]

    viewer = make_panel_user('al_viewer', role=CustomUser.Role.READER, is_staff=True)
    viewer.user_permissions.add(Permission.objects.get(codename='view_contactinquiry'))
    client.force_login(viewer)
    content = client.get(reverse(CHANGELIST)).content.decode()
    menu = re.search(r'<details class="nr-more nr-rowmenu".*?</details>', content, re.S).group(0)

    assert '<span>Abrir</span>' in menu
    assert '<span>Editar</span>' not in menu
    assert 'Remover' not in menu


@pytest.mark.django_db
def test_popup_list_has_no_row_menu(client, root, inquiries):
    client.force_login(root)

    content = client.get(reverse(CHANGELIST), {'_popup': '1'}).content.decode()

    assert 'nr-rowmenu' not in content


@pytest.mark.django_db
def test_list_columns_are_in_portuguese(client, root, inquiries):
    client.force_login(root)

    contact = client.get(reverse(CHANGELIST)).content.decode()
    thead = _section(contact, '<thead>', '</thead>')

    assert 'Recebida em' in thead
    assert 'Status' in thead
    assert 'Created at' not in thead
    assert 'Site' not in thead
    assert 'kb-read-btn' not in contact
    assert 'nr-status nr-status--info">Nova<' in contact
    assert 'Selecionar todos' in thead
    assert 'Select all rows' not in thead

    users = client.get(reverse('admin:accounts_customuser_changelist')).content.decode()
    thead = _section(users, '<thead>', '</thead>')

    assert 'Cargo' in thead
    assert 'method' not in thead


@pytest.mark.django_db
def test_sorted_column_shows_one_direction_arrow(client, root, inquiries):
    client.force_login(root)

    content = client.get(reverse(CHANGELIST), {'o': '-7'}).content.decode()
    sort = _section(content, '<div class="sortoptions nr-sort">', '</div>')

    assert 'nr-sort__toggle descending' in sort
    assert 'title="Tirar da ordenação"' in sort
    assert 'arrow_circle' not in sort


def test_action_label_drops_the_selected_word():
    template = Template('{% load newsroom %}{{ label|nr_action_label }}')

    def render(label):
        return template.render(Context({'label': label}))

    assert render('Arquivar mensagens selecionadas') == 'Arquivar mensagens'
    assert render('Ocultar posts selecionados do site') == 'Ocultar posts do site'
    assert render('Desativar inscrições selecionadas (spam/bots)') == 'Desativar inscrições (spam/bots)'
    assert render('Marcar como Aceito') == 'Marcar como Aceito'
