"""Prévia de newsletter: permissão de ver notícias + Site atual (IDOR-02).

Antes bastava is_staff: o Administrador Komuniki, sem nenhuma permissão de
notícias, lia qualquer rascunho percorrendo IDs.
"""

import pytest
from django.contrib.sites.models import Site
from django.urls import reverse

from apps.accounts.models import CustomUser
from apps.news.models import Article


def _draft(site, slug='rascunho-previa'):
    return Article.objects.create(
        title='Rascunho da prévia', slug=slug, excerpt='', content='<p>texto</p>', site=site, status=Article.Status.DRAFT,
    )


@pytest.mark.django_db
def test_staff_without_news_permission_is_forbidden(client, make_panel_user, current_site):
    school_admin = make_panel_user('escola_prev', role=CustomUser.Role.SCHOOL_ADMIN, is_staff=True)
    client.force_login(school_admin)

    response = client.get(reverse('news:newsletter_preview', args=[_draft(current_site).pk]))

    assert response.status_code == 403
    assert 'Rascunho da prévia' not in response.content.decode()


@pytest.mark.django_db
def test_reporter_without_staff_can_preview(client, make_panel_user, current_site):
    reporter = make_panel_user('reporter_prev', role=CustomUser.Role.REPORTER)
    client.force_login(reporter)

    response = client.get(reverse('news:newsletter_preview', args=[_draft(current_site).pk]))

    assert response.status_code == 200
    assert 'Rascunho da prévia' in response.content.decode()


@pytest.mark.django_db
def test_preview_is_limited_to_current_site(client, make_panel_user, current_site):
    other = Site.objects.create(domain='outro.example', name='Outro')
    client.force_login(make_panel_user('editor_prev', role=CustomUser.Role.NEWS_EDITOR))

    assert client.get(reverse('news:newsletter_preview', args=[_draft(other, 'de-fora').pk])).status_code == 404


@pytest.mark.django_db
def test_anonymous_goes_to_panel_login(client, current_site):
    response = client.get(reverse('news:newsletter_preview', args=[_draft(current_site).pk]))

    assert response.status_code == 302
    assert response['Location'].startswith(reverse('panel:login'))
