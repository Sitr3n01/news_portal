"""Formulários do Django admin (Unfold) com a barra do painel.

Cobrem: a barra no lugar do cartão "Edição orientada", do cartão "Próximos
passos" e da faixa de botões do rodapé; título, selo de estado e "Somente
leitura"; os botões de salvar com os nomes que o Django espera (e o "Salvar"
invisível que mantém o Enter salvando); Guia, Histórico e o menu ⋯ conforme as
permissões; as janelas popup sem barra; as seções recolhidas depois das abas;
os formulários de usuário com os campos do Unfold; e o envio de cada botão. O
comportamento no navegador (barra presa ao rolar, "Alterações não salvas",
Ctrl+S, celular) foi validado à parte.
"""

import re

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from apps.accounts.models import CustomUser
from apps.contact.models import ContactInquiry
from apps.school.models import SchoolHomeConfig


@pytest.fixture
def root(make_panel_user):
    return make_panel_user('af_root', role=CustomUser.Role.SUPER_ADMIN, is_staff=True, is_superuser=True)


@pytest.fixture
def inquiry(current_site):
    return ContactInquiry.objects.create(site=current_site, name='Maria', email='maria@example.com', message='Oi')


def _bar(content):
    start = content.index('<section class="nr-editorbar nr-formbar"')
    return content[start:content.index('</section>', start)]


def _change(client, inquiry, **params):
    return client.get(reverse('admin:contact_contactinquiry_change', args=[inquiry.pk]), params).content.decode()


@pytest.mark.django_db
def test_form_bar_replaces_guidance_cards_and_bottom_row(client, root, inquiry):
    client.force_login(root)

    content = _change(client, inquiry)
    bar = _bar(content)

    assert 'kb-model-guide' not in content
    assert 'Edição orientada' not in content
    assert 'kb-form-next-steps' not in content
    assert 'id="submit-row"' not in content
    assert '<h1 class="nr-editorbar__title">Maria - general</h1>' in bar
    assert 'nr-status nr-status--info nr-editorbar__status">Nova<' in bar
    assert 'aria-label="Voltar para Mensagens de contato"' in bar
    assert reverse('admin:contact_contactinquiry_changelist') in bar


@pytest.mark.django_db
def test_save_buttons_keep_django_names_and_enter_default(client, root, inquiry):
    client.force_login(root)

    bar = _bar(_change(client, inquiry))
    buttons = re.findall(r'<button type="submit" form="contactinquiry_form" name="(\w+)" class="([^"]+)"', bar)

    # O primeiro botão ligado ao formulário é o do Enter: "Salvar", invisível.
    assert buttons[0] == ('_save', 'nr-sr-only')
    names = [name for name, _classes in buttons]
    assert names.count('_save') == 2
    assert '_continue' in names
    assert '_addanother' in names
    assert '>Salvar e continuar editando<' in bar
    assert '>Salvar e adicionar outro<' in bar
    assert 'outro(a)' not in bar


@pytest.mark.django_db
def test_guide_history_and_more_menu(client, root, inquiry):
    client.force_login(root)

    bar = _bar(_change(client, inquiry))

    assert 'aria-label="Guia desta tela"' in bar
    assert 'Atendimento de mensagem' in bar
    assert 'Leia a mensagem e identifique o assunto.' in bar
    assert 'Mensagens novas' in bar  # atalho de ux_after_save_actions
    assert reverse('admin:contact_contactinquiry_history', args=[inquiry.pk]) in bar
    assert reverse('admin:contact_contactinquiry_delete', args=[inquiry.pk]) in bar
    assert 'nr-menu__item is-danger' in bar


@pytest.mark.django_db
def test_add_form_has_title_and_no_history_or_delete(client, root):
    client.force_login(root)

    content = client.get(reverse('admin:contact_contactinquiry_add')).content.decode()
    bar = _bar(content)

    assert '<h1 class="nr-editorbar__title">Adicionar Mensagem de Contato</h1>' in bar
    assert 'Histórico' not in bar
    assert 'is-danger' not in bar
    assert 'nr-editorbar__status' not in bar


@pytest.mark.django_db
def test_view_only_form_is_read_only(client, make_panel_user, inquiry):
    viewer = make_panel_user('af_viewer', role=CustomUser.Role.READER, is_staff=True)
    viewer.user_permissions.add(Permission.objects.get(codename='view_contactinquiry'))
    client.force_login(viewer)

    bar = _bar(_change(client, inquiry))

    assert 'Somente leitura' in bar
    assert 'type="submit"' not in bar
    assert 'is-danger' not in bar
    assert reverse('admin:contact_contactinquiry_history', args=[inquiry.pk]) in bar


