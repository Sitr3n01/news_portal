"""Usuários no /cms/: só superusuário cria, edita, exclui ou age em massa.

A gestão de contas do projeto é a do /admin/ (apps/accounts/admin.py), que
sincroniza cargo e grupos e trava os campos de privilégio. As telas que o
`wagtail.users` acrescenta ao /cms/ conferem só accounts.*_customuser — que o
Administrador Geral tem —, e o formulário delas oferece "Administrador"
(is_superuser) e grupos a quem edita OUTRA conta. Sem estes hooks, bastava
criar uma conta nova já como superusuário em /cms/users/new/.

Hooks oficiais do Wagtail 7.4; a listagem continua visível a quem tem
permissão de ver usuários (e já não aparece no menu, ver navigation.py).
"""

from django.contrib.auth import get_user_model
from wagtail import hooks
from wagtail.admin.auth import permission_denied


def _only_superuser(request):
    if not request.user.is_superuser:
        return permission_denied(request)
    return None


@hooks.register('before_create_user')
def restrict_create_user(request):
    return _only_superuser(request)


@hooks.register('before_edit_user')
def restrict_edit_user(request, user):
    return _only_superuser(request)


@hooks.register('before_delete_user')
def restrict_delete_user(request, user):
    return _only_superuser(request)


@hooks.register('before_bulk_action')
def restrict_user_bulk_actions(request, action_type, objects, action_class_instance):
    # Atribuir grupo, ativar/desativar e excluir contas em massa: mesma regra.
    if getattr(action_class_instance, 'model', None) is get_user_model():
        return _only_superuser(request)
    return None
