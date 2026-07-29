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

Round 7 — "Redação": dashboard do Wagtail (/cms/) reformulado com 4
componentes dedicados (cabeçalho, cartões de status, "continuar de onde
parou" e artigos recentes), relatório dedicado de artigos em revisão
(reaproveitando WorkflowView nativo) e microcopy em PT-BR nas ações de
publicação do snippet Article.
"""

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.templatetags.static import static
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, PublishingPanel
from wagtail.admin.ui.components import Component
from wagtail.admin.views.reports.workflows import WorkflowView as BaseWorkflowView
from wagtail.models import WorkflowState
from wagtail.permission_policies.base import ModelPermissionPolicy
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from apps.news.models import Article, Category, NewsHomeConfig, Tag

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


# ── Round 7: dashboard "Redação" (/cms/) ─────────────────────────────────────


def _article_status_counts():
    now = timezone.now()
    article_ct = ContentType.objects.get_for_model(Article, for_concrete_model=False)
    return {
        'published': Article.objects.filter(status=Article.Status.PUBLISHED).count(),
        'draft': Article.objects.filter(status=Article.Status.DRAFT).count(),
        'in_review': WorkflowState.objects.active().filter(base_content_type=article_ct).count(),
        'scheduled': Article.objects.filter(live=False, go_live_at__isnull=False, go_live_at__gt=now).count(),
    }


class RedacaoHeaderPanel(Component):
    """Cabeçalho do dashboard "Redação": saudação, botão de criar notícia e
    links de navegação rápida (categorias, tags, home do portal e site
    público) — estes últimos substituem os "links rápidos" do antigo
    EditorialDashboardPanel."""

    order = 90
    template_name = 'news/wagtail/redacao_header_panel.html'

    def get_context_data(self, parent_context):
        request = parent_context['request']
        user = request.user
        return {
            'visible': user.has_perm('news.view_article'),
            'display_name': user.first_name or user.get_username(),
            'can_add_article': user.has_perm('news.add_article'),
            'add_url': reverse('wagtailsnippets_news_article:add'),
            'public_site_url': reverse('news:list'),
            'can_view_categories': user.has_perm('news.view_category'),
            'category_url': reverse('wagtailsnippets_news_category:list'),
            'can_view_tags': user.has_perm('news.view_tag'),
            'tag_url': reverse('wagtailsnippets_news_tag:list'),
            'can_view_home_config': user.has_perm('news.view_newshomeconfig'),
            'home_config_url': reverse('wagtailsnippets_news_newshomeconfig:list'),
        }


class ArticleStatusCardsPanel(Component):
    """Cartões de contagem (publicadas/rascunhos/em revisão/agendadas), cada
    um linkando para a listagem filtrada correspondente."""

    order = 100
    template_name = 'news/wagtail/status_cards_panel.html'

    def get_context_data(self, parent_context):
        request = parent_context['request']
        user = request.user
        if not user.has_perm('news.view_article'):
            return {'visible': False}

        counts = _article_status_counts()
        list_url = reverse('wagtailsnippets_news_article:list')
        cards = [
            {
                'label': 'Publicadas',
                'count': counts['published'],
                'icon': 'check',
                'url': f'{list_url}?status={Article.Status.PUBLISHED}',
            },
            {
                'label': 'Rascunhos',
                'count': counts['draft'],
                'icon': 'draft',
                'url': f'{list_url}?status={Article.Status.DRAFT}',
            },
            {
                'label': 'Em revisão',
                'count': counts['in_review'],
                'icon': 'resubmit',
                'url': reverse('news_workflow_report'),
            },
            {
                'label': 'Agendadas',
                'count': counts['scheduled'],
                'icon': 'time',
                'url': list_url,
            },
        ]
        return {
            'visible': True,
            'cards': cards,
        }


class ContinueWorkingPanel(Component):
    """Atalho para o último artigo em que o usuário mexeu e que ainda não
    está publicado (ou tem alterações não publicadas)."""

    order = 110
    template_name = 'news/wagtail/continue_working_panel.html'

    def get_context_data(self, parent_context):
        request = parent_context['request']
        user = request.user
        if not user.has_perm('news.view_article'):
            return {'visible': False}

        article = (
            Article.objects.filter(latest_revision__user=user)
            .filter(Q(live=False) | Q(has_unpublished_changes=True))
            .select_related('category', 'latest_revision', 'featured_image_wagtail')
            .order_by('-latest_revision__created_at')
            .first()
        )
        if article is None:
            return {'visible': False}

        return {
            'visible': True,
            'article': article,
            'edit_url': reverse('wagtailsnippets_news_article:edit', args=[article.pk]),
        }


class RecentArticlesPanel(Component):
    """Tabela com os artigos mais recentemente atualizados, sinalizando quais
    estão em revisão. Substitui o antigo painel de tabela do
    EditorialDashboardPanel."""

    order = 150
    template_name = 'news/wagtail/recent_articles_panel.html'

    def get_context_data(self, parent_context):
        request = parent_context['request']
        if not request.user.has_perm('news.view_article'):
            return {'visible': False}

        articles = list(
            Article.objects.select_related('category', 'author', 'latest_revision', 'featured_image_wagtail')
            .order_by('-updated_at')[:8]
        )

        if articles:
            article_ct = ContentType.objects.get_for_model(Article, for_concrete_model=False)
            in_review_ids = set(
                WorkflowState.objects.active().filter(
                    base_content_type=article_ct,
                    object_id__in=[str(a.pk) for a in articles],
                ).values_list('object_id', flat=True)
            )
            for article in articles:
                article.is_in_review = str(article.pk) in in_review_ids

        return {
            'visible': bool(articles),
            'articles': articles,
            'list_url': reverse('wagtailsnippets_news_article:list'),
        }


@hooks.register('construct_homepage_panels')
def add_redacao_panels(request, panels):
    panels.extend([
        RedacaoHeaderPanel(),
        ArticleStatusCardsPanel(),
        ContinueWorkingPanel(),
        RecentArticlesPanel(),
    ])


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


# ── Round 7: CSS do dashboard "Redação" ──────────────────────────────────────


@hooks.register('insert_global_admin_css')
def redacao_dashboard_css():
    return format_html('<link rel="stylesheet" href="{}">', static('wagtailadmin/css/redacao_dashboard.css'))
