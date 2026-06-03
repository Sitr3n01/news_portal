from django.contrib import admin
from django.contrib.sites.admin import SiteAdmin as DjangoSiteAdmin
from django.contrib.sites.models import Site
from django.urls import reverse_lazy
from unfold.admin import ModelAdmin

from apps.common.admin_mixins import AdminUXMixin

from .models import SiteExtension

try:
    admin.site.unregister(Site)
except admin.sites.NotRegistered:
    pass


@admin.register(Site)
class SiteDomainAdmin(AdminUXMixin, ModelAdmin, DjangoSiteAdmin):
    ux_list_title = 'Domínios e sites'
    ux_list_description = 'Cada site define o contexto de conteúdo dos portais. Altere domínios com cuidado para não misturar dados.'
    ux_list_icon = 'language'
    ux_list_actions = [
        {'label': 'Guia de gerenciamento', 'icon': 'admin_panel_settings', 'url': reverse_lazy('admin_management_guide')},
    ]
    ux_empty_message = 'Nenhum site cadastrado. O projeto precisa de pelo menos um registro no Sites Framework.'
    ux_form_title = 'Site e domínio'
    ux_form_description = 'Use nome amigável para identificação interna e domínio conforme ambiente atual.'
    ux_form_icon = 'language'
    ux_form_steps = [
        'Confirme o domínio usado pelo ambiente.',
        'Use nome interno que ajude a equipe a reconhecer o portal.',
        'Depois revise as configurações públicas do site correspondente.',
    ]
    ux_after_save_actions = [
        {'label': 'Guia de gerenciamento', 'icon': 'admin_panel_settings', 'url': reverse_lazy('admin_management_guide')},
        {'label': 'Configurações do site', 'icon': 'settings', 'url': reverse_lazy('admin:common_siteextension_changelist')},
    ]


@admin.register(SiteExtension)
class SiteExtensionAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['site', 'primary_email', 'newsletter_sender']
    list_filter_submit = True
    search_fields = ['site__name', 'primary_email']
    ux_list_title = 'Configurações dos sites'
    ux_list_description = 'Revise identidade, contato público e remetente de newsletter de cada portal.'
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
        'Revise marca, contatos e endereço público.',
        'Defina remetente de newsletter amigável para leitores.',
    ]
    ux_after_save_actions = [
        {'label': 'Guia de gerenciamento', 'icon': 'admin_panel_settings', 'url': reverse_lazy('admin_management_guide')},
        {'label': 'Entregas de newsletter', 'icon': 'mark_email_read', 'url': reverse_lazy('admin:news_newsletterdelivery_changelist')},
    ]
    fieldsets = [
        ('Site', {
            'fields': ('site',),
        }),
        ('Identidade Visual', {
            'fields': ('tagline', 'logo', 'favicon'),
        }),
        ('Contato', {
            'fields': ('primary_email', 'phone_number', 'address'),
        }),
        ('Newsletter', {
            'fields': ('newsletter_from_email', 'newsletter_from_name'),
            'description': (
                'Configure o remetente visível para o cliente. '
                'Servidor SMTP, usuário e senha continuam no .env.prod e a dashboard '
                'mostra se essas variáveis estão prontas para envio.'
            ),
        }),
        ('Analytics e Redes Sociais', {
            'fields': ('google_analytics_id', 'facebook_url', 'instagram_url', 'youtube_url'),
            'classes': ('collapse',),
        }),
    ]

    @admin.display(description='Remetente Newsletter')
    def newsletter_sender(self, obj):
        if obj.newsletter_from_email:
            return obj.newsletter_from_email
        return 'Usa DEFAULT_FROM_EMAIL'
