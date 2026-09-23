"""Dados da visão geral unificada (``/painel/``).

Tudo aqui é consulta de leitura sobre os modelos existentes, sempre filtrada
pelo que o usuário pode ver — a mesma regra que decide os itens da sidebar
(``navigation.is_item_visible``). Nenhum número é inventado: indicador sem
fonte real simplesmente não é exibido.

Ações (criar, editar, publicar, despublicar, revisar, excluir) são LINKS para
as views nativas do Wagtail/Django admin, que continuam aplicando as próprias
checagens de permissão, bloqueio e fluxo de revisão.
"""

from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.urls import reverse
from django.utils import timezone

from apps.accounts import panels
from apps.common.dashboard import build_guide_links, build_system_health
from apps.common.newsroom.navigation import is_item_visible, item_url

PER_PAGE = 10
SEARCH_MAX_LENGTH = 100
VIEW_LIST = 'list'
VIEW_GRID = 'grid'
THUMB_TONES = ('blue', 'violet', 'sand', 'green')


_QUERY_DEFAULTS = {'status': 'all', 'view': VIEW_LIST, 'page': 1}


def _querystring(**params):
    """Querystring só com o que difere do padrão, na ordem dos parâmetros."""
    clean = {
        key: value for key, value in params.items()
        if value not in (None, '') and value != _QUERY_DEFAULTS.get(key)
    }
    return f'?{urlencode(clean)}' if clean else '?'


def _parse_params(request, allowed_status):
    query = (request.GET.get('q') or '').strip()[:SEARCH_MAX_LENGTH]
    status = request.GET.get('status') or 'all'
    if status not in allowed_status:
        status = 'all'
    view = request.GET.get('view') if request.GET.get('view') in (VIEW_LIST, VIEW_GRID) else VIEW_LIST
    return query, status, view


def _stat(label, icon, value, note, url=''):
    return {'label': label, 'icon': icon, 'value': value, 'note': note, 'url': url}


# ── Blog da Kelly ──────────────────────────────────────────────────────────


def _article_policy():
    from apps.news.models import Article

    return Article.snippet_viewset.permission_policy


def kelly_stats(request):
    from apps.news.editorial import article_status_counts
    from apps.news.models import Article, Comment

    stats = []
    now = timezone.now()
    show_articles = is_item_visible(request, 'articles')
    show_review = is_item_visible(request, 'review')
    counts = article_status_counts() if (show_articles or show_review) else {}
    if show_articles:
        list_url = item_url(request, 'articles')
        recent_published = Article.objects.filter(
            status=Article.Status.PUBLISHED, published_at__gte=now - timedelta(days=30),
        ).count()
        drafts_today = Article.objects.filter(
            status=Article.Status.DRAFT, updated_at__date=timezone.localdate(now),
        ).count()
        stats.append(_stat(
            'Publicadas', 'news', counts['published'],
            f'{recent_published} nos últimos 30 dias',
            f'{list_url}?status={Article.Status.PUBLISHED}',
        ))
        stats.append(_stat(
            'Rascunhos', 'edit', counts['draft'],
            f'{drafts_today} atualizado hoje' if drafts_today == 1 else f'{drafts_today} atualizados hoje',
            f'{list_url}?status={Article.Status.DRAFT}',
        ))
    if show_review:
        stats.append(_stat(
            'Em revisão', 'clock', counts['in_review'],
            'Aguardando aprovação' if counts['in_review'] else 'Nenhuma aguardando',
            item_url(request, 'review'),
        ))
    if is_item_visible(request, 'comments'):
        pending = Comment.objects.filter(is_active=False).count()
        stats.append(_stat(
            'Comentários', 'comment', pending,
            'Aguardando moderação' if pending else 'Nenhum aguardando moderação',
            f"{item_url(request, 'comments')}?is_active=false",
        ))
    return stats


