"""Notificações do painel (newsroom/partials/toasts.html e wagtailadmin/base.html).

Cobrem a marcação nas três cascas: a visão geral e o Unfold pelo modelo
compartilhado, o Wagtail pelo próprio base.html, que mantém o controlador
w-messages e os modelos das notificações criadas pelo JS. Entrar descendo do
topo, fechar e sumir sozinhas (static/newsroom/js/newsroom.js e o CSS) foram
validados no navegador.
"""

import re

import pytest
from django.contrib.messages import constants
from django.contrib.messages.storage.base import Message
from django.template.loader import render_to_string
from django.urls import reverse

from apps.accounts.models import CustomUser


@pytest.fixture
def root(make_panel_user):
    return make_panel_user('toast_root', role=CustomUser.Role.SUPER_ADMIN, is_staff=True, is_superuser=True)


def test_shared_template_renders_each_level_with_its_icon():
    html = render_to_string('newsroom/partials/toasts.html', {'messages': [
        Message(constants.SUCCESS, 'Salvo.'),
        Message(constants.WARNING, 'Cuidado.'),
        Message(constants.ERROR, 'Falhou.'),
        Message(constants.INFO, 'Para saber.'),
    ]})

    assert '<ul class="nr-toasts" role="status" aria-live="polite">' in html
    toasts = re.findall(r'<li class="nr-toast nr-toast--(\w+)">.*?#nr-(\w+)".*?<div class="nr-toast__text">([^<]+)</div>', html, re.S)
    assert toasts == [
        ('success', 'check', 'Salvo.'),
        ('warning', 'alert', 'Cuidado.'),
        ('error', 'alert', 'Falhou.'),
        ('info', 'info', 'Para saber.'),
    ]


def test_shared_template_renders_nothing_without_messages():
    assert render_to_string('newsroom/partials/toasts.html', {'messages': []}).strip() == ''


@pytest.mark.django_db
def test_unfold_messages_become_toasts(client, root):
    client.force_login(root)
    url = reverse('admin:hiring_department_changelist')

    # Ação em massa sem nada selecionado: o Django avisa e não muda nada.
    response = client.post(url, {'action': 'delete_selected', 'index': 0}, follow=True)
    html = response.content.decode()

    assert '<li class="nr-toast nr-toast--warning">' in html
    assert 'Nenhum item foi modificado' in html


@pytest.mark.django_db
def test_wagtail_messages_keep_the_controller_and_become_toasts(client, root):
    client.force_login(root)

    html = client.get(reverse('wagtailsnippets_news_category:list')).content.decode()
    host = re.search(r'<div class="nr-toasts-host".*?</div>\s*\n', html, re.S).group(0)

    assert 'data-controller="w-messages"' in host
    assert '<ul class="nr-toasts" data-w-messages-target="container">' in host
    for level in ('success', 'error', 'warning'):
        # Modelos do JS: o texto entra em .nr-toast__text, não no último filho
        # (que vira o botão de fechar).
        assert f'data-type="{level}" data-selector=".nr-toast__text"' in host
        assert f'<li class="nr-toast nr-toast--{level} {level}">' in host
    assert 'class="messages"' not in html
