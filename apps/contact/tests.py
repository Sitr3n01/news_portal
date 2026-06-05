import pytest
from django.urls import reverse

from apps.common import turnstile

from .models import ContactInquiry


def mock_turnstile(monkeypatch, *, valid=True):
    monkeypatch.setattr(turnstile, 'verify_turnstile', lambda token, remote_ip='': valid and token == 'valid-token')


@pytest.mark.django_db
def test_contact_page_get(client):
    url = reverse('contact:page')
    response = client.get(url)
    assert response.status_code == 200
    assert 'text/html' in response['Content-Type']


@pytest.mark.django_db
def test_contact_page_post(client, monkeypatch):
    url = reverse('contact:page')
    mock_turnstile(monkeypatch)
    data = {
        'name': 'Test User',
        'email': 'test@example.com',
        'phone': '11999999999',
        'subject': 'general',
        'message': 'This is a test message.',
        'cf-turnstile-response': 'valid-token',
    }
    response = client.post(url, data)
    assert response.status_code == 302 # redirect on success
    assert ContactInquiry.objects.count() == 1
    assert ContactInquiry.objects.first().name == 'Test User'


@pytest.mark.django_db
def test_contact_page_rejects_invalid_turnstile(client, monkeypatch):
    url = reverse('contact:page')
    mock_turnstile(monkeypatch, valid=False)
    data = {
        'name': 'Test User',
        'email': 'test@example.com',
        'phone': '11999999999',
        'subject': 'general',
        'message': 'This is a test message.',
        'cf-turnstile-response': 'bad-token',
    }

    response = client.post(url, data)

    assert response.status_code == 200
    assert ContactInquiry.objects.count() == 0
    assert 'Confirme a verificação anti-bot' in response.content.decode()


@pytest.mark.django_db
def test_contact_page_rejects_missing_turnstile(client, monkeypatch):
    url = reverse('contact:page')
    mock_turnstile(monkeypatch, valid=False)

    response = client.post(url, {
        'name': 'Test User',
        'email': 'test@example.com',
        'phone': '11999999999',
        'subject': 'general',
        'message': 'This is a test message.',
    })

    assert response.status_code == 200
    assert ContactInquiry.objects.count() == 0
