import pytest
from django.urls import reverse

from apps.news.admin import _csv_safe


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
