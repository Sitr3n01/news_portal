from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import SiteExtension


@admin.register(SiteExtension)
class SiteExtensionAdmin(ModelAdmin):
    list_display = ['site', 'primary_email', 'newsletter_sender']
    search_fields = ['site__name', 'primary_email']
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
