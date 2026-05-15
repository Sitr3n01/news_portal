from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import NewsletterSubscriptionForm
from .models import Article, ArticleBookmark, ArticleLike, Category, Comment, NewsletterSubscription, Tag
from .utils import get_sidebar_context


def safe_referer_redirect(request, default_url):
    referer = request.META.get('HTTP_REFERER')
    site_domain = get_current_site(request).domain
    if referer and url_has_allowed_host_and_scheme(url=referer, allowed_hosts={site_domain}):
        return redirect(referer)
    return redirect(default_url)

User = get_user_model()


def article_list(request):
    """Homepage do portal de noticias com artigo destaque + grid paginado."""
    articles = (
        Article.on_site
        .filter(status=Article.Status.PUBLISHED)
        .select_related('category', 'author')
        .prefetch_related('tags')
    )
    categories = Category.objects.all()

    # Featured: prioriza is_featured=True, senao o mais recente
    featured = articles.filter(is_featured=True).first() or articles.first()

    # Grid: demais artigos (excluindo featured)
    grid_articles = articles.exclude(pk=featured.pk) if featured else articles
    paginator = Paginator(grid_articles, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'news/article_list.html', {
        'featured': featured,
        'page_obj': page_obj,
        'categories': categories,
        **get_sidebar_context(),
    })


def article_detail(request, slug):
    """Detalhe do artigo com artigos relacionados, comentarios e likes."""
    article = get_object_or_404(
        Article.on_site.select_related('category', 'author').prefetch_related('tags'),
        slug=slug,
        status=Article.Status.PUBLISHED,
    )

    # Incrementar view_count atomicamente apenas se não foi visto nesta sessão
    session_key = f'viewed_article_{article.pk}'
    if not request.session.get(session_key, False):
        Article.on_site.filter(pk=article.pk).update(view_count=F('view_count') + 1)
        request.session[session_key] = True

    article.refresh_from_db(fields=['view_count'])

    # Artigos relacionados (mesma categoria, excluindo atual)
    related_articles = Article.objects.none()
    if article.category:
        related_articles = (
            Article.on_site
            .filter(status=Article.Status.PUBLISHED, category=article.category)
            .exclude(pk=article.pk)
            .select_related('category', 'author')
            .order_by('-published_at')[:3]
        )

    is_bookmarked = False
    is_liked = False
    if request.user.is_authenticated:
        is_bookmarked = ArticleBookmark.objects.filter(user=request.user, article=article).exists()
        is_liked = ArticleLike.objects.filter(user=request.user, article=article).exists()

    comments = article.comments.filter(is_active=True).select_related('user').order_by('created_at')
    comment_count = comments.count()
    like_count = article.likes.count()

    return render(request, 'news/article_detail.html', {
        'article': article,
        'related_articles': related_articles,
        'is_bookmarked': is_bookmarked,
        'is_liked': is_liked,
        'comments': comments,
        'comment_count': comment_count,
        'like_count': like_count,
        **get_sidebar_context(),
    })


def category_detail(request, slug):
    """Artigos de uma categoria especifica."""
    category = get_object_or_404(Category, slug=slug)
    articles = (
        Article.on_site
        .filter(category=category, status=Article.Status.PUBLISHED)
        .select_related('category', 'author')
        .prefetch_related('tags')
    )
    paginator = Paginator(articles, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'news/category_detail.html', {
        'category': category,
        'page_obj': page_obj,
        **get_sidebar_context(),
    })


def tag_detail(request, slug):
    """Artigos filtrados por tag."""
    tag = get_object_or_404(Tag, slug=slug)
    articles = (
        Article.on_site
        .filter(tags=tag, status=Article.Status.PUBLISHED)
        .select_related('category', 'author')
        .prefetch_related('tags')
    )
    paginator = Paginator(articles, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'news/tag_detail.html', {
        'tag': tag,
        'page_obj': page_obj,
        **get_sidebar_context(),
    })


