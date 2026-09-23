"""Cabeçalho das listas do Django admin (Unfold) no padrão do painel.

Substitui o antigo cartão "Rotina da tela" (templates/admin/includes/
model_list_help.html): título com a contagem, uma linha de descrição, a ação
principal à direita, o guia como botão discreto e os filtros rápidos como abas
com contagem e estado ativo, o mesmo componente das abas da visão geral.

Os dados continuam vindo do que cada tela declara no AdminUXMixin
(apps/common/admin_mixins.py): ``ux_list_title``, ``ux_list_description``,
``ux_list_actions`` e ``ux_list_filters``. Telas sem o mixin recebem o nome
do modelo e o botão de adicionar, se a pessoa puder adicionar.
"""

from urllib.parse import parse_qsl, urlencode

from django.contrib.admin.views.main import ORDER_VAR, PAGE_VAR, SEARCH_VAR
from django.core.exceptions import FieldError, ValidationError
from django.urls import NoReverseMatch, reverse

# Parâmetros da lista que não são filtro: não contam para decidir a aba ativa.
NOT_FILTERS = {ORDER_VAR, PAGE_VAR, SEARCH_VAR, '_changelist_filters', 'e'}


def _params(query):
    return dict(parse_qsl(query.lstrip('?'), keep_blank_values=True))


def _count(model_admin, request, params):
    """Contagem da aba aplicando os parâmetros ``campo__exact=valor`` direto
    no queryset da tela (o mesmo que o admin aplica). Se a aba usar um filtro
    que não é campo do modelo, a contagem é omitida em vez de chutada."""
    try:
        return model_admin.get_queryset(request).filter(**params).count()
    except (FieldError, ValidationError, ValueError, TypeError):
        return None


def _tabs(model_admin, request, cl):
    filters = list(getattr(model_admin, 'ux_list_filters', None) or [])
    if not filters:
        return []
    current = {key: value for key, value in request.GET.items() if key not in NOT_FILTERS}
    base = request.path
    tabs = [{
        'label': getattr(model_admin, 'ux_list_all_label', 'Todos'),
        'url': base,
        'count': model_admin.get_queryset(request).count(),
        'active': not current,
    }]
    for item in filters:
        params = _params(str(item.get('url', '')))
        tabs.append({
            'label': item.get('label', ''),
            'url': f'{base}?{urlencode(params)}',
            'count': _count(model_admin, request, params),
            'active': bool(params) and current == params,
        })
    return tabs


def _actions(model_admin, request, cl, has_add_permission):
    primary = None
    secondary = []
    for item in getattr(model_admin, 'ux_list_actions', None) or []:
        action = {'label': item.get('label', ''), 'url': str(item.get('url', ''))}
        if item.get('kind') == 'primary' and primary is None:
            primary = action
        else:
            secondary.append(action)
    if primary is None and has_add_permission:
        opts = cl.opts
        try:
            primary = {
                'label': f'Adicionar {opts.verbose_name}',
                'url': reverse(f'admin:{opts.app_label}_{opts.model_name}_add'),
            }
        except NoReverseMatch:
            primary = None
    return primary, secondary


def list_header(context):
    cl = context.get('cl')
    request = context.get('request')
    if cl is None or request is None:
        return None
    model_admin = cl.model_admin
    primary, secondary = _actions(model_admin, request, cl, context.get('has_add_permission'))
    return {
        'title': getattr(model_admin, 'ux_list_title', '') or str(cl.opts.verbose_name_plural).capitalize(),
        'description': getattr(model_admin, 'ux_list_description', ''),
        'count': cl.result_count,
        'filtered': cl.full_result_count is not None and cl.result_count != cl.full_result_count,
        'total': cl.full_result_count,
        'primary': primary,
        'secondary': secondary,
        'tabs': _tabs(model_admin, request, cl),
        'empty_message': getattr(model_admin, 'ux_empty_message', ''),
    }
