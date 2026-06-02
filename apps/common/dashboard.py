from datetime import timedelta

from django.conf import settings
from django.utils import timezone


def _get_setting(name, default=''):
    value = getattr(settings, name, default)
    if value is None:
        return ''
    return str(value)


def _get_email_status():
    email_backend = _get_setting('EMAIL_BACKEND')
    email_host = _get_setting('EMAIL_HOST')
    email_host_user = _get_setting('EMAIL_HOST_USER')
    email_host_password = _get_setting('EMAIL_HOST_PASSWORD')
    default_from_email = _get_setting('DEFAULT_FROM_EMAIL')

    missing = []
    if email_backend != 'django.core.mail.backends.smtp.EmailBackend':
        missing.append('EMAIL_BACKEND SMTP')
    if not email_host or email_host == 'localhost':
        missing.append('EMAIL_HOST')
    if not email_host_user:
        missing.append('EMAIL_HOST_USER')
    if not email_host_password:
        missing.append('EMAIL_HOST_PASSWORD')
    if not default_from_email or default_from_email == 'noreply@localhost':
        missing.append('DEFAULT_FROM_EMAIL')

    backend_parts = email_backend.split('.')
    email_backend_label = '.'.join(backend_parts[-2:]) if len(backend_parts) >= 2 else email_backend

    return {
        'email_backend': email_backend_label if email_backend else 'Não configurado',
        'email_host': email_host if email_host and email_host != 'localhost' else 'Não configurado',
        'email_port': _get_setting('EMAIL_PORT', '587'),
        'smtp_configured': not missing,
        'email_missing_settings': ', '.join(missing),
    }


def dashboard_callback(request, context):
    """Enriquece o contexto do admin index com stats dos portais."""
    from apps.common.models import SiteExtension
    from apps.contact.models import ContactInquiry
    from apps.hiring.models import Application, JobPosting
    from apps.news.models import Article, Comment, NewsletterDelivery, NewsletterSubscription

    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (start_of_month - timedelta(days=1)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    last_draft = (
        Article.objects.filter(status=Article.Status.DRAFT)
        .order_by('-updated_at').first()
    )
    email_status = _get_email_status()
    configured_sender_sites = SiteExtension.objects.exclude(
        newsletter_from_email=''
    ).count()
    newsletter_config_ready = email_status['smtp_configured'] and configured_sender_sites > 0
    if not email_status['smtp_configured']:
        newsletter_config_hint = 'Ajuste as variáveis EMAIL_* no .env.prod do servidor.'
    elif not configured_sender_sites:
        newsletter_config_hint = 'Defina o remetente em Configurações dos Sites.'
    else:
        newsletter_config_hint = 'SMTP e remetente por site prontos para envio.'

    context.update({
        # ── Portal Escolar ──
        'open_jobs': JobPosting.objects.filter(status='open').count(),
        'pending_applications': Application.objects.filter(
            status=Application.Status.RECEIVED).count(),
        'unread_messages': ContactInquiry.objects.filter(status='new').count(),

        # ── Portal de Notícias ──
        'published_articles': Article.objects.filter(
            status=Article.Status.PUBLISHED).count(),
        'draft_articles': Article.objects.filter(
            status=Article.Status.DRAFT).count(),
        'newsletter_subscribers': NewsletterSubscription.objects.filter(
            is_active=True).count(),
        'pending_comments': Comment.objects.filter(is_active=False).count(),
        'newsletter_pending_deliveries': NewsletterDelivery.objects.filter(
            status=NewsletterDelivery.Status.PENDING).count(),
        'newsletter_failed_deliveries': NewsletterDelivery.objects.filter(
            status=NewsletterDelivery.Status.FAILED).count(),
        'newsletter_sent_today': NewsletterDelivery.objects.filter(
            status=NewsletterDelivery.Status.SENT,
            sent_at__gte=start_of_today).count(),
        'newsletter_articles_pending': Article.objects.filter(
            status=Article.Status.PUBLISHED,
            newsletter_sent_at__isnull=True).count(),
        'newsletter_config_ready': newsletter_config_ready,
        'newsletter_config_hint': newsletter_config_hint,
        'newsletter_sender_sites': configured_sender_sites,
        **email_status,

        # ── Tendências ──
        'articles_this_month': Article.objects.filter(
            status=Article.Status.PUBLISHED,
            published_at__gte=start_of_month).count(),
        'articles_last_month': Article.objects.filter(
            status=Article.Status.PUBLISHED,
            published_at__gte=last_month_start,
            published_at__lt=start_of_month).count(),
        'newsletter_today': NewsletterSubscription.objects.filter(
            is_active=True, created_at__gte=start_of_today).count(),
        'last_draft_updated': last_draft.updated_at if last_draft else None,

        # ── Tabelas de atividade ──
        'recent_articles': (
            Article.objects.select_related('author', 'category')
            .order_by('-updated_at')[:5]
        ),
        'recent_applications': (
            Application.objects.select_related('job')
            .order_by('-created_at')[:5]
        ),
        'recent_messages': (
            ContactInquiry.objects.order_by('-created_at')[:5]
        ),
    })
    return context