def author_detail(request, username):
    """Perfil do autor com seus artigos publicados."""
    author = get_object_or_404(User, username=username)
    articles = (
        Article.on_site
        .filter(author=author, status=Article.Status.PUBLISHED)
        .select_related('category')
        .prefetch_related('tags')
    )
    if not articles.exists():
        raise Http404
    paginator = Paginator(articles, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'news/author_detail.html', {
        'author': author,
        'page_obj': page_obj,
        **get_sidebar_context(),
    })


def article_search(request):
    """Busca de artigos por titulo, excerpt, conteudo, tags, categoria ou autor."""
    query = request.GET.get('q', '').strip()[:200]
    articles = Article.objects.none()

    if query and len(query) >= 3:
        articles = (
            Article.on_site
            .filter(
                Q(title__icontains=query) |
                Q(excerpt__icontains=query) |
                Q(content__icontains=query) |
                Q(tags__name__icontains=query) |
                Q(category__name__icontains=query) |
                Q(author__first_name__icontains=query) |
                Q(author__last_name__icontains=query),
                status=Article.Status.PUBLISHED,
            )
            .distinct()
            .select_related('category', 'author')
        )

    paginator = Paginator(articles, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    if request.htmx:
        return render(request, 'news/partials/search_results.html', {
            'page_obj': page_obj,
            'query': query,
        })

    return render(request, 'news/search.html', {
        'page_obj': page_obj,
        'query': query,
        **get_sidebar_context(),
    })


def article_archive(request, year, month=None):
    """Arquivo de artigos por ano e mes opcional."""
    articles = (
        Article.on_site
        .filter(
            status=Article.Status.PUBLISHED,
            published_at__year=year,
        )
        .select_related('category', 'author')
    )
    if month:
        articles = articles.filter(published_at__month=month)

    paginator = Paginator(articles, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'news/archive.html', {
        'page_obj': page_obj,
        'year': year,
        'month': month,
        **get_sidebar_context(),
    })


def article_list_page(request):
    """Endpoint HTMX para load-more na listagem principal."""
    if not request.htmx:
        return redirect('news:list')

    try:
        exclude_pk = int(request.GET.get('exclude', 0)) or None
    except (ValueError, TypeError):
        exclude_pk = None
    articles = (
        Article.on_site
        .filter(status=Article.Status.PUBLISHED)
        .select_related('category', 'author')
    )
    if exclude_pk:
        articles = articles.exclude(pk=exclude_pk)

    paginator = Paginator(articles, 12)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'news/partials/article_grid.html', {'page_obj': page_obj})


@require_POST
def newsletter_subscribe(request):
    """Inscricao na newsletter (POST only, suporte HTMX)."""
    form = NewsletterSubscriptionForm(request.POST)
    if form.is_valid():
        site = get_current_site(request)
        obj, created = NewsletterSubscription.objects.get_or_create(
            email=form.cleaned_data['email'],
            site=site,
            defaults={'is_active': True},
        )
        if not created:
            obj.is_active = True
            obj.save(update_fields=['is_active'])
        if request.htmx:
            email = form.cleaned_data['email']
            response = render(request, 'news/partials/newsletter_success_cta.html', {'email': email})
            response['HX-Retarget'] = '#sidebar-newsletter'
            response['HX-Reswap'] = 'outerHTML'
            return response
        messages.success(request, "Inscrição realizada com sucesso!")
        return safe_referer_redirect(request, 'news:list')
    if request.htmx:
        return render(request, 'news/partials/newsletter_error.html', {'form': form})
    messages.error(request, "E-mail inválido. Tente novamente.")
    return safe_referer_redirect(request, 'news:list')