def _article_actions(request, article, state):
    from apps.news.editorial import STATE_PUBLISHED

    policy = _article_policy()
    user = request.user
    actions = []
    # Por notícia, não por modelo: quem não publica só altera as próprias e
    # os rascunhos dos colegas (apps/news/permissions.py). As demais abrem a
    # ficha somente leitura — a mesma regra que a edição do Wagtail aplica.
    can_change = policy.user_has_permission_for_instance(user, 'change', article)
    if can_change:
        label = 'Revisar' if state == 'review' else 'Editar'
        actions.append({'label': label, 'icon': 'edit',
                        'url': reverse('wagtailsnippets_news_article:edit', args=[article.pk])})
    else:
        actions.append({'label': 'Ver', 'icon': 'eye',
                        'url': reverse('wagtailsnippets_news_article:inspect', args=[article.pk])})
    actions.append({'label': 'Histórico', 'icon': 'clock',
                    'url': reverse('wagtailsnippets_news_article:history', args=[article.pk])})
    if state == STATE_PUBLISHED or article.live:
        actions.append({'label': 'Ver no site', 'icon': 'external', 'url': article.get_absolute_url(),
                        'external': True})
    if article.live and policy.user_has_permission(user, 'publish'):
        actions.append({'label': 'Despublicar', 'icon': 'eye-off',
                        'url': reverse('wagtailsnippets_news_article:unpublish', args=[article.pk])})
    if policy.user_has_permission(user, 'delete'):
        actions.append({'label': 'Excluir', 'icon': 'trash', 'danger': True,
                        'url': reverse('wagtailsnippets_news_article:delete', args=[article.pk])})
    return actions


def kelly_articles(request):
    """Listagem paginada no servidor — busca, aba de estado e categoria."""
    from apps.news import editorial
    from apps.news.models import Article, Category

    query, status, view = _parse_params(request, editorial.FILTER_KEYS)
    category_id = request.GET.get('categoria') or ''
    if not category_id.isdigit():
        category_id = ''

    queryset = (
        Article.objects
        .select_related('category', 'author', 'featured_image_wagtail')
        .prefetch_related(Prefetch('featured_image_wagtail__renditions'))
        .order_by('-updated_at', '-pk')
    )
    if query:
        queryset = queryset.filter(title__icontains=query)
    if category_id:
        queryset = queryset.filter(category_id=int(category_id))
    queryset = editorial.filter_articles(queryset, status)

    page = Paginator(queryset, PER_PAGE).get_page(request.GET.get('page'))
    articles = list(page.object_list)
    pks = [article.pk for article in articles]
    review_ids = editorial.in_review_ids(pks)
    scheduled = editorial.scheduled_ids(pks)

    rows = []
    for article in articles:
        state = editorial.editorial_state(article, review_ids, scheduled)
        actions = _article_actions(request, article, state)
        author = (article.author.get_full_name() or article.author.get_username()) if article.author else ''
        rows.append({
            'pk': article.pk,
            'title': article.title,
            'path': article.get_absolute_url(),
            'category': article.category.name if article.category else 'Sem categoria',
            'author': author or 'Sem autor',
            'state': state,
            'state_label': editorial.STATE_LABELS[state],
            'unpublished_changes': article.live and article.has_unpublished_changes,
            'updated_at': article.updated_at,
            'image_url': article.card_image_url,
            'tone': THUMB_TONES[(article.category_id or 0) % len(THUMB_TONES)],
            'edit_url': actions[0]['url'],
            'actions': actions,
        })

    base = {'q': query, 'categoria': category_id, 'view': view}
    tabs = [
        {'key': key, 'label': label, 'active': key == status,
         'url': _querystring(status=key, **base)}
        for key, label in editorial.FILTERS
    ]

    return {
        'kind': 'articles',
        'rows': rows,
        'page': page,
        'tabs': tabs,
        'status': status,
        'query': query,
        'view': view,
        'category_id': category_id,
        'categories': list(Category.objects.order_by('name').values('pk', 'name')),
        'prev_url': _querystring(status=status, page=page.previous_page_number(), **base) if page.has_previous() else '',
        'next_url': _querystring(status=status, page=page.next_page_number(), **base) if page.has_next() else '',
        'noun_singular': 'notícia',
        'noun_plural': 'notícias',
        'search_placeholder': 'Pesquisar pelo título da notícia...',
        'search_label': 'Pesquisar notícias pelo título',
        'filtered': bool(query or category_id or status != 'all'),
    }


_LOG_ACTION_PHRASES = {
    'wagtail.create': 'criou',
    'wagtail.edit': 'editou',
    'wagtail.publish': 'publicou',
    'wagtail.publish.scheduled': 'agendou a publicação de',
    'wagtail.schedule.cancel': 'cancelou o agendamento de',
    'wagtail.unpublish': 'retirou do ar',
    'wagtail.unpublish.scheduled': 'agendou a retirada de',
    'wagtail.delete': 'excluiu',
    'wagtail.revert': 'restaurou uma versão de',
    'wagtail.lock': 'bloqueou',
    'wagtail.unlock': 'desbloqueou',
    'wagtail.workflow.start': 'enviou para revisão',
    'wagtail.workflow.approve': 'aprovou',
    'wagtail.workflow.reject': 'pediu alterações em',
    'wagtail.workflow.resume': 'reenviou para revisão',
    'wagtail.workflow.cancel': 'cancelou a revisão de',
}
_LOG_ALERT_ACTIONS = {'wagtail.workflow.start', 'wagtail.workflow.reject', 'wagtail.unpublish', 'wagtail.delete'}


