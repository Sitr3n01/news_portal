import logging

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.db.models import F
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from .models import Article, NewsletterDelivery, NewsletterSubscription

logger = logging.getLogger(__name__)

UNSUBSCRIBE_TOKEN_SALT = 'apps.news.newsletter.unsubscribe'


def _empty_result():
    return {
        'articles_considered': 0,
        'articles_skipped': 0,
        'articles_marked_sent': 0,
        'subscribers_found': 0,
        'deliveries_created': 0,
        'deliveries_existing': 0,
        'would_create': 0,
        'sent': 0,
        'failed': 0,
        'skipped': 0,
        'would_send': 0,
    }


def _merge_result(target, source):
    for key, value in source.items():
        target[key] = target.get(key, 0) + value
    return target


def make_unsubscribe_token(subscription):
    return signing.dumps(
        {'subscription_id': subscription.pk, 'email': subscription.email},
        salt=UNSUBSCRIBE_TOKEN_SALT,
    )


def get_subscription_from_unsubscribe_token(token):
    try:
        data = signing.loads(token, salt=UNSUBSCRIBE_TOKEN_SALT)
    except signing.BadSignature:
        return None

    return (
        NewsletterSubscription.objects
        .select_related('site')
        .filter(pk=data.get('subscription_id'), email=data.get('email'))
        .first()
    )


def get_newsletter_context(article, site=None, request=None, subscription=None):
    """
    Monta o contexto usado no template de newsletter.
    Preview usa request.get_host(); envio real usa site.domain.
    """
    site = site or article.site

    try:
        site_settings = site.extension
    except AttributeError:
        site_settings = None

    if request is not None:
        protocol = 'https' if request.is_secure() else 'http'
        base_url = f'{protocol}://{request.get_host()}'
    else:
        protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
        base_url = f'{protocol}://{site.domain}'

    if subscription is not None:
        token = make_unsubscribe_token(subscription)
        unsubscribe_url = f'{base_url}{reverse("news:newsletter_unsubscribe", args=[token])}'
    else:
        unsubscribe_url = f'{base_url}/news/account/?tab=settings'

    return {
        'article': article,
        'site': site,
        'site_settings': site_settings,
        'base_url': base_url,
        'article_url': f'{base_url}{article.get_absolute_url()}',
        'unsubscribe_url': unsubscribe_url,
    }


def get_from_email(site_settings):
    """Retorna o remetente da newsletter a partir das configurações do site."""
    if site_settings and site_settings.newsletter_from_email:
        email = site_settings.newsletter_from_email
        name = getattr(site_settings, 'newsletter_from_name', '')
        if name:
            return f'{name} <{email}>'
        return email
    return getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@localhost')


def _mark_article_if_complete(article_id):
    article = Article.objects.filter(pk=article_id, status=Article.Status.PUBLISHED).first()
    if not article or article.newsletter_sent_at is not None:
        return 0

    has_open_deliveries = NewsletterDelivery.objects.filter(
        article=article,
        status__in=[NewsletterDelivery.Status.PENDING, NewsletterDelivery.Status.FAILED],
    ).exists()
    if has_open_deliveries:
        return 0

    Article.objects.filter(pk=article.pk, newsletter_sent_at__isnull=True).update(
        newsletter_sent_at=timezone.now(),
    )
    return 1


def enqueue_article_newsletter(article, *, dry_run=False, include_marked_sent=False):
    """Cria entregas pendentes para os inscritos ativos do site do artigo."""
    result = _empty_result()
    result['articles_considered'] = 1

    if article.status != Article.Status.PUBLISHED:
        result['articles_skipped'] = 1
        return result

    if article.newsletter_sent_at is not None and not include_marked_sent:
        result['articles_skipped'] = 1
        return result

    subscribers = list(
        NewsletterSubscription.objects
        .filter(site=article.site, is_active=True)
        .order_by('created_at')
    )
    result['subscribers_found'] = len(subscribers)

    if not subscribers:
        if dry_run:
            result['would_create'] = 0
        elif article.newsletter_sent_at is None:
            Article.objects.filter(pk=article.pk, newsletter_sent_at__isnull=True).update(
                newsletter_sent_at=timezone.now(),
            )
            result['articles_marked_sent'] = 1
        return result

    for subscription in subscribers:
        if dry_run:
            exists = NewsletterDelivery.objects.filter(article=article, subscription=subscription).exists()
            result['deliveries_existing' if exists else 'would_create'] += 1
            continue

        _, created = NewsletterDelivery.objects.get_or_create(
            article=article,
            subscription=subscription,
            defaults={
                'email': subscription.email,
                'status': NewsletterDelivery.Status.PENDING,
            },
        )
        result['deliveries_created' if created else 'deliveries_existing'] += 1

    return result


