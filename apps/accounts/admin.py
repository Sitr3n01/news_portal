from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.urls import reverse_lazy
from unfold.admin import ModelAdmin

from apps.accounts.admin_roles import sync_user_role_group
from apps.common.admin_mixins import AdminUXMixin, SuperuserOnlyAdminMixin

from .models import CustomUser, GoogleIdentity, VerificationCode

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
    list_filter = ['role', 'is_active', 'is_staff', 'email_verified', 'date_joined']
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
        ('Informações Pessoais', {
            'fields': ('first_name', 'last_name', 'email', 'email_verified', 'email_verified_at'),
            'classes': ('tab',),
        }),
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
                          '(ex.: "Editor de Notícias"). Use "Leitor" para quem só acessa o portal público. '
                          'Para liberar a Administração do sistema, marque também "Acesso administrativo" '
                          'na aba Permissões. Ajuste depois em Permissões se precisar de algo específico.',
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


# Todos os campos de VerificationCode MENOS code_hash. Calculado a partir do
# _meta (e não escrito à mão) para que, se o modelo ganhar um campo novo no
# futuro, ele apareça aqui automaticamente — só code_hash precisa continuar
# excluído explicitamente, em vez de alguém ter de lembrar de atualizar uma
# lista solta toda vez que o modelo mudar.
_VERIFICATION_CODE_SAFE_FIELDS = [field.name for field in VerificationCode._meta.fields if field.name != 'code_hash']


@admin.register(VerificationCode)
class VerificationCodeAdmin(SuperuserOnlyAdminMixin, ModelAdmin):
    """Somente leitura: existe para o superusuário AUDITAR emissões suspeitas
    (ex.: muitas emissões seguidas para a mesma conta), nunca para operar
    sobre elas.

    SuperuserOnlyAdminMixin (apps.common.admin_mixins) restringe módulo e
    visualização a superusuário — nenhum grupo de cargo (admin_roles.py) tem,
    ou deveria ter, motivo para ver códigos de verificação de outras contas;
    isto não é uma tela operacional do dia a dia, é uma trilha de auditoria.
    has_add/has_change abaixo ficam False incondicionalmente, inclusive para
    superusuário — o mixin sozinho já os amarra a is_superuser, mas aqui o
    ponto não é QUEM pode mudar a linha, é que NINGUÉM deve: criar ou editar
    à mão forjaria uma emissão que nunca aconteceu, ou apagaria o rastro de
    tentativas de uma tentativa de invasão real, o oposto do que uma trilha
    de auditoria existe para garantir. Delete continua liberado a
    superusuário (herdado do mixin) para expurgo pontual (LGPD); a faxina de
    rotina é o management command clear_expired_verification_codes.

    `code_hash` NUNCA aparece — nem aqui embaixo, nem em nenhum outro campo
    desta classe. Mesmo sendo hash (não o código em texto puro), listar um
    hash de segredo num changelist normaliza a ideia de que hash é "seguro o
    bastante para mostrar", e é assim que um code review futuro deixa passar
    um vazamento pior.
    """

    list_display = ['user', 'purpose', 'email', 'attempts', 'is_used', 'is_expired', 'created_at']
    list_filter = ['purpose']
    search_fields = ['user__username', 'user__email', 'email']
    fields = _VERIFICATION_CODE_SAFE_FIELDS
    readonly_fields = _VERIFICATION_CODE_SAFE_FIELDS

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(GoogleIdentity)
class GoogleIdentityAdmin(SuperuserOnlyAdminMixin, ModelAdmin):
    """Somente leitura, mesmo raciocínio de VerificationCodeAdmin: existe para
    o superusuário auditar vínculos (ex.: confirmar qual conta local está
    ligada a qual `google_sub` num chamado de suporte), nunca para criar ou
    editar um vínculo à mão — isso pertence ao login social (Fase 2), que
    grava a linha no momento da primeira autenticação bem-sucedida via
    Google, não a um formulário de admin.

    `google_sub` não é segredo (é um identificador, não uma credencial —
    equivalente a mostrar o e-mail de alguém, não a senha), por isso pode
    aparecer em list_display/search_fields sem o mesmo cuidado de
    VerificationCode.code_hash.
    """

    list_display = ['user', 'email', 'google_sub', 'created_at', 'last_login_at']
    search_fields = ['user__username', 'user__email', 'email', 'google_sub']
    readonly_fields = [field.name for field in GoogleIdentity._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