def kelly_activity(request, limit=6):
    """Auditoria real: log do Wagtail sobre notícias + comentários recebidos."""
    from wagtail.models import ModelLogEntry

    from apps.news.editorial import article_content_type
    from apps.news.models import Comment

    events = []
    if is_item_visible(request, 'articles'):
        entries = (
            ModelLogEntry.objects
            .filter(content_type=article_content_type(), action__in=_LOG_ACTION_PHRASES.keys())
            .select_related('user')
            .order_by('-timestamp')[:limit]
        )
        for entry in entries:
            who = entry.user_display_name or 'Sistema'
            events.append({
                'title': f'{who} {_LOG_ACTION_PHRASES[entry.action]} “{entry.label}”',
                'caption': 'Notícias',
                'when': entry.timestamp,
                'tone': 'alert' if entry.action in _LOG_ALERT_ACTIONS else 'info',
            })
    if is_item_visible(request, 'comments'):
        comments = (
            Comment.objects.select_related('article', 'user')
            .order_by('-created_at')[:limit]
        )
        for comment in comments:
            events.append({
                'title': (
                    f'Novo comentário aguardando moderação em “{comment.article.title}”'
                    if not comment.is_active else f'Novo comentário em “{comment.article.title}”'
                ),
                'caption': 'Comentários',
                'when': comment.created_at,
                'tone': 'alert' if not comment.is_active else 'info',
            })
    events.sort(key=lambda event: event['when'], reverse=True)
    return events[:limit]


def kelly_quick_links(request):
    from apps.news.models import Article

    links = []
    if is_item_visible(request, 'articles'):
        own_draft = (
            Article.objects.filter(latest_revision__user=request.user)
            .filter(Q(live=False) | Q(has_unpublished_changes=True))
            .order_by('-latest_revision__created_at')
            .only('pk')
            .first()
        )
        if own_draft and _article_policy().user_has_permission(request.user, 'change'):
            url = reverse('wagtailsnippets_news_article:edit', args=[own_draft.pk])
            label = 'Continuar editando seu último rascunho'
        else:
            url = f"{item_url(request, 'articles')}?status={Article.Status.DRAFT}"
            label = 'Continuar editando rascunhos'
        links.append({'label': label, 'icon': 'edit', 'url': url})
    if is_item_visible(request, 'comments'):
        links.append({'label': 'Moderar comentários', 'icon': 'comment',
                      'url': f"{item_url(request, 'comments')}?is_active=false"})
    if is_item_visible(request, 'images'):
        links.append({'label': 'Gerenciar biblioteca de mídia', 'icon': 'image', 'url': item_url(request, 'images')})
    if is_item_visible(request, 'news_home'):
        links.append({'label': 'Destaques da home do portal', 'icon': 'home', 'url': item_url(request, 'news_home')})
    if is_item_visible(request, 'site_settings'):
        links.append({'label': 'Configurações do portal', 'icon': 'settings', 'url': item_url(request, 'site_settings')})
    return links


# ── Komuniki ───────────────────────────────────────────────────────────────


def komuniki_stats(request):
    from apps.contact.models import ContactInquiry
    from apps.school.models import SchoolFeature
    from apps.social.models import SocialAccount, SocialPost

    stats = []
    week_ago = timezone.now() - timedelta(days=7)
    if is_item_visible(request, 'messages'):
        url = item_url(request, 'messages')
        new = ContactInquiry.objects.filter(status=ContactInquiry.Status.NEW).count()
        received = ContactInquiry.objects.filter(created_at__gte=week_ago).count()
        read = ContactInquiry.objects.filter(status=ContactInquiry.Status.READ).count()
        stats.append(_stat('Mensagens novas', 'inbox', new,
                           f'{received} recebidas em 7 dias' if received != 1 else '1 recebida em 7 dias',
                           f'{url}?status__exact={ContactInquiry.Status.NEW}'))
        stats.append(_stat('Em atendimento', 'clock', read, 'Lidas, sem resposta registrada',
                           f'{url}?status__exact={ContactInquiry.Status.READ}'))
    if is_item_visible(request, 'school_features'):
        active = SchoolFeature.objects.filter(is_active=True, placement=SchoolFeature.Placement.TRUST).count()
        stats.append(_stat('Blocos ativos', 'blocks', active, 'Barra de confiança da home',
                           item_url(request, 'school_features')))
    if is_item_visible(request, 'social_posts'):
        visible = SocialPost.objects.filter(is_visible=True).count()
        accounts = SocialAccount.objects.filter(is_active=True).count()
        stats.append(_stat('Posts visíveis', 'layers', visible,
                           f'{accounts} conta ativa' if accounts == 1 else f'{accounts} contas ativas',
                           item_url(request, 'social_posts')))
    return stats


