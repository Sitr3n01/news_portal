"""Registra Category, Tag e Article como Wagtail Snippets.

Category e Tag são administrados exclusivamente via Wagtail Snippets.

Article vira Snippet com suporte a preview, revisões, rascunho e
bloqueio, usando SnippetViewSet para customização dos painéis de edição.

NewsHomeConfig registrado como Snippet, seguindo mesmo padrão de
SiteExtension para singleton por site.

Round 6 — FieldPanel('status') removido do formulário: o campo agora é
controlado exclusivamente pelos botões nativos do Wagtail (Publicar/
Despublicar/Salvar rascunho), sincronizados via signals em
apps/news/signals.py. Editar o dropdown manualmente ao lado desses botões
era uma fonte de confusão (dois controles para o mesmo estado).

Round 7 — relatório dedicado de artigos em revisão (reaproveitando
WorkflowView nativo) e microcopy em PT-BR nas ações de publicação do snippet
Article. Os painéis "Redação" da página inicial do /cms/ migraram para a visão
geral unificada (/painel/).
"""

from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, PublishingPanel
from wagtail.admin.views.reports.workflows import WorkflowView as BaseWorkflowView
from wagtail.permission_policies.base import ModelPermissionPolicy
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from apps.news.editorial import article_status_counts
from apps.news.models import Article, Category, NewsHomeConfig, Tag
from apps.news.wagtail_moderation import (
    BULK_ACTIONS,
    CommentSnippetViewSet,
    NewsletterDeliverySnippetViewSet,
    NewsletterSubscriptionSnippetViewSet,
)

register_snippet(Category)
register_snippet(Tag)


class ArticleSnippetViewSet(SnippetViewSet):
    model = Article
    icon = 'newspaper'
    menu_label = 'Notícias'
    menu_name = 'article-snippets'
    menu_order = 100
    add_to_admin_menu = True
    list_display = ('title', 'category', 'status', 'published_at', 'is_featured')
    list_filter = ('status', 'category', 'site', 'is_featured')
    search_fields = ('title', 'excerpt')

    # Todo campo editável do modelo precisa aparecer aqui: o Article deixou de ser
    # registrado no admin do Django (apps/news/admin.py), então este formulário é a
    # ÚNICA tela que existe para ele. Campo fora desta lista fica inalcançável —
    # foi o que aconteceu com is_featured, featured_image_caption, meta_title e
    # meta_description, todos consumidos pelo site público mas sem onde preencher.
    # Exceção deliberada: `status`, controlado só pelos botões nativos de
    # publicação (ver o docstring do módulo).
    panels = [
        FieldPanel('title'),
        FieldPanel('slug'),
        FieldPanel('excerpt'),
        MultiFieldPanel(
            [
                FieldPanel('featured_image_wagtail'),
                FieldPanel('featured_image_caption'),
            ],
            heading='Imagem de capa',
        ),
        FieldPanel('category'),
        FieldPanel('tags'),
        FieldPanel('body'),
        FieldPanel('site'),
        FieldPanel('author'),
        MultiFieldPanel(
            [
                FieldPanel('meta_title'),
                FieldPanel('meta_description'),
                FieldPanel('meta_keywords'),
            ],
            heading='SEO',
            help_text=(
                'Como a matéria aparece no Google e ao ser compartilhada. '
                'Em branco, o portal usa o título e o resumo.'
            ),
        ),
        # is_featured decide o destaque automático da home
        # (apps/news/views.py::_resolve_home_highlights) quando não há
        # NewsHomeConfig com hero manual. Fica junto da publicação porque é
        # decisão editorial do mesmo momento.
        FieldPanel('is_featured'),
        PublishingPanel(),
    ]


register_snippet(ArticleSnippetViewSet)


class NewsHomeConfigSnippetViewSet(SnippetViewSet):
    model = NewsHomeConfig
    icon = 'home'
    menu_label = 'Home do Portal de Notícias'
    menu_name = 'news-home-config'
    add_to_admin_menu = True
    list_display = ('site', 'is_active', 'updated_at')
    search_fields = ('site__name',)

    panels = [
        FieldPanel('site', help_text='Não altere depois de criado — é 1-para-1 com o portal.'),
        FieldPanel('is_active'),
        FieldPanel('hero_override'),
        FieldPanel('secondary_highlights'),
        MultiFieldPanel([
            FieldPanel('meta_title'),
            FieldPanel('meta_description'),
        ], heading='SEO da home'),
    ]


register_snippet(NewsHomeConfigSnippetViewSet)


# ── Comentários e newsletter (migrados do Django admin) ──────────────────────
# Ver apps/news/wagtail_moderation.py para o motivo e a paridade de recursos.

register_snippet(CommentSnippetViewSet)
register_snippet(NewsletterSubscriptionSnippetViewSet)
register_snippet(NewsletterDeliverySnippetViewSet)

for _bulk_action in BULK_ACTIONS:
    hooks.register('register_bulk_action', _bulk_action)


# ── Contagens editoriais ─────────────────────────────────────────────────────
#
# O dashboard "Redação" que vivia na página inicial do /cms/ foi absorvido pela
# visão geral do painel unificado (/painel/, apps/common/newsroom): mesmos
# números, mesma fonte (apps/news/editorial.py). A página inicial do /cms/
# agora redireciona para lá (config/urls.py).


def _article_status_counts():
    """Mantido por compatibilidade; a regra mora em apps.news.editorial."""
    return article_status_counts()


# ── Round 7: microcopy PT-BR nas ações do snippet Article ───────────────────


@hooks.register('construct_snippet_action_menu')
def relabel_article_publishing_actions(menu_items, request, context):
    if context.get('model') is not Article:
        return
    for item in menu_items:
        if item.name == 'action-unpublish':
            item.label = 'Retirar do ar'


# ── Round 7: relatório dedicado "Notícias em revisão" ────────────────────────


class ArticleWorkflowReportView(BaseWorkflowView):
    """Reaproveita o WorkflowView nativo do Wagtail (relatório de Workflows),
    trocando apenas a política de permissão de página pela política de
    permissão do snippet Article — a queryset nativa já filtra por
    conteúdo editável pelo usuário e é compatível com snippets, então não
    precisa ser reescrita.

    index_url_name/index_results_url_name são sobrescritos para apontar
    para as URLs próprias deste relatório (registradas abaixo), evitando
    colisão com o relatório nativo de Workflows de Páginas
    (`wagtailadmin_reports:workflow` / `wagtailadmin_reports:workflow_results`).
    """

    permission_policy = ModelPermissionPolicy(Article)
    any_permission_required = ['view']
    header_icon = 'resubmit'
    page_title = 'Notícias em revisão'
    index_url_name = 'news_workflow_report'
    index_results_url_name = 'news_workflow_report_results'


@hooks.register('register_admin_urls')
def register_article_workflow_report_urls():
    return [
        path(
            'reports/noticias-em-revisao/',
            ArticleWorkflowReportView.as_view(),
            name='news_workflow_report',
        ),
        path(
            'reports/noticias-em-revisao/results/',
            ArticleWorkflowReportView.as_view(results_only=True),
            name='news_workflow_report_results',
        ),
    ]


class ArticleReportsMenuItem(MenuItem):
    def is_shown(self, request):
        return request.user.has_perm('news.view_article')


@hooks.register('register_reports_menu_item')
def register_article_workflow_report_menu_item():
    return ArticleReportsMenuItem(
        'Notícias em revisão',
        reverse('news_workflow_report'),
        name='noticias-em-revisao',
        icon_name='resubmit',
        order=100,
    )
