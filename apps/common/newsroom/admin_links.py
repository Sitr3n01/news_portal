"""Atalhos das telas do Django admin (o Guia da barra dos formulários e as
ações do cabeçalho das listas) só aparecem para quem pode abrir o destino.

As telas declaram os atalhos à mão (``ux_after_save_actions``,
``ux_list_actions``), sem saber quem vai vê-los: "Depoimentos" é só de
superusuário, "Usuários" pede permissão de ver usuários, e assim por diante.
Um atalho que termina em 403 não serve para nada.

- Tela de modelo do Django admin: a mesma regra da view (lista e formulário:
  ver ou alterar; adicionar: adicionar), lida do ModelAdmin que o Django
  anexa à view (``model_admin``).
- Tela do Wagtail: exige acesso ao Wagtail.
- ``permissions`` no próprio atalho: basta uma delas.
- Qualquer outro endereço (guias de operação, páginas do site) passa.
"""

from urllib.parse import urlsplit

from django.urls import Resolver404, resolve

from apps.accounts import panels


def link_allowed(request, link):
    user = request.user
    permissions = link.get('permissions')
    if permissions and not any(user.has_perm(permission) for permission in permissions):
        return False
    path = urlsplit(str(link.get('url', ''))).path
    if not path.startswith('/'):
        return True
    try:
        match = resolve(path)
    except Resolver404:
        return True
    model_admin = getattr(match.func, 'model_admin', None)
    if model_admin is not None:
        if (match.url_name or '').endswith('_add'):
            return model_admin.has_add_permission(request)
        return model_admin.has_view_or_change_permission(request)
    if any(name.startswith('wagtail') for name in match.namespaces):
        return panels.can_access_cms(user)
    return True
