from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.urls import reverse_lazy
from unfold.admin import ModelAdmin

from apps.accounts.admin_roles import sync_user_role_group
from apps.common.admin_mixins import AdminUXMixin

from .models import CustomUser

try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


@admin.register(Group)
class AdminRoleGroupAdmin(AdminUXMixin, ModelAdmin, DjangoGroupAdmin):
    ux_list_title = 'Grupos e permissões'
    ux_list_description = 'Grupos representam responsabilidades administrativas. Use os perfis prontos antes de montar permissões manuais.'
    ux_list_icon = 'badge'
    ux_list_actions = [
        {'label': 'Guia de gerenciamento', 'icon': 'admin_panel_settings', 'url': reverse_lazy('admin_management_guide')},
        {'label': 'Novo grupo', 'icon': 'add', 'url': reverse_lazy('admin:auth_group_add'), 'kind': 'primary'},
    ]
    ux_empty_message = 'Nenhum grupo encontrado. Rode as migrações ou crie os perfis administrativos iniciais.'
    ux_form_title = 'Grupo de permissões'
    ux_form_description = 'Altere permissões somente quando um perfil pronto não atender à rotina da equipe.'
    ux_form_icon = 'badge'
    ux_form_steps = [
        'Use um nome que represente responsabilidade, não pessoa.',
        'Revise permissões por área antes de salvar.',
        'Depois atribua o grupo aos usuários correspondentes.',
    ]
    ux_after_save_actions = [
        {'label': 'Guia de gerenciamento', 'icon': 'admin_panel_settings', 'url': reverse_lazy('admin_management_guide')},
        {'label': 'Usuários', 'icon': 'manage_accounts', 'url': reverse_lazy('admin:accounts_customuser_changelist')},
    ]


@admin.register(CustomUser)
class CustomUserAdmin(AdminUXMixin, ModelAdmin, UserAdmin):
    list_display = ['username', 'email', 'get_role_display', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['role', 'is_active', 'is_staff', 'date_joined']
    list_filter_submit = True
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    radio_fields = {'role': admin.HORIZONTAL}
    ux_list_title = 'Usuários administrativos'
    ux_list_description = 'Crie contas nominativas e use grupos de permissões por responsabilidade. Evite superusuários para rotinas diárias.'
    ux_list_icon = 'manage_accounts'
    ux_list_actions = [
        {'label': 'Guia de gerenciamento', 'icon': 'admin_panel_settings', 'url': reverse_lazy('admin_management_guide')},
        {'label': 'Novo usuário', 'icon': 'person_add', 'url': reverse_lazy('admin:accounts_customuser_add'), 'kind': 'primary'},
    ]
    ux_list_filters = [
        {'label': 'Ativos', 'icon': 'check_circle', 'url': '?is_active__exact=1'},
        {'label': 'Equipe admin', 'icon': 'admin_panel_settings', 'url': '?is_staff__exact=1'},
        {'label': 'Inativos', 'icon': 'block', 'url': '?is_active__exact=0'},
    ]
    ux_empty_message = 'Nenhum usuário encontrado para os filtros atuais.'
    ux_form_title = 'Usuário e permissões'
    ux_form_description = 'Configure acesso com cuidado: primeiro perfil e grupos, depois permissões individuais apenas quando necessário.'
    ux_form_icon = 'manage_accounts'
    ux_form_steps = [
        'Preencha identificação e e-mail real do usuário.',
        'Marque acesso administrativo somente quando a pessoa precisar entrar no admin.',
        'Atribua grupos por função antes de permissões individuais.',
    ]
    ux_after_save_description = 'Revise grupos e teste o acesso com uma conta sem superusuário quando criar perfis operacionais.'
    ux_after_save_actions = [
        {'label': 'Guia de gerenciamento', 'icon': 'admin_panel_settings', 'url': reverse_lazy('admin_management_guide')},
        {'label': 'Grupos de permissões', 'icon': 'badge', 'url': reverse_lazy('admin:auth_group_changelist')},
        {'label': 'Todos os usuários', 'icon': 'manage_accounts', 'url': reverse_lazy('admin:accounts_customuser_changelist')},
    ]
    fieldsets = (
        (None, {'fields': ('username', 'password'), 'classes': ('tab',)}),
        ('Informações Pessoais', {'fields': ('first_name', 'last_name', 'email'), 'classes': ('tab',)}),
        ('Permissões', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('tab',),
        }),
        ('Perfil', {'fields': ('role', 'avatar', 'bio'), 'classes': ('tab',)}),
        ('Datas Importantes', {'fields': ('last_login', 'date_joined'), 'classes': ('collapse',)}),
    )
    add_fieldsets = (
        ('Credenciais', {
            'classes': ('wide',),
            'fields': ('username', 'usable_password', 'password1', 'password2'),
            'description': 'Defina o nome de usuário e a senha de acesso.',
        }),
        ('Perfil', {
            'fields': ('role',),
            'description': 'O cargo define o grupo de permissões atribuído automaticamente ao salvar '
                          '(ex.: "Editor de Notícias"). Ajuste depois em Permissões se precisar de algo específico.',
        }),
    )

    class Media:
        css = {
            'all': [],
        }

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['kb_password_fix'] = True
        return super().changeform_view(request, object_id, form_url, extra_context)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # role é fonte da verdade do grupo de cargo: sincroniza (adiciona o atual
        # e revoga grupos de cargos anteriores, evitando privilégio residual).
        sync_user_role_group(form.instance)
