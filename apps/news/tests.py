import pytest
from django.contrib.sites.models import Site
from django.core import mail
from django.core.management import call_command
from django.urls import reverse

from apps.common import turnstile
from apps.news.admin import _csv_safe
from apps.news.models import Article, NewsletterDelivery, NewsletterSubscription
from apps.news.newsletter import make_unsubscribe_token


def make_site(pk=1, domain='testserver', name='Test Site'):
    site, _ = Site.objects.update_or_create(
        id=pk,
        defaults={'domain': domain, 'name': name},
    )
    return site


def make_article(site, slug='artigo', status=Article.Status.PUBLISHED):
    return Article.objects.create(
        title=f'Artigo {slug}',
        slug=slug,
        excerpt='Resumo do artigo',
        content='Conteúdo do artigo para newsletter.',
        site=site,
        status=status,
    )


def mock_turnstile(monkeypatch, *, valid=True):
    monkeypatch.setattr(turnstile, 'verify_turnstile', lambda token, remote_ip='': valid and token == 'valid-token')


@pytest.mark.django_db
def test_news_article_list(client):
    url = reverse('news:list')
    response = client.get(url)
    assert response.status_code == 200
    assert 'text/html' in response['Content-Type']


@pytest.mark.parametrize('payload', ['=cmd', '+1', '-1', '@SUM', '\tx', '\rx'])
def test_csv_safe_neutralizes_formula(payload):
    assert _csv_safe(payload).startswith("'")


def test_csv_safe_leaves_normal_values():
    assert _csv_safe('ana@example.com') == 'ana@example.com'
    assert _csv_safe('') == ''
    assert _csv_safe(None) == ''


@pytest.mark.django_db
def test_newsletter_subscribe_htmx_reactivates_existing_email(client, monkeypatch):
    site = make_site()
    mock_turnstile(monkeypatch)
    NewsletterSubscription.objects.create(
        email='ana@example.com',
        site=site,
        is_active=False,
    )

    response = client.post(
        reverse('news:newsletter_subscribe'),
        {
            'email': 'ana@example.com',
            'cf-turnstile-response': 'valid-token',
        },
        HTTP_HX_REQUEST='true',
    )

    assert response.status_code == 200
    subscription = NewsletterSubscription.objects.get(email='ana@example.com', site=site)
    assert subscription.is_active is True


@pytest.mark.django_db
def test_newsletter_subscribe_rejects_invalid_turnstile(client, monkeypatch):
    make_site()
    mock_turnstile(monkeypatch, valid=False)

    response = client.post(
        reverse('news:newsletter_subscribe'),
        {
            'email': 'ana@example.com',
            'cf-turnstile-response': 'bad-token',
        },
        HTTP_HX_REQUEST='true',
    )

    assert response.status_code == 200
    assert NewsletterSubscription.objects.count() == 0
    assert 'Confirme a verificação anti-bot' in response.content.decode()


@pytest.mark.django_db
def test_newsletter_subscribe_rejects_missing_turnstile(client, monkeypatch):
    make_site()
    mock_turnstile(monkeypatch, valid=False)

    response = client.post(
        reverse('news:newsletter_subscribe'),
        {'email': 'ana@example.com'},
        HTTP_HX_REQUEST='true',
    )

    assert response.status_code == 200
    assert NewsletterSubscription.objects.count() == 0


@pytest.mark.django_db
def test_send_pending_newsletters_sends_only_to_article_site_subscribers():
    site = make_site(pk=1, domain='news.example.com', name='News')
    other_site = make_site(pk=2, domain='school.example.com', name='School')
    NewsletterSubscription.objects.create(email='reader@example.com', site=site, is_active=True)
    NewsletterSubscription.objects.create(email='other@example.com', site=other_site, is_active=True)
    article = make_article(site)

    call_command('send_pending_newsletters')

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ['reader@example.com']
    delivery = NewsletterDelivery.objects.get(article=article)
    assert delivery.status == NewsletterDelivery.Status.SENT
    article.refresh_from_db()
    assert article.newsletter_sent_at is not None


@pytest.mark.django_db
def test_send_pending_newsletters_dry_run_does_not_write_or_send():
    site = make_site()
    NewsletterSubscription.objects.create(email='reader@example.com', site=site, is_active=True)
    article = make_article(site)

    call_command('send_pending_newsletters', dry_run=True)

    assert len(mail.outbox) == 0
    assert NewsletterDelivery.objects.count() == 0
    article.refresh_from_db()
    assert article.newsletter_sent_at is None


@pytest.mark.django_db
def test_send_pending_newsletters_is_idempotent_on_rerun():
    site = make_site()
    NewsletterSubscription.objects.create(email='reader@example.com', site=site, is_active=True)
    article = make_article(site)

    call_command('send_pending_newsletters')
    call_command('send_pending_newsletters')

    assert len(mail.outbox) == 1
    assert NewsletterDelivery.objects.filter(article=article).count() == 1


@pytest.mark.django_db
def test_send_pending_newsletters_records_failure_and_retry(monkeypatch):
    site = make_site()
    NewsletterSubscription.objects.create(email='ok@example.com', site=site, is_active=True)
    NewsletterSubscription.objects.create(email='fail@example.com', site=site, is_active=True)
    article = make_article(site)

    from apps.news import newsletter

    original_send = newsletter.EmailMultiAlternatives.send

    def flaky_send(self, *args, **kwargs):
        if self.to == ['fail@example.com']:
            raise RuntimeError('SMTP indisponível')
        return original_send(self, *args, **kwargs)

    monkeypatch.setattr(newsletter.EmailMultiAlternatives, 'send', flaky_send)

    call_command('send_pending_newsletters')

    assert len(mail.outbox) == 1
    failed = NewsletterDelivery.objects.get(email='fail@example.com')
    assert failed.status == NewsletterDelivery.Status.FAILED
    assert failed.attempts == 1
    article.refresh_from_db()
    assert article.newsletter_sent_at is None

    monkeypatch.setattr(newsletter.EmailMultiAlternatives, 'send', original_send)
    call_command('send_pending_newsletters', retry_failed=True)

    failed.refresh_from_db()
    article.refresh_from_db()
    assert failed.status == NewsletterDelivery.Status.SENT
    assert failed.attempts == 2
    assert article.newsletter_sent_at is not None
    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_newsletter_unsubscribe_token_deactivates_subscription(client):
    site = make_site()
    subscription = NewsletterSubscription.objects.create(
        email='reader@example.com',
        site=site,
        is_active=True,
    )
    token = make_unsubscribe_token(subscription)

    response = client.get(reverse('news:newsletter_unsubscribe', args=[token]))

    assert response.status_code == 302
    subscription.refresh_from_db()
    assert subscription.is_active is False


@pytest.mark.django_db
def test_newsletter_unsubscribe_rejects_invalid_token(client):
    site = make_site()
    subscription = NewsletterSubscription.objects.create(
        email='reader@example.com',
        site=site,
        is_active=True,
    )

    response = client.get(reverse('news:newsletter_unsubscribe', args=['token-invalido']))

    assert response.status_code == 302
    subscription.refresh_from_db()
    assert subscription.is_active is True


@pytest.mark.django_db
def test_send_pending_newsletters_ignores_unpublished_articles():
    site = make_site()
    NewsletterSubscription.objects.create(email='reader@example.com', site=site, is_active=True)
    make_article(site, slug='draft', status=Article.Status.DRAFT)
    make_article(site, slug='archived', status=Article.Status.ARCHIVED)

    call_command('send_pending_newsletters')

    assert len(mail.outbox) == 0
    assert NewsletterDelivery.objects.count() == 0