MESSAGE_FILTERS = (
    ('all', 'Todas'),
    ('new', 'Novas'),
    ('read', 'Lidas'),
    ('replied', 'Respondidas'),
    ('archived', 'Arquivadas'),
)
MESSAGE_STATE_TONES = {'new': 'review', 'read': 'scheduled', 'replied': 'published', 'archived': 'draft'}


def komuniki_messages(request):
    from apps.contact.models import ContactInquiry

    allowed = {key for key, _label in MESSAGE_FILTERS}
    query, status, view = _parse_params(request, allowed)
    queryset = ContactInquiry.objects.select_related('site').order_by('-created_at', '-pk')
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query) | Q(email__icontains=query) | Q(course_interest__icontains=query)
        )
    if status != 'all':
        queryset = queryset.filter(status=status)

    page = Paginator(queryset, PER_PAGE).get_page(request.GET.get('page'))
    rows = []
    for message in page.object_list:
        url = reverse('admin:contact_contactinquiry_change', args=[message.pk])
        detail = message.get_subject_display()
        if message.course_interest:
            detail = f'{detail} · {message.course_interest}'
        rows.append({
            'pk': message.pk,
            'title': message.name,
            'path': message.email,
            'category': detail,
            'author': message.site.name if message.site_id else '',
            'state': MESSAGE_STATE_TONES.get(message.status, 'draft'),
            'state_label': message.get_status_display(),
            'updated_at': message.created_at,
            'image_url': '',
            'initial': (message.name or '?')[:1].upper(),
            'tone': 'blue',
            'edit_url': url,
            'actions': [{'label': 'Abrir mensagem', 'icon': 'inbox', 'url': url}],
        })

    base = {'q': query, 'view': view}
    tabs = [
        {'key': key, 'label': label, 'active': key == status, 'url': _querystring(status=key, **base)}
        for key, label in MESSAGE_FILTERS
    ]
    return {
        'kind': 'messages',
        'rows': rows,
        'page': page,
        'tabs': tabs,
        'status': status,
        'query': query,
        'view': view,
        'category_id': '',
        'categories': [],
        'prev_url': _querystring(status=status, page=page.previous_page_number(), **base) if page.has_previous() else '',
        'next_url': _querystring(status=status, page=page.next_page_number(), **base) if page.has_next() else '',
        'noun_singular': 'mensagem',
        'noun_plural': 'mensagens',
        'search_placeholder': 'Pesquisar por nome, e-mail ou curso...',
        'search_label': 'Pesquisar mensagens por nome, e-mail ou curso',
        'filtered': bool(query or status != 'all'),
    }


_KOMUNIKI_APPS = ('school', 'contact', 'social', 'media_library')
_ADMIN_ACTION_PHRASES = {ADDITION: 'adicionou', CHANGE: 'alterou', DELETION: 'excluiu'}


def komuniki_activity(request, limit=6):
    """Auditoria real: log do Django admin sobre modelos da Komuniki que o
    usuário pode ver, mais as mensagens recém-chegadas."""
    from apps.contact.models import ContactInquiry

    user = request.user
    events = []
    if panels.can_access_admin(user):
        allowed_ct_ids = [
            ct.pk for ct in ContentType.objects.filter(app_label__in=_KOMUNIKI_APPS)
            if user.has_perm(f'{ct.app_label}.view_{ct.model}') or user.has_perm(f'{ct.app_label}.change_{ct.model}')
        ]
        entries = (
            LogEntry.objects.filter(content_type_id__in=allowed_ct_ids)
            .select_related('user', 'content_type')
            .order_by('-action_time')[:limit]
        )
        for entry in entries:
            who = entry.user.get_full_name() or entry.user.get_username()
            model_name = entry.content_type.model_class()._meta.verbose_name if entry.content_type.model_class() else ''
            events.append({
                'title': f'{who} {_ADMIN_ACTION_PHRASES.get(entry.action_flag, "alterou")} “{entry.object_repr}”',
                'caption': str(model_name).capitalize(),
                'when': entry.action_time,
                'tone': 'alert' if entry.action_flag == DELETION else 'info',
            })
    if is_item_visible(request, 'messages'):
        for message in ContactInquiry.objects.order_by('-created_at')[:limit]:
            events.append({
                'title': f'Nova mensagem de {message.name}',
                'caption': message.get_subject_display(),
                'when': message.created_at,
                'tone': 'alert' if message.status == ContactInquiry.Status.NEW else 'info',
            })
    events.sort(key=lambda event: event['when'], reverse=True)
    return events[:limit]


