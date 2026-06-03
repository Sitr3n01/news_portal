from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

ROLE_TO_GROUP = {
    'school_admin': 'Administrador Escolar',
    'news_editor': 'Editor de Notícias',
    'hiring_manager': 'Contratações',
    'super_admin': 'Administrador Geral',
}

ALL_ACTIONS = ('view', 'add', 'change', 'delete')

ROLE_PERMISSION_SPECS = {
    'Administrador Escolar': [
        ('school', 'page', ALL_ACTIONS),
        ('school', 'schoolhomeconfig', ALL_ACTIONS),
        ('school', 'schoolfeature', ALL_ACTIONS),
        ('school', 'teammember', ALL_ACTIONS),
        ('school', 'testimonial', ALL_ACTIONS),
        ('hiring', 'department', ALL_ACTIONS),
        ('hiring', 'jobposting', ALL_ACTIONS),
        ('hiring', 'application', ('view', 'change')),
        ('contact', 'contactinquiry', ('view', 'change')),
        ('media_library', 'mediafile', ('view', 'add', 'change')),
        ('media_library', 'mediafolder', ('view', 'add', 'change')),
    ],
    'Editor de Notícias': [
        ('news', 'article', ALL_ACTIONS),
        ('news', 'category', ALL_ACTIONS),
        ('news', 'tag', ALL_ACTIONS),
        ('news', 'comment', ('view', 'change')),
        ('news', 'newslettersubscription', ('view', 'change')),
        ('news', 'newsletterdelivery', ('view', 'change')),
        ('news', 'articlelike', ('view',)),
        ('news', 'articlebookmark', ('view',)),
        ('media_library', 'mediafile', ('view', 'add', 'change')),
        ('media_library', 'mediafolder', ('view', 'add', 'change')),
    ],
    'Contratações': [
        ('hiring', 'department', ALL_ACTIONS),
        ('hiring', 'jobposting', ALL_ACTIONS),
        ('hiring', 'application', ('view', 'change')),
        ('contact', 'contactinquiry', ('view', 'change')),
        ('school', 'schoolhomeconfig', ('view',)),
    ],
}

GENERAL_ADMIN_APP_LABELS = [
    'accounts',
    'common',
    'contact',
    'hiring',
    'media_library',
    'news',
    'school',
    'sites',
]


def _permission_codenames(model_name, actions):
    return [f'{action}_{model_name}' for action in actions]


def _permissions_for_specs(specs):
    permissions = []
    for app_label, model_name, actions in specs:
        try:
            content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        except ContentType.DoesNotExist:
            continue
        permissions.extend(
            Permission.objects.filter(
                content_type=content_type,
                codename__in=_permission_codenames(model_name, actions),
            )
        )
    return permissions


def _general_admin_permissions():
    permissions = list(
        Permission.objects.filter(
            content_type__app_label__in=GENERAL_ADMIN_APP_LABELS,
        ).select_related('content_type')
    )
    permissions.extend(
        Permission.objects.filter(
            content_type__app_label='auth',
            content_type__model='group',
        ).select_related('content_type')
    )
    return permissions


def ensure_admin_role_groups():
    for group_name, specs in ROLE_PERMISSION_SPECS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.add(*_permissions_for_specs(specs))

    general_group, _ = Group.objects.get_or_create(name='Administrador Geral')
    general_group.permissions.add(*_general_admin_permissions())

    return Group.objects.filter(name__in=[*ROLE_PERMISSION_SPECS.keys(), 'Administrador Geral'])


def sync_user_role_group(user):
    """Sincroniza a associação de grupos do usuário com o seu cargo (role).

    O ``role`` é a fonte da verdade para o grupo de cargo: remove os grupos de
    OUTROS cargos — de modo que rebaixar o cargo revogue de fato o privilégio
    anterior, em vez de acumulá-lo — e adiciona o grupo do cargo atual. Grupos
    atribuídos manualmente (fora do mapa role->grupo) são preservados.
    """
    ensure_admin_role_groups()
    target_group_name = ROLE_TO_GROUP.get(getattr(user, 'role', None))
    stale_role_groups = user.groups.filter(
        name__in=set(ROLE_TO_GROUP.values()) - {target_group_name}
    )
    if stale_role_groups.exists():
        user.groups.remove(*stale_role_groups)
    if target_group_name:
        target_group = Group.objects.filter(name=target_group_name).first()
        if target_group:
            user.groups.add(target_group)