@login_required
def user_dashboard(request):
    """Dashboard do usuario com artigos salvos, curtidos e comentarios."""

    user = request.user
    site = get_current_site(request)

    saved_articles = (
        Article.objects
        .filter(bookmarks__user=user)
        .select_related('category', 'author')
        .order_by('-bookmarks__created_at')
    )
    liked_articles = (
        Article.objects
        .filter(likes__user=user)
        .select_related('category', 'author')
        .order_by('-likes__created_at')
    )
    user_comments = user.comments.select_related('article').order_by('-created_at')

    has_newsletter = NewsletterSubscription.objects.filter(
        email=user.email,
        site=site,
        is_active=True,
    ).exists()

    return render(request, 'news/account/dashboard.html', {
        'saved_articles': saved_articles,
        'liked_articles': liked_articles,
        'user_comments': user_comments,
        'has_newsletter': has_newsletter,
        **get_sidebar_context(),
    })


@require_POST
@login_required
def toggle_bookmark(request, article_id):
    """Toggle de bookmark de artigo para o usuario autenticado."""
    article = get_object_or_404(Article, id=article_id)
    bookmark, created = ArticleBookmark.objects.get_or_create(user=request.user, article=article)

    if not created:
        bookmark.delete()
        is_bookmarked = False
    else:
        is_bookmarked = True

    if request.htmx:
        # Se chamado do dashboard, remover o elemento da lista
        if request.GET.get('source') == 'dashboard':
            return HttpResponse('')
        # Se chamado do article_detail, retornar o botão atualizado
        return render(request, 'news/partials/bookmark_button.html', {
            'article': article,
            'is_bookmarked': is_bookmarked,
        })
    return safe_referer_redirect(request, article.get_absolute_url())


@require_POST
@login_required
def toggle_like(request, article_id):
    """Toggle de like em artigo (por usuario autenticado)."""
    article = get_object_or_404(Article, id=article_id)
    like, created = ArticleLike.objects.get_or_create(
        article=article,
        user=request.user,
        defaults={'ip_address': request.META.get('REMOTE_ADDR')},
    )
    if not created:
        like.delete()

    like_count = article.likes.count()

    if request.htmx:
        is_liked = created
        return render(request, 'news/partials/like_button.html', {
            'article': article,
            'like_count': like_count,
            'is_liked': is_liked,
        })
    return safe_referer_redirect(request, article.get_absolute_url())


@require_POST
@login_required
def add_comment(request, article_id):
    """Adiciona comentario em um artigo (usuario autenticado)."""
    article = get_object_or_404(Article, id=article_id, status=Article.Status.PUBLISHED)
    content = request.POST.get('content', '').strip()[:5000]

    if not content:
        if request.htmx:
            return HttpResponse('<p class="text-red-500 text-sm font-ui">O comentário não pode estar vazio.</p>')
        messages.error(request, 'O comentário não pode estar vazio.')
        return redirect(article.get_absolute_url())

    Comment.objects.create(article=article, user=request.user, content=content)

    if request.htmx:
        comments = article.comments.filter(is_active=True).select_related('user').order_by('created_at')
        return render(request, 'news/partials/comments_list.html', {
            'comments': comments,
            'article': article,
        })
    messages.success(request, 'Comentário publicado com sucesso!')
    return safe_referer_redirect(request, article.get_absolute_url())


@require_POST
@login_required
def delete_comment(request, comment_id):
    """Permite que o usuario delete seu proprio comentario."""
    comment = get_object_or_404(Comment, id=comment_id, user=request.user)
    article_url = comment.article.get_absolute_url()
    comment.delete()

    if request.htmx:
        return HttpResponse('')
    return safe_referer_redirect(request, article_url)


@staff_member_required
def newsletter_preview(request, article_id):
    """Preview do template de newsletter para um artigo (somente staff).

    Passa o request para que os links no preview usem o host real do servidor,
    tornando-os navegáveis no browser (em vez do domínio configurado no banco).
    """
    from .newsletter import get_newsletter_context

    article = get_object_or_404(Article, id=article_id)
    context = get_newsletter_context(article, request=request)
    html = render_to_string('news/email/newsletter_article.html', context)
    return HttpResponse(html)

