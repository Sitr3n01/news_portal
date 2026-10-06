"""Article como Snippet do Wagtail: modelo, registro, URLs, painéis do formulário e prévia."""

import pytest

from apps.news.models import Article, Tag
from apps.news.testing import make_article, make_article_full, make_site


@pytest.mark.django_db
def test_article_tags_parental_m2m():
    """Article.tags funciona como M2M normal após mudança para ParentalManyToManyField."""
    site = make_site()
    article = make_article(site, slug='tag-test')
    tag = Tag.objects.create(name='Tag Parental', slug='tag-parental')

    article.tags.add(tag)
    article.save()

    article.refresh_from_db()
    assert article.tags.count() == 1
    assert article.tags.first().name == 'Tag Parental'


@pytest.mark.django_db
def test_article_mixin_fields_exist():
    """Campos dos mixins (DraftStateMixin, RevisionMixin, LockableMixin) existem."""
    site = make_site()
    article = make_article(site, slug='mixin-test')

    # Campos de DraftStateMixin
    assert article.live is True  # default=True
    assert article.has_unpublished_changes is False
    assert article.expired is False
    assert article.first_published_at is None
    assert article.last_published_at is None

    # Campo de RevisionMixin
    assert article.latest_revision is None

    # Campos de LockableMixin
    assert article.locked is False
    assert article.locked_at is None
    assert article.locked_by is None


@pytest.mark.django_db
def test_article_snippet_registration():
    """Article, Category e Tag estão registrados como Wagtail Snippets."""
    from wagtail.snippets.models import get_snippet_models
    snippet_names = {m.__name__ for m in get_snippet_models()}
    assert 'Article' in snippet_names
    assert 'Category' in snippet_names
    assert 'Tag' in snippet_names


@pytest.mark.django_db
def test_article_snippet_urls_resolve():
    """URLs de listagem dos snippets resolvem sem erro."""
    from django.urls import reverse

    article_url = reverse('wagtailsnippets_news_article:list')
    assert '/cms/snippets/news/article/' in article_url

    category_url = reverse('wagtailsnippets_news_category:list')
    assert '/cms/snippets/news/category/' in category_url

    tag_url = reverse('wagtailsnippets_news_tag:list')
    assert '/cms/snippets/news/tag/' in tag_url


# ── Wagtail admin ─────────────────────────────────────────────────────────────


def _panel_field_names(panels):
    """Nomes de campo de uma lista de painéis, DESCENDO nos painéis compostos.

    Um FieldPanel dentro de MultiFieldPanel está tão presente no formulário como
    um solto no topo — checar só o nível raiz daria falso negativo e nos faria
    "consertar" a estrutura do formulário para agradar o teste.
    """
    names = []
    for panel in panels:
        if hasattr(panel, 'field_name'):
            names.append(panel.field_name)
        names.extend(_panel_field_names(getattr(panel, 'children', []) or []))
    return names


@pytest.mark.django_db
def test_wagtail_snippet_panels_include_featured_image_wagtail():
    """O FieldPanel de featured_image_wagtail está nos painéis do SnippetViewSet."""
    from apps.news.wagtail_hooks import ArticleSnippetViewSet

    panel_names = _panel_field_names(ArticleSnippetViewSet().panels)

    assert 'featured_image_wagtail' in panel_names
    # featured_image (campo antigo) NÃO deve estar nos painéis Wagtail
    assert 'featured_image' not in panel_names


@pytest.mark.django_db
def test_wagtail_snippet_panels_hide_status_field():
    """Round 6: status não aparece no formulário — é controlado só pelos
    botões nativos Publicar/Despublicar/Salvar rascunho (sincronizados via
    signals), evitando dois controles para o mesmo estado."""
    from apps.news.wagtail_hooks import ArticleSnippetViewSet

    panel_names = _panel_field_names(ArticleSnippetViewSet().panels)

    assert 'status' not in panel_names


@pytest.mark.django_db
def test_wagtail_snippet_panels_cover_every_editable_field():
    """Nenhum campo editável do Article fica sem tela.

    O Article deixou de ser registrado no admin do Django, então o formulário do
    snippet é a ÚNICA porta de edição. Quando is_featured, featured_image_caption,
    meta_title e meta_description saíram dos painéis, os quatro continuaram sendo
    lidos pelo site público e ninguém tinha onde preenchê-los. Este teste existe
    para que o próximo campo esquecido apareça aqui e não em produção.
    """
    from apps.news.wagtail_hooks import ArticleSnippetViewSet

    panel_names = set(_panel_field_names(ArticleSnippetViewSet().panels))

    # Mantidos pela máquina, não por gente: os botões de publicação do Wagtail
    # (ver teste acima), o agendamento do PublishingPanel e o contador de acessos
    # incrementado por apps.news.views.article_detail.
    machine_maintained = {
        'status', 'published_at', 'first_published_at', 'expire_at', 'go_live_at',
        'view_count',
    }
    # Substituído por featured_image_wagtail; segue no modelo só para ler o acervo.
    legacy = {'featured_image'}

    editable = {
        field.name for field in Article._meta.get_fields()
        if getattr(field, 'editable', False) and not field.auto_created
    }
    missing = editable - panel_names - machine_maintained - legacy

    assert not missing, f'Campos editáveis sem FieldPanel (inalcançáveis na interface): {sorted(missing)}'


@pytest.mark.django_db
def test_article_get_preview_context_renders_public_template(rf):
    """get_preview_context() supre as variáveis que news/article_detail.html exige.

    Regressão: PreviewableMixin.get_preview_context() por padrão só fornece
    `object`/`request`, mas o template de preview (reusado da página pública)
    também referencia `article`, `comments`, `related_articles` etc. Sem
    Article.get_preview_context() sobrescrito, a renderização quebra com
    VariableDoesNotExist para qualquer artigo — reproduzido manualmente via
    o botão "Alternar pré-visualização" no /cms/ antes da correção.
    """
    from django.template.loader import render_to_string

    site = make_site()
    article = make_article_full(site, slug='preview-check')
    request = rf.get('/')

    context = article.get_preview_context(request, 'default')
    assert context['article'] == article
    assert context['comments'].count() == 0
    assert context['comment_count'] == 0

    html = render_to_string(article.get_preview_template(request, 'default'), context, request=request)
    assert article.title in html
