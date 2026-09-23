"""Barra dos formulários do Django admin (Unfold), no modelo da barra do editor
do Wagtail (apps/common/newsroom/editor.py).

Uma barra só no topo do formulário, no lugar do cartão "Edição orientada", do
cartão "Próximos passos" e da faixa de botões do rodapé do Unfold:

- à esquerda, voltar para a lista, o título do registro e o selo de estado
  (``AdminUXMixin.nr_status``), ou "Somente leitura" para quem só pode ver;
- à direita, as ferramentas (Guia, com o texto que cada tela declara em
  ``ux_form_*`` e os atalhos de ``ux_after_save_actions``; Histórico; Ver no
  site), as ações de salvar e o menu ⋯ (links da tela, como "Alterar
  senha", e Remover).

Os botões de salvar são os do próprio Django: ``<button type="submit">`` com o
mesmo ``name`` (``_save``, ``_continue``, ``_addanother``, ``_saveasnew``) e o
atributo ``form`` apontando para o formulário, como os do rodapé do Unfold, que
também ficavam fora dele. Quais aparecem vem de ``submit_row`` do Django, a
mesma regra de permissões do rodapé.
"""

from django.contrib.admin.templatetags.admin_modify import submit_row
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.admin.utils import quote
from django.urls import NoReverseMatch, reverse


def _url(name, *args):
    try:
        return reverse(name, args=args)
    except NoReverseMatch:
        return ''


def _preserved(context, opts, url):
    if not url:
        return ''
    return add_preserved_filters({'preserved_filters': context.get('preserved_filters'), 'opts': opts}, url)


def _guide(model_admin):
    steps = [str(step) for step in getattr(model_admin, 'ux_form_steps', None) or []]
    links = [
        {'label': str(item.get('label', '')), 'url': str(item.get('url', ''))}
        for item in getattr(model_admin, 'ux_after_save_actions', None) or []
        if item.get('url')
    ]
    title = str(getattr(model_admin, 'ux_form_title', '') or '')
    description = str(getattr(model_admin, 'ux_form_description', '') or '')
    if not (title or description or steps or links):
        return None
    return {
        'title': title,
        'description': description,
        'steps': steps,
        'links_title': str(getattr(model_admin, 'ux_after_save_title', '') or 'Atalhos'),
        'links_description': str(getattr(model_admin, 'ux_after_save_description', '') or ''),
        'links': links,
    }


def _actions(context, flags):
    """Botões de salvar na ordem da barra: o secundário à vista, o principal e,
    no menu da seta, os demais. Os rótulos longos do Django ("Salvar e
    adicionar outro(a)") ficam curtos e sem "(a)"."""
    can_change = flags.get('can_change')
    primary = {'name': '_save', 'label': 'Salvar'} if flags.get('show_save') else None
    secondary = None
    if flags.get('show_save_and_continue'):
        secondary = {
            'name': '_continue',
            'label': 'Salvar e continuar editando' if can_change else 'Salvar e ver',
            'short': 'Continuar',
        }
    menu = []
    if flags.get('show_save_and_add_another'):
        menu.append({'name': '_addanother', 'label': 'Salvar e adicionar outro', 'icon': 'plus'})
    if flags.get('show_save_as_new'):
        menu.append({'name': '_saveasnew', 'label': 'Salvar como novo', 'icon': 'copy'})
    # Ações extras do Unfold (actions_submit_line), se alguma tela declarar.
    for action in context.get('actions_submit_line') or []:
        attrs = getattr(action, 'attrs', None) or {}
        name = attrs.get('name') or getattr(action, 'action_name', '')
        if name:
            menu.append({'name': name, 'label': str(getattr(action, 'description', name)), 'icon': 'check'})
    if primary is None and secondary is not None:
        primary, secondary = {**secondary, 'short': ''}, None
    return {'primary': primary, 'secondary': secondary, 'menu': menu}


def form_bar(context):
    adminform = context.get('adminform')
    opts = context.get('opts')
    request = context.get('request')
    if adminform is None or opts is None or request is None or context.get('is_popup'):
        return {'enabled': False}

    model_admin = adminform.model_admin
    obj = context.get('original')
    change = bool(context.get('change')) and obj is not None
    flags = submit_row(context)
    name = f'admin:{opts.app_label}_{opts.model_name}'

    plural = str(opts.verbose_name_plural).capitalize()
    # Quem só pode adicionar não abre a lista (403): sem o voltar, como no Django.
    back_url = ''
    if context.get('has_view_permission'):
        back_url = _preserved(context, opts, _url(f'{name}_changelist'))
    if change:
        title = str(obj)
    else:
        title = str(getattr(model_admin, 'ux_form_new_title', '') or f'Adicionar {opts.verbose_name}')

    status = None
    readonly = change and not flags.get('can_change')
    if change and hasattr(model_admin, 'nr_status'):
        status = model_admin.nr_status(obj)

    history_url = ''
    if change and context.get('has_view_permission'):
        history_url = _preserved(context, opts, _url(f'{name}_history', quote(obj.pk)))
    site_url = context.get('absolute_url') if change and context.get('has_absolute_url') else ''

    delete_url = ''
    if change and flags.get('show_delete_link'):
        delete_url = _preserved(context, opts, _url(f'{name}_delete', quote(obj.pk)))
    links = []
    if change and hasattr(model_admin, 'nr_form_links'):
        links = model_admin.nr_form_links(request, obj)

    return {
        'enabled': True,
        'form_id': f'{opts.model_name}_form',
        'back': {'url': back_url, 'label': plural} if back_url else None,
        'title': title,
        'status': status,
        'readonly': readonly,
        'guide': _guide(model_admin),
        'history_url': history_url,
        'site_url': site_url,
        'actions': _actions(context, flags),
        'links': links,
        'delete_url': delete_url,
    }
