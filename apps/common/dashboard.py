from datetime import timedelta

from django.utils import timezone

from apps.common.admin_nav import (
    MANAGEMENT_PERMISSIONS,
    NEWS_PERMISSIONS,
    SCHOOL_PERMISSIONS,
)
from apps.common.admin_nav import admin_url as _admin_url
from apps.common.admin_nav import can as _can
from apps.common.admin_nav import can_any as _can_any
from apps.common.admin_nav import get_email_status as _get_email_status
from apps.common.admin_nav import visible as _visible

# Aliases mantidos para compatibilidade com os nomes usados no restante do módulo.
SCHOOL_GUIDE_PERMISSIONS = SCHOOL_PERMISSIONS
NEWS_GUIDE_PERMISSIONS = NEWS_PERMISSIONS
MANAGEMENT_GUIDE_PERMISSIONS = MANAGEMENT_PERMISSIONS


def _link(user, title, icon, route_name, permission, query=None, args=None, kind='secondary'):
    if not _can(user, permission):
        return None
    return {
        'title': title,
        'icon': icon,
        'url': _admin_url(route_name, query=query, args=args),
        'kind': kind,
    }


def _metric(user, permission, title, value, icon, route_name, tone='neutral', hint='', query=None):
    if not _can(user, permission):
        return None
    return {
        'title': title,
        'value': value,
        'icon': icon,
        'url': _admin_url(route_name, query=query),
        'tone': tone,
        'hint': hint,
    }


def _system_tone(email_status, newsletter_config_ready, newsletter_failed_deliveries):
    if newsletter_failed_deliveries:
        return 'danger'
    if not email_status['smtp_configured'] or not newsletter_config_ready:
        return 'warning'
    return 'success'


