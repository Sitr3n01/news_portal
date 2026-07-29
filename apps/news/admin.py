from django.contrib import admin, messages
from django.urls import reverse_lazy
from django.utils.text import format_lazy
from unfold.admin import ModelAdmin

from apps.common.admin_mixins import AdminUXMixin, SuperuserOnlyAdminMixin

from .models import ArticleBookmark, ArticleLike, Comment, NewsletterDelivery, NewsletterSubscription


def _csv_safe(value):
    """Previne CSV/formula injection: prefixa com aspa simples valores que
    aplicativos de planilha interpretariam como fórmula."""
    text = '' if value is None else str(value)
    if text and text[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + text
    return text


@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['email', 'site', 'is_active', 'created_at']
    list_filter = ['is_active', 'site', 'created_at']
    list_filter_submit = True
    search_fields = ['email']
    readonly_fields = ['email', 'site', 'created_at']
    list_per_page = 25
    ux_list_title = 'Assinantes da newsletter'
    ux_list_description = 'Acompanhe inscrições por site. Exportação de e-mails é restrita a superusuários.'
    ux_list_icon = 'mail'
    ux_list_actions = [
    ]
    ux_list_filters = [
        {'label': 'Ativos', 'icon': 'mark_email_read', 'url': '?is_active__exact=1'},
        {'label': 'Inativos', 'icon': 'unsubscribe', 'url': '?is_active__exact=0'},
    ]
    ux_empty_message = 'Nenhum assinante encontrado para os filtros atuais.'
    ux_form_title = 'Assinante'
    ux_form_description = 'Dados de inscrição são preservados. Use apenas o status ativo/inativo para atendimento ou limpeza.'
    ux_form_icon = 'mail'
    ux_form_steps = [
        'Confira o e-mail e o site da inscrição.',
        'Desative apenas quando houver solicitação ou sinal claro de spam.',
        'Não edite manualmente dados de origem da inscrição.',
    ]
    ux_after_save_actions = [
        {'label': 'Assinantes ativos', 'icon': 'mark_email_read', 'url': format_lazy('{}?is_active__exact=1', reverse_lazy('admin:news_newslettersubscription_changelist'))},
        {'label': 'Entregas', 'icon': 'mark_email_read', 'url': reverse_lazy('admin:news_newsletterdelivery_changelist')},
    ]
    actions = ['deactivate_subscriptions', 'activate_subscriptions', 'export_emails']

    fieldsets = [
        (None, {
            'fields': ('email', 'site', 'is_active', 'created_at'),
        }),
    ]

    def has_add_permission(self, request):
        return False

    @admin.action(description='Desativar inscrições selecionadas (spam/bots)')
    def deactivate_subscriptions(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} inscrição(ões) desativada(s).')

    @admin.action(description='Reativar inscrições selecionadas')
    def activate_subscriptions(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} inscrição(ões) reativada(s).')

    @admin.action(description='Exportar emails como CSV')
    def export_emails(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(
                request,
                'Apenas superusuários podem exportar emails.',
                messages.ERROR,
            )
            return

        import csv

        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="assinantes.csv"'
        writer = csv.writer(response)
        writer.writerow(['E-mail', 'Site', 'Data de Inscrição', 'Ativo'])
        for sub in queryset:
            writer.writerow([_csv_safe(sub.email), _csv_safe(sub.site.name), sub.created_at, 'Sim' if sub.is_active else 'Não'])
        return response


@admin.register(NewsletterDelivery)
class NewsletterDeliveryAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['article', 'email', 'status', 'attempts', 'sent_at', 'updated_at']
    list_filter = ['status', 'article__site', 'sent_at', 'created_at']
    list_filter_submit = True
    search_fields = ['email', 'article__title', 'last_error']
    readonly_fields = ['article', 'subscription', 'email', 'status', 'attempts', 'last_error', 'sent_at', 'created_at', 'updated_at']
    list_per_page = 50
    ux_list_title = 'Entregas de newsletter'
    ux_list_description = 'Monitore envios processados, pendentes e com falha para agir antes que a comunicação se perca.'
    ux_list_icon = 'mark_email_read'
    ux_list_actions = [
    ]
    ux_list_filters = [
        {'label': 'Falhas', 'icon': 'error', 'url': '?status__exact=failed'},
        {'label': 'Pendentes', 'icon': 'outbox', 'url': '?status__exact=pending'},
        {'label': 'Enviadas', 'icon': 'check_circle', 'url': '?status__exact=sent'},
    ]
    ux_empty_message = 'Nenhuma entrega encontrada. As entregas aparecem após envio de newsletter.'
    ux_form_title = 'Entrega de newsletter'
    ux_form_description = 'Esta tela é de auditoria. Use as informações para entender falhas e reprocessar pelo fluxo adequado.'
    ux_form_icon = 'mark_email_read'
    ux_form_steps = [
        'Confira artigo, destinatário e tentativas.',
        'Leia o erro apenas quando houver falha.',
        'Ajustes de envio devem ser feitos nas configurações do site ou no fluxo de newsletter.',
    ]
    ux_after_save_actions = [
        {'label': 'Falhas', 'icon': 'error', 'url': format_lazy('{}?status__exact=failed', reverse_lazy('admin:news_newsletterdelivery_changelist'))},
        {'label': 'Configurações dos sites', 'icon': 'settings', 'url': reverse_lazy('wagtailsnippets_common_siteextension:list')},
    ]

    fieldsets = [
        ('Entrega', {
            'fields': ('article', 'subscription', 'email', 'status', 'attempts', 'sent_at'),
        }),
        ('Erro', {
            'fields': ('last_error',),
            'classes': ('collapse',),
        }),
        ('Auditoria', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    ]

    def has_add_permission(self, request):
        return False


@admin.register(Comment)
class CommentAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['user', 'article', 'short_content', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    list_filter_submit = True
    search_fields = ['content', 'user__username', 'article__title']
    readonly_fields = ['user', 'article', 'content', 'created_at']
    list_per_page = 25
    ux_list_title = 'Moderação de comentários'
    ux_list_description = 'Revise comentários ocultos ou pendentes e mantenha visível apenas o que pode permanecer no portal.'
    ux_list_icon = 'forum'
    ux_list_actions = [
    ]
    ux_list_filters = [
        {'label': 'Ocultos ou pendentes', 'icon': 'visibility_off', 'url': '?is_active__exact=0'},
        {'label': 'Visíveis', 'icon': 'visibility', 'url': '?is_active__exact=1'},
    ]
    ux_empty_message = 'Nenhum comentário encontrado para os filtros atuais.'
    ux_form_title = 'Comentário'
    ux_form_description = 'O conteúdo do comentário não é editado no admin. Use a visibilidade para aprovar ou ocultar.'
    ux_form_icon = 'forum'
    ux_form_steps = [
        'Leia o comentário no contexto do artigo.',
        'Mantenha visível quando estiver adequado à conversa.',
        'Oculte quando precisar remover do portal sem perder registro.',
    ]
    ux_after_save_actions = [
        {'label': 'Pendentes', 'icon': 'visibility_off', 'url': format_lazy('{}?is_active__exact=0', reverse_lazy('admin:news_comment_changelist'))},
        {'label': 'Todos os comentários', 'icon': 'forum', 'url': reverse_lazy('admin:news_comment_changelist')},
    ]
    actions = ['approve_comments', 'hide_comments']

    fieldsets = [
        ('Comentário', {
            'fields': ('user', 'article', 'content', 'created_at'),
            'description': 'Detalhes do comentário. Estes campos não podem ser editados.',
        }),
        ('Moderação', {
            'fields': ('is_active',),
            'description': 'Desmarque "Visível" para ocultar este comentário do portal.',
        }),
    ]

    def has_add_permission(self, request):
        return False

    @admin.display(description='Trecho')
    def short_content(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content

    @admin.action(description='Aprovar comentários selecionados')
    def approve_comments(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} comentário(s) aprovado(s).')

    @admin.action(description='Ocultar comentários selecionados')
    def hide_comments(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} comentário(s) ocultado(s).')


@admin.register(ArticleLike)
class ArticleLikeAdmin(SuperuserOnlyAdminMixin, ModelAdmin):
    list_display = ['article', 'user', 'ip_address', 'created_at']
    list_filter = ['created_at']
    search_fields = ['article__title', 'user__username', 'ip_address']
    readonly_fields = ['article', 'user', 'ip_address', 'session_key', 'created_at']


@admin.register(ArticleBookmark)
class ArticleBookmarkAdmin(SuperuserOnlyAdminMixin, ModelAdmin):
    list_display = ['user', 'article', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'article__title']
    readonly_fields = ['user', 'article', 'created_at']