@pytest.mark.django_db
def test_popup_form_keeps_native_submit_row(client, root, inquiry):
    client.force_login(root)

    content = _change(client, inquiry, _popup='1')

    assert 'nr-formbar' not in content
    assert 'name="_save"' in content


@pytest.mark.django_db
def test_collapsed_fieldsets_come_after_tabs(client, root, current_site):
    config, _ = SchoolHomeConfig.objects.get_or_create(site=current_site)
    client.force_login(root)

    content = client.get(reverse('admin:school_schoolhomeconfig_change', args=[config.pk])).content.decode()

    tabs = content.index('activeFieldsetTab')
    # Recolhidas ("collapse"), não são abas: antes vinham acima delas.
    assert content.index('Campos sem uso no site atual') > tabs
    assert re.search(r'>\s*Datas\s*<', content[tabs:])
    assert not re.search(r'>\s*Datas\s*<', content[:tabs])


@pytest.mark.django_db
@pytest.mark.parametrize(('button', 'expected'), [
    ('_save', 'admin:contact_contactinquiry_changelist'),
    ('_continue', 'admin:contact_contactinquiry_change'),
    ('_addanother', 'admin:contact_contactinquiry_add'),
])
def test_each_save_button_submits_like_django(client, root, inquiry, button, expected):
    client.force_login(root)
    url = reverse('admin:contact_contactinquiry_change', args=[inquiry.pk])

    response = client.post(url, {'status': 'read', button: '1'})

    inquiry.refresh_from_db()
    assert inquiry.status == 'read'
    assert response.status_code == 302
    args = [inquiry.pk] if expected.endswith('_change') else []
    assert response['Location'].split('?')[0] == reverse(expected, args=args)


@pytest.mark.django_db
def test_user_forms_use_unfold_widgets_and_password_link(client, root):
    client.force_login(root)

    add = client.get(reverse('admin:accounts_customuser_add')).content.decode()
    change = client.get(reverse('admin:accounts_customuser_change', args=[root.pk])).content.decode()
    password = client.get(reverse('admin:auth_user_password_change', args=[root.pk])).content.decode()

    # Campos de senha com as classes do Unfold (antes ficavam sem borda nem fundo).
    assert re.search(r'<input type="password" name="password1"[^>]*class="[^"]*border', add)
    assert 'Depois de criar o usuário' in add
    assert "After you've created a user" not in add
    assert '#1f2937' not in add
    assert 'Alterar senha' in _bar(change)
    assert reverse('admin:auth_user_password_change', args=[root.pk]) in _bar(change)
    assert re.search(r'<input type="password" name="password1"[^>]*class="[^"]*border', password)


@pytest.mark.django_db
def test_select_placeholder_is_in_portuguese(client, root):
    client.force_login(root)

    content = client.get(reverse('admin:school_page_add')).content.decode()

    assert 'Select value' not in content
    assert '>Selecione<' in content


@pytest.mark.django_db
def test_forms_without_tabs_keep_the_declared_fieldset_order(client, root):
    client.force_login(root)

    content = client.get(reverse('admin:social_socialaccount_add')).content.decode()

    # Só formulários com abas levam as seções recolhidas para depois delas.
    assert content.index('Credenciais de API') < content.index('Status da sincroniza')


@pytest.mark.django_db
def test_add_only_user_gets_no_back_link_to_a_forbidden_list(client, make_panel_user):
    adder = make_panel_user('af_adder', role=CustomUser.Role.READER, is_staff=True)
    adder.user_permissions.add(Permission.objects.get(codename='add_contactinquiry'))
    client.force_login(adder)

    content = client.get(reverse('admin:contact_contactinquiry_add')).content.decode()

    assert 'nr-editorbar__back' not in _bar(content)
    assert f'href="{reverse("admin:contact_contactinquiry_changelist")}"' not in content.split('<section class="nr-editorbar nr-formbar"')[0]


@pytest.mark.django_db
def test_unsaved_note_is_announced_and_shown_after_a_failed_save(client, root, inquiry):
    client.force_login(root)
    url = reverse('admin:contact_contactinquiry_change', args=[inquiry.pk])

    fresh = _bar(client.get(url).content.decode())
    failed = _bar(client.post(url, {'status': 'invalido', '_save': '1'}).content.decode())

    assert 'aria-label="Barra do formulário"' in fresh
    assert 'class="nr-editorbar__state" role="status"' in fresh
    assert 'data-nr-formbar-dirty hidden' in fresh
    assert 'data-nr-formbar-dirty>' in failed
