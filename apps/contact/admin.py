from django.contrib import admin
from django.urls import reverse_lazy
from django.utils.text import format_lazy
from unfold.admin import ModelAdmin

from apps.common.admin_mixins import AdminUXMixin

from .models import ContactInquiry


@admin.register(ContactInquiry)
class ContactInquiryAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['name', 'email', 'subject', 'site', 'status', 'created_at']
    list_filter = ['status', 'site', 'created_at']
    list_filter_submit = True
    search_fields = ['name', 'email', 'phone', 'subject', 'message']
    readonly_fields = ['site', 'name', 'email', 'phone', 'subject', 'message', 'created_at', 'updated_at']
    radio_fields = {'status': admin.HORIZONTAL}
    ux_list_title = 'Mensagens de contato'
    ux_list_description = 'Use esta tela como uma fila de atendimento: responda mensagens novas, marque como lidas e arquive o que já foi tratado.'
    ux_list_icon = 'contact_mail'
    ux_list_actions = [
        {'label': 'Guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
    ]
    ux_list_filters = [
        {'label': 'Novas', 'icon': 'mark_email_unread', 'url': '?status__exact=new'},
        {'label': 'Lidas', 'icon': 'drafts', 'url': '?status__exact=read'},
        {'label': 'Respondidas', 'icon': 'reply', 'url': '?status__exact=replied'},
        {'label': 'Arquivadas', 'icon': 'archive', 'url': '?status__exact=archived'},
    ]
    ux_empty_message = 'Nenhuma mensagem encontrada. Quando visitantes enviarem contato, elas aparecerão aqui.'
    ux_form_title = 'Atendimento de mensagem'
    ux_form_description = 'Os dados recebidos ficam preservados. Use o status para registrar o andamento do atendimento.'
    ux_form_icon = 'support_agent'
    ux_form_steps = [
        'Leia a mensagem e identifique o assunto.',
        'Responda pelo canal adequado usando e-mail ou telefone informado.',
        'Atualize o status para manter a fila organizada.',
    ]
    ux_after_save_actions = [
        {'label': 'Guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Mensagens novas', 'icon': 'mark_email_unread', 'url': format_lazy('{}?status__exact=new', reverse_lazy('admin:contact_contactinquiry_changelist'))},
        {'label': 'Todas as mensagens', 'icon': 'inbox', 'url': reverse_lazy('admin:contact_contactinquiry_changelist')},
    ]
    fieldsets = [
        ('Dados de Contato', {
            'fields': ('site', 'name', 'email', 'phone', 'subject', 'message', 'created_at', 'updated_at'),
        }),
        ('Status', {
            'fields': ('status',),
        }),
    ]
    actions = ['mark_resolved']

    @admin.action(description='Arquivar mensagens selecionadas')
    def mark_resolved(self, request, queryset):
        # Update to archived instead of resolved since valid choices are:
        # new, read, replied, archived
        updated = queryset.update(status='archived')
        self.message_user(request, f'{updated} mensagem(ns) arquivada(s).')
