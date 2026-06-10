from django.contrib import admin, messages
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.html import format_html
from django.utils.text import format_lazy
from unfold.admin import ModelAdmin, StackedInline

from apps.common.admin_mixins import AdminUXMixin, SuperuserOnlyAdminMixin

from .models import Article, ArticleBlock, ArticleBookmark, ArticleLike, Category, Comment, NewsletterDelivery, NewsletterSubscription, Tag


def _csv_safe(value):
    """Previne CSV/formula injection: prefixa com aspa simples valores que
    aplicativos de planilha interpretariam como fórmula."""
    text = '' if value is None else str(value)
    if text and text[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + text
    return text


class NewsletterStatusFilter(admin.SimpleListFilter):
    """Filtro descobrível de status de newsletter no changelist de Artigos.

    Substitui o parâmetro de URL solto ``newsletter_sent_at__isnull`` (que
    funcionava, mas não aparecia na barra de filtros) por uma opção visível,
    usada também pelos atalhos do dashboard e do guia editorial.
    """
    title = 'newsletter'
    parameter_name = 'newsletter'

    def lookups(self, request, model_admin):
        return [
            ('pending', 'Aguardando envio'),
            ('sent', 'Já enviada'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'pending':
            return queryset.filter(status=Article.Status.PUBLISHED, newsletter_sent_at__isnull=True)
        if self.value() == 'sent':
            return queryset.filter(newsletter_sent_at__isnull=False)
        return queryset


@admin.register(Category)
class CategoryAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['name', 'parent', 'order']
    list_filter = ['parent']
    list_filter_submit = True
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']
    ux_list_title = 'Categorias editoriais'
    ux_list_description = 'Categorias estruturam o portal e ajudam leitores a navegar por temas principais.'
    ux_list_icon = 'category'
    ux_list_actions = [
        {'label': 'Guia editorial', 'icon': 'newspaper', 'url': reverse_lazy('admin_news_guide')},
        {'label': 'Nova categoria', 'icon': 'add', 'url': reverse_lazy('admin:news_category_add'), 'kind': 'primary'},
    ]
    ux_empty_message = 'Nenhuma categoria criada. Cadastre pelo menos uma antes de publicar artigos.'
    ux_form_title = 'Categoria'
    ux_form_description = 'Use nomes curtos e estáveis. Categorias demais deixam a navegação confusa.'
    ux_form_icon = 'category'
    ux_form_steps = [
        'Defina nome e slug.',
        'Use categoria-mãe apenas quando houver hierarquia real.',
        'Ajuste a ordem para controlar a navegação.',
    ]
    ux_after_save_actions = [
        {'label': 'Guia editorial', 'icon': 'newspaper', 'url': reverse_lazy('admin_news_guide')},
        {'label': 'Criar artigo', 'icon': 'edit_square', 'url': reverse_lazy('admin:news_article_add')},
    ]
    fieldsets = [
        (None, {'fields': ('name', 'slug', 'parent', 'order')}),
        ('Descrição', {'fields': ('description',)}),
    ]


@admin.register(Tag)
class TagAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    ux_list_title = 'Tags de notícias'
    ux_list_description = 'Tags conectam artigos relacionados. Use termos específicos e evite duplicatas parecidas.'
    ux_list_icon = 'label'
    ux_list_actions = [
        {'label': 'Guia editorial', 'icon': 'newspaper', 'url': reverse_lazy('admin_news_guide')},
        {'label': 'Nova tag', 'icon': 'add', 'url': reverse_lazy('admin:news_tag_add'), 'kind': 'primary'},
    ]
    ux_empty_message = 'Nenhuma tag criada. Adicione tags quando elas ajudarem a conectar matérias.'
    ux_form_title = 'Tag'
    ux_form_description = 'Crie tags reutilizáveis para temas, pessoas, eventos ou séries editoriais.'
    ux_form_icon = 'label'
    ux_form_steps = [
        'Use nomes curtos.',
        'Revise se já existe uma tag equivalente.',
        'Confirme o slug antes de salvar.',
    ]
    ux_after_save_actions = [
        {'label': 'Guia editorial', 'icon': 'newspaper', 'url': reverse_lazy('admin_news_guide')},
        {'label': 'Todas as tags', 'icon': 'label', 'url': reverse_lazy('admin:news_tag_changelist')},
    ]


class ArticleBlockInline(StackedInline):
    """Blocos que formam o corpo do artigo (texto, imagem, vídeo/post).

    O JS article_blocks.js mostra só os campos do tipo escolhido, deixando a
    edição amigável (sem HTML cru e sem campos irrelevantes na tela).
    """
    model = ArticleBlock
    extra = 0
    autocomplete_fields = ['media']
    ordering = ['order']
    fieldsets = [
        (None, {
            'fields': ('block_type', 'order'),
            'description': 'Escolha o tipo do bloco. Só os campos desse tipo aparecem abaixo.',
        }),
        ('Texto', {'fields': ('rich_text',), 'classes': ('block-fields', 'block-fields-rich_text')}),
        ('Imagem', {'fields': ('media',), 'classes': ('block-fields', 'block-fields-image')}),
        ('Vídeo / Post', {'fields': ('embed_url',), 'classes': ('block-fields', 'block-fields-embed')}),
        ('Legenda', {'fields': ('caption',), 'classes': ('block-fields', 'block-fields-caption')}),
    ]

    class Media:
        js = ('admin/js/article_blocks.js',)


@admin.register(Article)
class ArticleAdmin(AdminUXMixin, ModelAdmin):
    inlines = [ArticleBlockInline]
    list_display = [
        'title', 'category', 'status', 'published_at',
        'is_featured', 'view_count', 'newsletter_status', 'newsletter_preview_link',
    ]
    list_filter = ['status', NewsletterStatusFilter, 'site', 'is_featured', 'category', 'published_at']
    list_filter_submit = True
    search_fields = ['title', 'excerpt', 'content']
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ['author', 'tags']
    date_hierarchy = 'published_at'
    readonly_fields = ['view_count', 'newsletter_sent_at', 'created_at', 'updated_at']
    radio_fields = {'status': admin.HORIZONTAL}
    ux_list_title = 'Artigos'
    ux_list_description = 'Gerencie o ciclo editorial completo: rascunho, revisão, publicação, destaque e envio de newsletter.'
    ux_list_icon = 'newspaper'
    ux_list_actions = [
        {'label': 'Guia editorial', 'icon': 'newspaper', 'url': reverse_lazy('admin_news_guide')},
        {'label': 'Novo artigo', 'icon': 'edit_square', 'url': reverse_lazy('admin:news_article_add'), 'kind': 'primary'},
    ]
    ux_list_filters = [
        {'label': 'Rascunhos', 'icon': 'draft', 'url': '?status__exact=draft'},
        {'label': 'Publicados', 'icon': 'check_circle', 'url': '?status__exact=published'},
        {'label': 'Destacados', 'icon': 'stars', 'url': '?is_featured__exact=1'},
        {'label': 'Aguardando newsletter', 'icon': 'outbox', 'url': '?newsletter=pending'},
    ]
    ux_empty_message = 'Nenhum artigo encontrado. Crie um rascunho antes de publicar conteúdo no portal.'
    ux_form_title = 'Artigo editorial'
    ux_form_description = 'O formulário segue a ordem natural da redação: conteúdo, mídia, organização, publicação, SEO e estatísticas.'
    ux_form_icon = 'edit_square'
    ux_form_steps = [
        'Escreva título, resumo e conteúdo antes de mexer em publicação.',
        'Adicione imagem de capa e organize categoria/tags para facilitar navegação.',
        'Publique apenas quando autor, site e data estiverem corretos.',
    ]
    ux_after_save_description = 'Depois de publicar, avalie se o artigo deve ser destacado e enviado por newsletter.'
    ux_after_save_actions = [
        {'label': 'Guia editorial', 'icon': 'newspaper', 'url': reverse_lazy('admin_news_guide')},
        {'label': 'Rascunhos', 'icon': 'draft', 'url': format_lazy('{}?status__exact=draft', reverse_lazy('admin:news_article_changelist'))},
        {'label': 'Publicados', 'icon': 'check_circle', 'url': format_lazy('{}?status__exact=published', reverse_lazy('admin:news_article_changelist'))},
        {'label': 'Entregas de newsletter', 'icon': 'mark_email_read', 'url': reverse_lazy('admin:news_newsletterdelivery_changelist')},
    ]
    fieldsets = [
        ('Conteúdo', {
            'fields': ('title', 'slug', 'excerpt'),
            'description': 'Título e resumo. O corpo do artigo é montado nos blocos de conteúdo (abaixo do formulário).',
            'classes': ('tab',),
        }),
        ('Mídia', {
            'fields': ('featured_image', 'featured_image_caption'),
            'description': 'Adicione uma imagem de capa para o artigo. Formatos aceitos: JPG, PNG, WebP.',
            'classes': ('tab',),
        }),
        ('Organização', {
            'fields': ('category', 'tags'),
            'description': 'Organize o artigo por categoria e tags. Digite no campo de tags para buscar.',
            'classes': ('tab',),
        }),
        ('Publicação', {
            'fields': ('site', 'author', 'status', 'published_at', 'is_featured'),
            'description': 'Controle onde e quando o artigo será publicado.',
            'classes': ('tab',),
        }),
        ('SEO (Otimização para Buscadores)', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('tab',),
            'description': 'Opcional. Melhore o posicionamento do artigo no Google.',
        }),
        ('Estatísticas', {
            'fields': ('view_count', 'newsletter_sent_at', 'created_at', 'updated_at'),
            'classes': ('tab',),
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

    @admin.display(description='Newsletter', ordering='newsletter_sent_at')
    def newsletter_status(self, obj):
        if obj.newsletter_sent_at:
            return 'Enviada'
        return 'Pendente'

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
        {'label': 'Guia editorial', 'icon': 'newspaper', 'url': reverse_lazy('admin_news_guide')},
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
        {'label': 'Guia editorial', 'icon': 'newspaper', 'url': reverse_lazy('admin_news_guide')},
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
        {'label': 'Guia editorial', 'icon': 'newspaper', 'url': reverse_lazy('admin_news_guide')},
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
        {'label': 'Guia editorial', 'icon': 'newspaper', 'url': reverse_lazy('admin_news_guide')},
        {'label': 'Falhas', 'icon': 'error', 'url': format_lazy('{}?status__exact=failed', reverse_lazy('admin:news_newsletterdelivery_changelist'))},
        {'label': 'Configurações dos sites', 'icon': 'settings', 'url': reverse_lazy('admin:common_siteextension_changelist')},
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
        {'label': 'Guia editorial', 'icon': 'newspaper', 'url': reverse_lazy('admin_news_guide')},
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
        {'label': 'Guia editorial', 'icon': 'newspaper', 'url': reverse_lazy('admin_news_guide')},
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