def komuniki_quick_links(request):
    from apps.contact.models import ContactInquiry

    links = []
    if is_item_visible(request, 'messages'):
        links.append({'label': 'Responder mensagens novas', 'icon': 'inbox',
                      'url': f"{item_url(request, 'messages')}?status__exact={ContactInquiry.Status.NEW}"})
    if is_item_visible(request, 'school_home'):
        links.append({'label': 'Editar textos da Home Komuniki', 'icon': 'home', 'url': item_url(request, 'school_home')})
    if is_item_visible(request, 'school_pages'):
        links.append({'label': 'Publicação da página Cursos', 'icon': 'book', 'url': item_url(request, 'school_pages')})
    if is_item_visible(request, 'social_posts'):
        links.append({'label': 'Posts das redes sociais', 'icon': 'layers', 'url': item_url(request, 'social_posts')})
    return links


# ── Montagem ───────────────────────────────────────────────────────────────


# Guia de cada espaço: o da Komuniki só faz sentido lá; o de gerenciamento
# (usuários, mídia, remetentes) vale nos dois.
_GUIDES_BY_WORKSPACE = {
    'kelly': {'admin_management_guide'},
    'komuniki': {'admin_school_guide', 'admin_management_guide'},
}


def _guide_links(request, workspace_key):
    if not panels.can_access_admin(request.user):
        return []
    wanted = _GUIDES_BY_WORKSPACE.get(workspace_key, {'admin_school_guide', 'admin_management_guide'})
    return [
        {'label': guide['title'], 'icon': guide['icon'], 'url': guide['url']}
        for guide in build_guide_links(request.user)
        if guide['route'] in wanted
    ]


def _primary_action(request, workspace_key):
    if workspace_key == 'kelly':
        if panels.can_access_cms(request.user) and is_item_visible(request, 'articles') \
                and _article_policy().user_has_permission(request.user, 'add'):
            return {'label': 'Nova notícia', 'url': reverse('wagtailsnippets_news_article:add')}
    if workspace_key == 'komuniki' and panels.can_access_admin(request.user):
        if is_item_visible(request, 'social_posts') and request.user.has_perm('social.add_socialpost'):
            return {'label': 'Novo post social', 'url': reverse('admin:social_socialpost_add')}
    return None


def _system_health(request, workspace_key):
    if workspace_key != 'kelly':
        return None
    user = request.user
    if panels.can_access_admin(user) or is_item_visible(request, 'newsletter_deliveries'):
        health = build_system_health(user)
        health['url'] = item_url(request, 'newsletter_deliveries') or ''
        if user.is_superuser:
            health['settings_url'] = item_url(request, 'site_settings') or ''
        return health
    return None


def list_context(request, workspace_key):
    if workspace_key == 'kelly' and is_item_visible(request, 'articles'):
        return kelly_articles(request)
    if workspace_key == 'komuniki' and is_item_visible(request, 'messages'):
        return komuniki_messages(request)
    return None


def overview_context(request, workspace_key):
    if workspace_key == 'kelly':
        stats = kelly_stats(request)
        quick_links = kelly_quick_links(request)
        activity = kelly_activity(request)
        section = {
            'title': 'Seus conteúdos',
            'subtitle': 'Acompanhe e organize as notícias do seu portal.',
            'link_label': 'Biblioteca editorial',
            'link_url': item_url(request, 'articles'),
        }
        subtitle = 'Um lugar para acompanhar e gerenciar seu conteúdo.'
    elif workspace_key == 'komuniki':
        stats = komuniki_stats(request)
        quick_links = komuniki_quick_links(request)
        activity = komuniki_activity(request)
        section = {
            'title': 'Mensagens recebidas',
            'subtitle': 'Fila de atendimento do formulário de contato da Komuniki.',
            'link_label': 'Todas as mensagens',
            'link_url': item_url(request, 'messages'),
        }
        subtitle = 'Acompanhe mensagens, a home e as redes da Komuniki.'
    else:
        stats, quick_links, activity = [], [], []
        section = None
        subtitle = 'Suas ferramentas administrativas em um só lugar.'

    quick_links = quick_links + _guide_links(request, workspace_key)
    return {
        'subtitle': subtitle,
        'stats': stats,
        'section': section,
        'quick_links': quick_links[:6],
        'activity': activity,
        'primary_action': _primary_action(request, workspace_key),
        'system_health': _system_health(request, workspace_key),
    }
