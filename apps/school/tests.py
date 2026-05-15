import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_school_homepage(client):
    url = reverse('school:home')
    response = client.get(url)
    assert response.status_code == 200
    assert 'text/html' in response['Content-Type']

@pytest.mark.django_db
def test_school_team_list(client):
    url = reverse('school:team_list')
    response = client.get(url)
    assert response.status_code == 200
    assert 'text/html' in response['Content-Type']