def _delivery_queryset(*, retry_failed=False, site_id=None, article_id=None, include_marked_sent=False):
    statuses = [NewsletterDelivery.Status.PENDING]
    if retry_failed:
        statuses.append(NewsletterDelivery.Status.FAILED)

    queryset = (
        NewsletterDelivery.objects
        .select_related('article__site', 'article__author', 'article__category', 'subscription__site')
        .prefetch_related('article__tags')
        .filter(status__in=statuses, article__status=Article.Status.PUBLISHED)
        .order_by('created_at')
    )
    if not include_marked_sent:
        queryset = queryset.filter(article__newsletter_sent_at__isnull=True)
    if site_id:
        queryset = queryset.filter(article__site_id=site_id)
    if article_id:
        queryset = queryset.filter(article_id=article_id)
    return queryset


def send_newsletter_delivery(delivery, *, dry_run=False):
    """Envia uma entrega individual, isolando falhas por destinatário."""
    result = _empty_result()
    article = delivery.article
    subscription = delivery.subscription

    if article.status != Article.Status.PUBLISHED:
        result['skipped'] = 1
        if not dry_run:
            NewsletterDelivery.objects.filter(pk=delivery.pk).update(
                status=NewsletterDelivery.Status.SKIPPED,
                last_error='Artigo não está publicado.',
            )
        return result

    if not subscription.is_active or subscription.site_id != article.site_id:
        result['skipped'] = 1
        if not dry_run:
            NewsletterDelivery.objects.filter(pk=delivery.pk).update(
                status=NewsletterDelivery.Status.SKIPPED,
                email=subscription.email,
                last_error='Assinatura inativa ou pertence a outro site.',
            )
        return result

    if dry_run:
        result['would_send'] = 1
        return result

    context = get_newsletter_context(article, article.site, subscription=subscription)
    subject = f'{article.title} — {article.site.name}'
    html_content = render_to_string('news/email/newsletter_article.html', context)
    text_content = strip_tags(html_content)
    from_email = get_from_email(context.get('site_settings'))

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[subscription.email],
        )
        msg.attach_alternative(html_content, 'text/html')
        msg.send(fail_silently=False)
    except Exception as exc:
        result['failed'] = 1
        NewsletterDelivery.objects.filter(pk=delivery.pk).update(
            status=NewsletterDelivery.Status.FAILED,
            email=subscription.email,
            attempts=F('attempts') + 1,
            last_error=str(exc)[:2000],
        )
        logger.error('Newsletter: falha ao enviar para %s: %s', subscription.email, exc)
        return result

    result['sent'] = 1
    NewsletterDelivery.objects.filter(pk=delivery.pk).update(
        status=NewsletterDelivery.Status.SENT,
        email=subscription.email,
        attempts=F('attempts') + 1,
        last_error='',
        sent_at=timezone.now(),
    )
    return result


def process_pending_newsletters(
    *,
    batch_size=100,
    site_id=None,
    article_id=None,
    retry_failed=False,
    dry_run=False,
    include_marked_sent=False,
):
    """Cria fila pendente e processa entregas em lote."""
    result = _empty_result()

    articles = (
        Article.objects
        .select_related('site')
        .filter(status=Article.Status.PUBLISHED)
        .order_by('published_at', 'created_at')
    )
    if not include_marked_sent:
        articles = articles.filter(newsletter_sent_at__isnull=True)
    if site_id:
        articles = articles.filter(site_id=site_id)
    if article_id:
        articles = articles.filter(pk=article_id)

    article_ids = set()
    for article in articles:
        article_ids.add(article.pk)
        _merge_result(
            result,
            enqueue_article_newsletter(
                article,
                dry_run=dry_run,
                include_marked_sent=include_marked_sent,
            ),
        )

    deliveries = _delivery_queryset(
        retry_failed=retry_failed,
        site_id=site_id,
        article_id=article_id,
        include_marked_sent=include_marked_sent,
    )
    if batch_size:
        deliveries = deliveries[:batch_size]

    processed_article_ids = set()
    for delivery in deliveries:
        processed_article_ids.add(delivery.article_id)
        _merge_result(result, send_newsletter_delivery(delivery, dry_run=dry_run))

    if not dry_run:
        for current_article_id in article_ids | processed_article_ids:
            result['articles_marked_sent'] += _mark_article_if_complete(current_article_id)

    logger.info(
        'Newsletter processada: %d enviado(s), %d falha(s), %d ignorado(s), %d criado(s)',
        result['sent'], result['failed'], result['skipped'], result['deliveries_created'],
    )
    return result


def process_article_newsletter(article, *, retry_failed=False, dry_run=False, include_marked_sent=True):
    return process_pending_newsletters(
        article_id=article.pk,
        retry_failed=retry_failed,
        dry_run=dry_run,
        include_marked_sent=include_marked_sent,
        batch_size=None,
    )


def send_article_newsletter(article, site=None):
    """
    Compatibilidade com chamadas antigas.
    Usa a fila de entregas e retorna o número de e-mails enviados.
    """
    if site is not None and article.site_id != site.pk:
        logger.warning('Newsletter: artigo pk=%s não pertence ao site %s', article.pk, site.pk)
        return 0

    result = process_article_newsletter(article, retry_failed=True, include_marked_sent=True)
    return result['sent']