def dashboard_callback(request, context):
    """Enriquece o contexto do admin index com stats dos portais."""
    from apps.common.models import SiteExtension
    from apps.contact.models import ContactInquiry
    from apps.news.models import Article, Comment, NewsletterDelivery, NewsletterSubscription
    from apps.school.models import Page, SchoolFeature, SchoolHomeConfig, Testimonial

    user = request.user
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (start_of_month - timedelta(days=1)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    # Conta apenas o que o usuário tem permissão de ver — evita ~20 COUNTs em todo
    # load do /admin/ para quem não enxerga aquele dado (performance).
    def _count(permission, queryset):
        return queryset.count() if _can(user, permission) else 0

    unread_messages = _count(
        'contact.view_contactinquiry',
        ContactInquiry.objects.filter(status=ContactInquiry.Status.NEW),
    )
    home_configs = _count(
        'school.view_schoolhomeconfig',
        SchoolHomeConfig.objects.filter(is_active=True),
    )
    published_courses = _count(
        'school.view_page',
        Page.objects.filter(slug='cursos', is_published=True),
    )
    active_features = _count(
        'school.view_schoolfeature',
        SchoolFeature.objects.filter(
            is_active=True,
            placement__in=[SchoolFeature.Placement.TRUST, SchoolFeature.Placement.LIFE],
        ),
    )
    featured_testimonials = _count(
        'school.view_testimonial',
        Testimonial.objects.filter(is_featured=True),
    )

    published_articles = _count(
        'news.view_article',
        Article.objects.filter(status=Article.Status.PUBLISHED),
    )
    draft_articles = _count(
        'news.view_article',
        Article.objects.filter(status=Article.Status.DRAFT),
    )
    articles_this_month = _count(
        'news.view_article',
        Article.objects.filter(status=Article.Status.PUBLISHED, published_at__gte=start_of_month),
    )
    articles_last_month = _count(
        'news.view_article',
        Article.objects.filter(
            status=Article.Status.PUBLISHED,
            published_at__gte=last_month_start,
            published_at__lt=start_of_month,
        ),
    )
    newsletter_subscribers = _count(
        'news.view_newslettersubscription',
        NewsletterSubscription.objects.filter(is_active=True),
    )
    newsletter_today = _count(
        'news.view_newslettersubscription',
        NewsletterSubscription.objects.filter(is_active=True, created_at__gte=start_of_today),
    )
    pending_comments = _count(
        'news.view_comment',
        Comment.objects.filter(is_active=False),
    )
    newsletter_sent_today = _count(
        'news.view_newsletterdelivery',
        NewsletterDelivery.objects.filter(
            status=NewsletterDelivery.Status.SENT,
            sent_at__gte=start_of_today,
        ),
    )
    newsletter_articles_pending = _count(
        'news.view_article',
        Article.objects.filter(status=Article.Status.PUBLISHED, newsletter_sent_at__isnull=True),
    )
    last_draft = (
        Article.objects.filter(status=Article.Status.DRAFT).order_by('-updated_at').first()
        if _can(user, 'news.view_article')
        else None
    )

    # Sempre necessários: alimentam o card "Saúde do sistema", que não tem gate de
    # permissão no template (visível para qualquer staff).
    email_status = _get_email_status()
    configured_sender_sites = SiteExtension.objects.exclude(newsletter_from_email='').count()
    newsletter_pending_deliveries = NewsletterDelivery.objects.filter(
        status=NewsletterDelivery.Status.PENDING,
    ).count()
    newsletter_failed_deliveries = NewsletterDelivery.objects.filter(
        status=NewsletterDelivery.Status.FAILED,
    ).count()

    # Tendência mês a mês (reaproveita dados já calculados; antes só "X este mês").
    articles_delta = articles_this_month - articles_last_month
    if articles_delta > 0:
        articles_published_hint = f'{articles_this_month} este mês · ▲{articles_delta} vs. anterior'
    elif articles_delta < 0:
        articles_published_hint = f'{articles_this_month} este mês · ▼{abs(articles_delta)} vs. anterior'
    else:
        articles_published_hint = f'{articles_this_month} este mês · estável'
    newsletter_config_ready = email_status['smtp_configured'] and configured_sender_sites > 0
    if not email_status['smtp_configured']:
        newsletter_config_hint = 'Configure o servidor de e-mail para liberar envios automáticos.'
    elif not configured_sender_sites:
        newsletter_config_hint = 'Defina um remetente de newsletter nas configurações dos sites.'
    else:
        newsletter_config_hint = 'Envio de e-mails e remetentes estão prontos.'

    attention_cards = _visible([
        _metric(
            user,
            'contact.view_contactinquiry',
            'Mensagens novas',
            unread_messages,
            'mail',
            'admin:contact_contactinquiry_changelist',
            tone='warning' if unread_messages else 'neutral',
            hint='Requer resposta' if unread_messages else 'Tudo em dia',
            query={'status__exact': ContactInquiry.Status.NEW},
        ),
        _metric(
            user,
            'news.view_comment',
            'Comentários para revisar',
            pending_comments,
            'rate_review',
            'admin:news_comment_changelist',
            tone='warning' if pending_comments else 'neutral',
            hint='Requer moderação' if pending_comments else 'Tudo em dia',
            query={'is_active__exact': '0'},
        ),
        _metric(
            user,
            'news.view_newsletterdelivery',
            'Falhas de envio',
            newsletter_failed_deliveries,
            'error',
            'admin:news_newsletterdelivery_changelist',
            tone='danger' if newsletter_failed_deliveries else 'neutral',
            hint='Revisar envio' if newsletter_failed_deliveries else 'Sem falhas abertas',
            query={'status__exact': NewsletterDelivery.Status.FAILED},
        ),
    ])
    # Triagem: manter só cards com pendência real (> 0). Com tudo zerado a lista
    # fica vazia e o template mostra o empty state "tudo em dia", em vez de repetir
    # números que já aparecem nos cards de portal.
    attention_cards = [card for card in attention_cards if card['value']]

    school_metrics = _visible([
        _metric(
            user,
            'school.view_schoolhomeconfig',
            'Home ativa',
            home_configs,
            'home',
            'admin:school_schoolhomeconfig_changelist',
            tone='success' if home_configs else 'warning',
            hint='Configuração principal',
        ),
        _metric(
            user,
            'school.view_page',
            'Página Cursos',
            published_courses,
            'article',
            'admin:school_page_changelist',
            tone='primary' if published_courses else 'warning',
            hint='Link público da navegação',
        ),
        _metric(
            user,
            'school.view_schoolfeature',
            'Blocos ativos',
            active_features,
            'auto_awesome',
            'admin:school_schoolfeature_changelist',
            tone='primary' if active_features else 'neutral',
            hint='Home Komuniki',
        ),
        _metric(
            user,
            'school.view_testimonial',
            'Depoimentos',
            featured_testimonials,
            'format_quote',
            'admin:school_testimonial_changelist',
            tone='primary' if featured_testimonials else 'neutral',
            hint='Destacados na home',
        ),
        _metric(
            user,
            'contact.view_contactinquiry',
            'Mensagens não lidas',
            unread_messages,
            'mark_email_unread',
            'admin:contact_contactinquiry_changelist',
            tone='warning' if unread_messages else 'neutral',
            hint='Requer resposta' if unread_messages else 'Tudo em dia',
            query={'status__exact': ContactInquiry.Status.NEW},
        ),
    ])

    news_metrics = _visible([
        _metric(
            user,
            'news.view_article',
            'Artigos publicados',
            published_articles,
            'check_circle',
            'admin:news_article_changelist',
            tone='primary',
            hint=articles_published_hint,
            query={'status__exact': Article.Status.PUBLISHED},
        ),
        _metric(
            user,
            'news.view_article',
            'Artigos em rascunho',
            draft_articles,
            'edit_note',
            'admin:news_article_changelist',
            tone='warning' if draft_articles else 'neutral',
            hint='Editado recentemente' if last_draft else 'Sem rascunhos',
            query={'status__exact': Article.Status.DRAFT},
        ),
        _metric(
            user,
            'news.view_comment',
            'Comentários pendentes',
            pending_comments,
            'forum',
            'admin:news_comment_changelist',
            tone='warning' if pending_comments else 'neutral',
            hint='Requer moderação' if pending_comments else 'Tudo em dia',
            query={'is_active__exact': '0'},
        ),
        _metric(
            user,
            'news.view_newslettersubscription',
            'Assinantes ativos',
            newsletter_subscribers,
            'group',
            'admin:news_newslettersubscription_changelist',
            tone='primary',
            hint=f'{newsletter_today} hoje',
            query={'is_active__exact': '1'},
        ),
        _metric(
            user,
            'news.view_article',
            'Aguardando newsletter',
            newsletter_articles_pending,
            'outbox',
            'admin:news_article_changelist',
            tone='warning' if newsletter_articles_pending else 'neutral',
            hint='Prontos para envio' if newsletter_articles_pending else 'Tudo enviado',
            query={'newsletter': 'pending'},
        ),
        _metric(
            user,
            'news.view_newsletterdelivery',
            'Enviadas hoje',
            newsletter_sent_today,
            'mark_email_read',
            'admin:news_newsletterdelivery_changelist',
            tone='success' if newsletter_sent_today else 'neutral',
            hint='Entregas processadas',
            query={'status__exact': NewsletterDelivery.Status.SENT},
        ),
    ])

    dashboard_actions = _visible([
        _link(
            user,
            'Novo artigo',
            'edit_square',
            'admin:news_article_add',
            'news.add_article',
            kind='primary',
        ),
        _link(
            user,
            'Mensagens',
            'mail',
            'admin:contact_contactinquiry_changelist',
            'contact.view_contactinquiry',
            query={'status__exact': ContactInquiry.Status.NEW},
        ),
    ])

    school_links = _visible([
        _link(user, 'Página Cursos', 'article', 'admin:school_page_changelist', 'school.view_page'),
        _link(user, 'Home Komuniki', 'home', 'admin:school_schoolhomeconfig_changelist', 'school.view_schoolhomeconfig'),
        _link(user, 'Blocos da Home', 'auto_awesome', 'admin:school_schoolfeature_changelist', 'school.view_schoolfeature'),
        _link(user, 'Depoimentos', 'format_quote', 'admin:school_testimonial_changelist', 'school.view_testimonial'),
        _link(user, 'Mensagens', 'contact_mail', 'admin:contact_contactinquiry_changelist', 'contact.view_contactinquiry'),
    ])

    news_links = _visible([
        _link(user, 'Artigos', 'newspaper', 'admin:news_article_changelist', 'news.view_article'),
        _link(user, 'Categorias', 'category', 'admin:news_category_changelist', 'news.view_category'),
        _link(user, 'Tags', 'label', 'admin:news_tag_changelist', 'news.view_tag'),
        _link(user, 'Comentários', 'chat', 'admin:news_comment_changelist', 'news.view_comment'),
        _link(user, 'Newsletter', 'mail', 'admin:news_newslettersubscription_changelist', 'news.view_newslettersubscription'),
        _link(user, 'Entregas', 'mark_email_read', 'admin:news_newsletterdelivery_changelist', 'news.view_newsletterdelivery'),
    ])

    guide_cards = _visible([
        {
            'title': 'Guia Komuniki',
            'icon': 'school',
            'url': _admin_url('admin_school_guide'),
            'tone': 'primary',
            'hint': 'Home, cursos, blocos, depoimentos e mensagens em um fluxo guiado.',
        } if _can_any(user, SCHOOL_GUIDE_PERMISSIONS) else None,
        {
            'title': 'Guia Editorial',
            'icon': 'newspaper',
            'url': _admin_url('admin_news_guide'),
            'tone': 'success',
            'hint': 'Rascunhos, publicação, newsletter, categorias, tags e moderação sem quebra de contexto.',
        } if _can_any(user, NEWS_GUIDE_PERMISSIONS) else None,
        {
            'title': 'Guia de Gerenciamento',
            'icon': 'admin_panel_settings',
            'url': _admin_url('admin_management_guide'),
            'tone': 'warning',
            'hint': 'Usuários, permissões, sites, mídia, remetentes e saúde do sistema com linguagem operacional.',
        } if _can_any(user, MANAGEMENT_GUIDE_PERMISSIONS) else None,
    ])

    recent_articles = []
    if _can(user, 'news.view_article'):
        recent_articles = [
            {
                'title': article.title,
                'meta': f'{article.get_status_display()} · {article.category.name if article.category else "Sem categoria"} · {article.site.name}',
                'status': article.get_status_display(),
                'when': article.updated_at,
                'url': _admin_url('admin:news_article_change', args=[article.pk]),
                'action': 'Editar',
            }
            for article in Article.objects.select_related('author', 'category', 'site').order_by('-updated_at')[:5]
        ]

    recent_messages = []
    if _can(user, 'contact.view_contactinquiry'):
        recent_messages = [
            {
                'title': message.name,
                'meta': f'{message.get_subject_display()} · {message.site.name}',
                'status': message.get_status_display(),
                'when': message.created_at,
                'url': _admin_url('admin:contact_contactinquiry_change', args=[message.pk]),
                'action': 'Responder',
            }
            for message in ContactInquiry.objects.select_related('site').order_by('-created_at')[:5]
        ]

    activity_cards = _visible([
        {
            'title': 'Últimos artigos',
            'icon': 'newspaper',
            'url': _admin_url('admin:news_article_changelist'),
            'items': recent_articles,
            'empty': 'Nenhum artigo recente',
        } if _can(user, 'news.view_article') else None,
        {
            'title': 'Últimas mensagens',
            'icon': 'mail',
            'url': _admin_url('admin:contact_contactinquiry_changelist'),
            'items': recent_messages,
            'empty': 'Nenhuma mensagem nova',
        } if _can(user, 'contact.view_contactinquiry') else None,
    ])

    system_tone = _system_tone(email_status, newsletter_config_ready, newsletter_failed_deliveries)
    if system_tone == 'danger':
        system_status = 'Falha de envio'
    elif system_tone == 'warning':
        system_status = 'Configuração incompleta'
    else:
        system_status = 'Tudo saudável'

    system_health = {
        'tone': system_tone,
        'status': system_status,
        'hint': newsletter_config_hint,
        'can_view_details': user.is_superuser,
        'url': _admin_url('admin:common_siteextension_changelist') if user.is_superuser else '',
        'metrics': [
            {
                'label': 'Envio de e-mails',
                'value': 'Pronto' if email_status['smtp_configured'] else 'Atenção',
                'tone': 'success' if email_status['smtp_configured'] else 'warning',
            },
            {
                'label': 'Remetentes configurados',
                'value': configured_sender_sites,
                'tone': 'success' if configured_sender_sites else 'warning',
            },
            {
                'label': 'Entregas pendentes',
                'value': newsletter_pending_deliveries,
                'tone': 'warning' if newsletter_pending_deliveries else 'neutral',
            },
            {
                'label': 'Falhas de newsletter',
                'value': newsletter_failed_deliveries,
                'tone': 'danger' if newsletter_failed_deliveries else 'neutral',
            },
        ],
        'details': [
            {'label': 'Servidor de e-mail', 'value': f"{email_status['email_host']}:{email_status['email_port']}"},
            {'label': 'Backend técnico', 'value': email_status['email_backend']},
            {'label': 'Itens técnicos ausentes', 'value': email_status['email_missing_settings'] or 'Nenhum'},
        ],
    }

    context.update({
        'attention_cards': attention_cards,
        'guide_cards': guide_cards,
        'school_metrics': school_metrics,
        'school_links': school_links,
        'news_metrics': news_metrics,
        'news_links': news_links,
        'dashboard_actions': dashboard_actions,
        'activity_cards': activity_cards,
        'system_health': system_health,
    })
    return context
