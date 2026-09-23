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

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.functional import cached_property
from wagtail import hooks
from wagtail.admin import messages
from wagtail.admin.auth import permission_denied
from wagtail.admin.menu import MenuItem
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, ObjectList
from wagtail.admin.ui.tables import Column
from wagtail.admin.views.reports.workflows import WorkflowView as BaseWorkflowView
from wagtail.permission_policies.base import ModelPermissionPolicy
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from apps.news.editorial import article_status_counts
from apps.news.models import Article, Category, NewsHomeConfig, Tag
from apps.news.permissions import (
    CHANGE_PERMISSION,
    PUBLISH_PERMISSION,
    ArticlePermissionPolicy,
    can_edit_article,
)
from apps.news.wagtail_article import (
    ArticleAdminForm,
    ArticleCopyView,
    ArticleCreateView,
    ArticleIndexView,
    ArticlePreviewOnCreateView,
    RestrictedPublishingPanel,
)
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
    list_display = (
        'title', 'category', 'status', 'published_at',
        # Só marca o que está em destaque; antes a coluna exibia "True/False" cru.
        Column(
            'is_featured', label='Destaque', sort_key='is_featured',
            accessor=lambda article: 'Em destaque' if article.is_featured else '',
        ),
    )
    list_filter = ('status', 'category', 'site', 'is_featured')
    search_fields = ('title', 'excerpt')

    # Regra editorial por notícia (apps/news/permissions.py): quem não publica
    # altera as próprias notícias e as dos colegas só enquanto forem rascunho.
    index_view_class = ArticleIndexView
    add_view_class = ArticleCreateView
    copy_view_class = ArticleCopyView
    preview_on_add_view_class = ArticlePreviewOnCreateView
    # Ficha somente leitura: é para onde a listagem leva quem não pode editar.
    inspect_view_enabled = True
    inspect_view_fields = ['title', 'excerpt', 'category', 'tags', 'author', 'status', 'published_at']

    @cached_property
    def permission_policy(self):
        return ArticlePermissionPolicy(self.model)

    # Todo campo editável do modelo precisa aparecer aqui: o Article deixou de ser
    # registrado no admin do Django (apps/news/admin.py), então este formulário é a
    # ÚNICA tela que existe para ele. Campo fora desta lista fica inalcançável —
    # foi o que aconteceu com is_featured, featured_image_caption, meta_title e
    # meta_description, todos consumidos pelo site público mas sem onde preencher.
    # Exceção deliberada: `status`, controlado só pelos botões nativos de
    # publicação (ver o docstring do módulo).
    #
    # Campos com `permission=PUBLISH_PERMISSION` só existem no formulário de
    # quem publica — o Wagtail os remove no servidor para os demais: destaque na
    # home, portal, autor (a notícia nasce assinada por quem cria) e agendamento.
    panels = [
        FieldPanel('title'),
        FieldPanel(
            'slug',
            help_text=(
                'Endereço da notícia. Pode mudar depois de publicada: o endereço antigo '
                'passa a levar automaticamente ao novo.'
            ),
        ),
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
        FieldPanel('site', permission=PUBLISH_PERMISSION),
        FieldPanel('author', permission=PUBLISH_PERMISSION),
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
        FieldPanel('is_featured', permission=PUBLISH_PERMISSION),
        RestrictedPublishingPanel(permission=PUBLISH_PERMISSION),
    ]
    edit_handler = ObjectList(panels, base_form_class=ArticleAdminForm)


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


# ── Porta da edição por notícia ──────────────────────────────────────────────
#
# A edição do Wagtail 7.4 confere só a permissão de modelo. Este hook oficial
# roda antes da view de edição E da de restaurar revisão (que herda dela) —
# GET e POST —, aplicando a regra de apps/news/permissions.py no servidor.
#
# A view entrega ao hook a ÚLTIMA REVISÃO como objeto, e o ``status`` guardado
# numa revisão é o do momento em que ela foi salva (uma notícia retirada do ar
# volta a aparecer como rascunho). A regra olha a linha gravada no banco, que é
# o estado real da notícia.


@hooks.register('before_edit_snippet')
def enforce_article_edit_rule(request, instance):
    if not isinstance(instance, Article):
        return None
    stored = Article._default_manager.filter(pk=instance.pk).only('status', 'author_id').first()
    if stored is None or not request.user.has_perm(CHANGE_PERMISSION):
        return permission_denied(request)
    if can_edit_article(request.user, stored):
        return None
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        raise PermissionDenied
    # Em vez do "sem permissão" genérico, explica a regra e leva à ficha
    # somente leitura da notícia, de onde dá para copiá-la como rascunho novo.
    messages.error(
        request,
        'Esta notícia é de outra pessoa e já esteve no ar: só quem publica pode alterá-la. '
        'Você pode consultá-la aqui ou copiá-la como um novo rascunho.',
    )
    return redirect('wagtailsnippets_news_article:inspect', stored.pk)


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
