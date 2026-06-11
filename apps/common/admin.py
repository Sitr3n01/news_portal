from django.contrib import admin
from django.contrib.sites.models import Site
from django.urls import reverse_lazy
from unfold.admin import ModelAdmin

from apps.common.admin_mixins import AdminUXMixin

from .models import SiteExtension

# O Sites Framework permanece ativo (contexto multi-site, domínio de e-mail), mas
# não tem mais página no admin: domínios raramente mudam e a tela só confundia
# usuários. Ajustes de domínio, quando necessários, são feitos via shell/migração.
try:
    admin.site.unregister(Site)
except admin.sites.NotRegistered:
    pass


@admin.register(SiteExtension)
class SiteExtensionAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['site', 'primary_email', 'newsletter_sender']
    list_filter_submit = True
    search_fields = ['site__name', 'primary_email']
    ux_list_title = 'Configurações dos sites'
    ux_list_description = 'Revise identidade, contato público e remetente da newsletter usados no front atual.'
    ux_list_icon = 'settings'
    ux_list_actions = [
        {'label': 'Guia de gerenciamento', 'icon': 'admin_panel_settings', 'url': reverse_lazy('admin_management_guide')},
    ]
    ux_empty_message = 'Nenhuma configuração de site encontrada. Cada site precisa de identidade e contatos públicos.'
    ux_form_title = 'Identidade e comunicação do site'
    ux_form_description = 'Mantenha os dados públicos claros. Detalhes técnicos de SMTP ficam fora desta tela e são vistos na saúde do sistema.'
    ux_form_icon = 'settings'
    ux_form_steps = [
        'Confirme qual site está sendo configurado.',
        'Defina o e-mail remetente da newsletter logo no topo.',
        'Revise marca, contatos e endereço público.',
    ]
    ux_after_save_actions = [
        {'label': 'Guia de gerenciamento', 'icon': 'admin_panel_settings', 'url': reverse_lazy('admin_management_guide')},
        {'label': 'Entregas de newsletter', 'icon': 'mark_email_read', 'url': reverse_lazy('admin:news_newsletterdelivery_changelist')},
    ]
    fieldsets = [
        ('Site', {
            'fields': ('site',),
            'description': 'Portal ao qual estas configurações se aplicam.',
        }),
        ('Newsletter — e-mail remetente', {
            'fields': ('newsletter_from_email', 'newsletter_from_name'),
            'description': (
                'E-mail e nome que aparecem como remetente das newsletters deste portal. '
                'É este o endereço que os leitores veem ao receber os artigos. '
                'O servidor SMTP (host, usuário e senha) continua no .env.prod e a '
                'dashboard mostra se está pronto para envio.'
            ),
        }),
        ('Identidade Visual', {
            'fields': ('tagline', 'logo', 'favicon'),
        }),
        ('Contato', {
            'fields': ('primary_email', 'phone_number', 'address'),
        }),
        ('Analytics e Redes Sociais', {
            'fields': ('google_analytics_id', 'facebook_url', 'instagram_url', 'tiktok_url', 'youtube_url'),
            'classes': ('collapse',),
        }),
        ('Seção de redes na home — textos', {
            'fields': (
                'social_section_title', 'social_section_title_en',
                'social_section_subtitle', 'social_section_subtitle_en',
            ),
            'description': (
                'Título e subtítulo da seção de redes na home. Para LIGAR/DESLIGAR a seção '
                'e cada rede (Instagram/TikTok), use os toggles no topo de "Posts de Redes Sociais".'
            ),
        }),
    ]

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            return super().get_fieldsets(request, obj)
        return [
            ('Site', {
                'fields': ('site',),
                'description': 'Portal ao qual estas configurações se aplicam.',
            }),
            ('Newsletter — e-mail remetente', {
                'fields': ('newsletter_from_email', 'newsletter_from_name'),
                'description': (
                    'E-mail e nome que aparecem como remetente das newsletters deste portal. '
                    'É este o endereço que os leitores veem. '
                    'O servidor SMTP continua no .env.prod.'
                ),
            }),
            ('Identidade Visual', {
                'fields': ('tagline', 'logo', 'favicon'),
            }),
            ('Contato', {
                'fields': ('primary_email', 'phone_number', 'address'),
            }),
            ('Seção de redes na home — textos', {
                'fields': (
                    'social_section_title', 'social_section_title_en',
                    'social_section_subtitle', 'social_section_subtitle_en',
                ),
                'description': (
                    'Título e subtítulo da seção de redes na home. Para LIGAR/DESLIGAR a seção '
                    'e cada rede, use os toggles no topo de "Posts de Redes Sociais".'
                ),
            }),
        ]

    def get_readonly_fields(self, request, obj=None):
        """O site é fixo depois de criado: a configuração é 1-para-1 com o portal,
        então editamos a linha existente em vez de reatribuir o site."""
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None and 'site' not in readonly:
            readonly.append('site')
        return readonly

    @admin.display(description='Remetente Newsletter')
    def newsletter_sender(self, obj):
        if obj.newsletter_from_email:
            return obj.newsletter_from_email
        return 'Usa DEFAULT_FROM_EMAIL'
