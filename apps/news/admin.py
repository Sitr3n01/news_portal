from django.contrib import admin, messages
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import Article, ArticleBookmark, ArticleLike, Category, Comment, NewsletterDelivery, NewsletterSubscription, Tag


def _csv_safe(value):
    """Previne CSV/formula injection: prefixa com aspa simples valores que
    aplicativos de planilha interpretariam como fórmula."""
    text = '' if value is None else str(value)
    if text and text[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + text
    return text


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ['name', 'parent', 'order']
    list_filter = ['parent']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']
    fieldsets = [
        (None, {'fields': ('name', 'slug', 'parent', 'order')}),
        ('Descrição', {'fields': ('description',)}),
    ]


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Article)
class ArticleAdmin(ModelAdmin):
    list_display = [
        'title', 'category', 'author', 'site',
        'status', 'published_at', 'is_featured', 'view_count', 'newsletter_sent_at', 'newsletter_preview_link',
    ]
    list_filter = ['status', 'site', 'is_featured', 'category', 'published_at']
    search_fields = ['title', 'excerpt', 'content']
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ['author', 'tags']
    date_hierarchy = 'published_at'
    readonly_fields = ['view_count', 'newsletter_sent_at', 'created_at', 'updated_at']
    fieldsets = [
        ('Conteúdo', {
            'fields': ('title', 'slug', 'excerpt', 'content'),
            'description': 'Preencha o título e o conteúdo do artigo. O campo URL amigável é gerado automaticamente.',
        }),
        ('Mídia', {
            'fields': ('featured_image', 'featured_image_caption'),
            'description': 'Adicione uma imagem de capa para o artigo. Formatos aceitos: JPG, PNG, WebP.',
        }),
        ('Classificação', {
            'fields': ('category', 'tags'),
            'description': 'Organize o artigo por categoria e tags. Digite no campo de tags para buscar.',
        }),
        ('Publicação', {
            'fields': ('site', 'author', 'status', 'published_at', 'is_featured'),
            'description': 'Controle onde e quando o artigo será publicado.',
        }),
        ('SEO (Otimização para Buscadores)', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',),
            'description': 'Opcional. Melhore o posicionamento do artigo no Google.',
        }),
        ('Estatísticas', {
            'fields': ('view_count', 'newsletter_sent_at', 'created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'newsletter_sent_at: preenchido automaticamente ao enviar a newsletter. Vazio = não enviada ainda.',
        }),
    ]
    actions = ['publish_articles', 'archive_articles', 'send_newsletter']

    @admin.display(description='Preview')
    def newsletter_preview_link(self, obj):
        url = reverse('news:newsletter_preview', args=[obj.pk])
        return format_html(
            '<a href="{}" target="_blank" title="Preview da Newsletter" '
            'style="font-size: 14px; text-decoration: underline; color: #1152d4;">Visualizar</a>',
            url,
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if field and hasattr(field, 'widget'):
            field.widget.can_add_related = False
            field.widget.can_change_related = False
            field.widget.can_delete_related = False
        return field

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        field = super().formfield_for_manytomany(db_field, request, **kwargs)
        if field and hasattr(field, 'widget'):
            field.widget.can_add_related = False
            field.widget.can_change_related = False
            field.widget.can_delete_related = False
        return field

    @admin.action(description='Publicar artigos selecionados')
    def publish_articles(self, request, queryset):
        updated = queryset.filter(status=Article.Status.DRAFT).update(
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        self.message_user(request, f'{updated} artigo(s) publicado(s).')

    @admin.action(description='Arquivar artigos selecionados')
    def archive_articles(self, request, queryset):
        updated = queryset.update(status=Article.Status.ARCHIVED)
        self.message_user(request, f'{updated} artigo(s) arquivado(s).')

    @admin.action(description='Enviar Newsletter para inscritos')
    def send_newsletter(self, request, queryset):
        from .newsletter import process_article_newsletter

        published = queryset.filter(status=Article.Status.PUBLISHED)

        if not published.exists():
            self.message_user(
                request,
                'Nenhum artigo publicado selecionado. Apenas artigos publicados podem ser enviados por newsletter.',
                messages.WARNING,
            )
            return

        total_sent = 0
        total_failed = 0
        total_skipped = 0
        articles_sent = 0

        for article in published:
            result = process_article_newsletter(
                article,
                retry_failed=True,
                include_marked_sent=True,
            )
            total_sent += result['sent']
            total_failed += result['failed']
            total_skipped += result['skipped']
            if result['sent'] > 0:
                articles_sent += 1

        if total_failed or total_skipped:
            self.message_user(
                request,
                f'Entregas com atenção: {total_failed} falha(s), {total_skipped} ignorada(s).',
                messages.WARNING,
            )

        if total_sent > 0:
            self.message_user(
                request,
                f'✅ Newsletter enviada! {articles_sent} artigo(s) para {total_sent} inscrito(s).',
                messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                'Nenhum inscrito ativo encontrado para enviar a newsletter.',
                messages.INFO,
            )


@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(ModelAdmin):
    list_display = ['email', 'site', 'is_active', 'created_at']
    list_filter = ['is_active', 'site', 'created_at']
    search_fields = ['email']
    readonly_fields = ['email', 'site', 'created_at']
    list_per_page = 25
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
class NewsletterDeliveryAdmin(ModelAdmin):
    list_display = ['article', 'email', 'status', 'attempts', 'sent_at', 'updated_at']
    list_filter = ['status', 'article__site', 'sent_at', 'created_at']
    search_fields = ['email', 'article__title', 'last_error']
    readonly_fields = ['article', 'subscription', 'email', 'status', 'attempts', 'last_error', 'sent_at', 'created_at', 'updated_at']
    list_per_page = 50

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
class CommentAdmin(ModelAdmin):
    list_display = ['user', 'article', 'short_content', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['content', 'user__username', 'article__title']
    readonly_fields = ['user', 'article', 'content', 'created_at']
    list_per_page = 25
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
class ArticleLikeAdmin(ModelAdmin):
    list_display = ['article', 'user', 'ip_address', 'created_at']
    list_filter = ['created_at']
    search_fields = ['article__title', 'user__username', 'ip_address']
    readonly_fields = ['article', 'user', 'ip_address', 'session_key', 'created_at']


@admin.register(ArticleBookmark)
class ArticleBookmarkAdmin(ModelAdmin):
    list_display = ['user', 'article', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'article__title']
    readonly_fields = ['user', 'article', 'created_at']
