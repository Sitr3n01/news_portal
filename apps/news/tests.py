import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_news_article_list(client):
    url = reverse('news:list')
    response = client.get(url)
    assert response.status_code == 200
    assert 'text/html' in response['Content-Type']
