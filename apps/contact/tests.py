import pytest
from django.urls import reverse

from .models import ContactInquiry


@pytest.mark.django_db
def test_contact_page_get(client):
    url = reverse('contact:page')
    response = client.get(url)
    assert response.status_code == 200
    assert 'text/html' in response['Content-Type']

@pytest.mark.django_db
def test_contact_page_post(client):
    url = reverse('contact:page')
    data = {
        'name': 'Test User',
        'email': 'test@example.com',
        'phone': '11999999999',
        'subject': 'general',
        'message': 'This is a test message.'
    }
    response = client.post(url, data)
    assert response.status_code == 302 # redirect on success
    assert ContactInquiry.objects.count() == 1
    assert ContactInquiry.objects.first().name == 'Test User'
