import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_hiring_job_list(client):
    url = reverse('hiring:list')
    response = client.get(url)
    assert response.status_code == 200
    assert 'text/html' in response['Content-Type']
