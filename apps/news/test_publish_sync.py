"""Publicar e despublicar pelo Wagtail sincroniza o status da notícia e dispara a newsletter pendente."""

import pytest
from django.utils import timezone

from apps.news.models import Article
from apps.news.testing import make_article_full, make_site

# ── Wagtail publish/unpublish → status sync ──────────────────────────────────


@pytest.mark.django_db
def test_wagtail_publish_syncs_status_to_published():
    """Publicar via Wagtail (save_revision().publish()) atualiza status para PUBLISHED."""
    site = make_site()
    art = make_article_full(site, slug='wagtail-pub-sync', status=Article.Status.DRAFT)

    rev = art.save_revision()
    rev.publish()

    art.refresh_from_db()
    assert art.status == Article.Status.PUBLISHED
    assert art.published_at is not None


@pytest.mark.django_db
def test_wagtail_unpublish_syncs_status_to_archived():
    """Despublicar via Wagtail (.unpublish()) atualiza status para ARCHIVED."""
    site = make_site()
    art = make_article_full(site, slug='wagtail-unpub-sync', status=Article.Status.PUBLISHED)
    art.published_at = timezone.now()
    art.save()

    # Publicar via Wagtail para garantir live=True
    rev = art.save_revision()
    rev.publish()
    art.refresh_from_db()
    assert art.live is True
    assert art.status == Article.Status.PUBLISHED

    # Despublicar
    art.unpublish()
    art.refresh_from_db()

    assert art.status == Article.Status.ARCHIVED
    assert art.live is False


@pytest.mark.django_db
def test_wagtail_publish_article_appears_in_public_queryset():
    """Artigo publicado via Wagtail aparece em on_site.filter(status=PUBLISHED)."""
    site = make_site(pk=1, domain='testserver')
    art = make_article_full(site, slug='wagtail-pub-queryset', status=Article.Status.DRAFT)

    # Antes de publicar, NÃO deve aparecer no queryset público
    qs = Article.on_site.filter(status=Article.Status.PUBLISHED)
    assert art not in qs

    # Publica via Wagtail
    rev = art.save_revision()
    rev.publish()
    art.refresh_from_db()

    # Agora DEVE aparecer
    qs = Article.on_site.filter(status=Article.Status.PUBLISHED)
    assert art in qs


@pytest.mark.django_db
def test_wagtail_unpublish_article_disappears_from_public_queryset():
    """Artigo despublicado via Wagtail some de on_site.filter(status=PUBLISHED)."""
    site = make_site(pk=1, domain='testserver')
    art = make_article_full(site, slug='wagtail-unpub-queryset', status=Article.Status.PUBLISHED)
    art.published_at = timezone.now()
    art.save()

    # Publica via Wagtail para garantir que aparece no queryset público
    rev = art.save_revision()
    rev.publish()
    art.refresh_from_db()

    qs = Article.on_site.filter(status=Article.Status.PUBLISHED)
    assert art in qs

    # Despublica
    art.unpublish()
    art.refresh_from_db()

    qs = Article.on_site.filter(status=Article.Status.PUBLISHED)
    assert art not in qs


@pytest.mark.django_db
def test_wagtail_publish_triggers_newsletter_pending(caplog):
    """Publicar via Wagtail dispara o log de newsletter pendente via post_save."""
    import logging

    site = make_site()
    art = make_article_full(site, slug='wagtail-pub-newsletter', status=Article.Status.DRAFT)

    # Configura logging para capturar a mensagem do mark_newsletter_pending_on_publish
    with caplog.at_level(logging.INFO, logger='apps.news.signals'):
        rev = art.save_revision()
        rev.publish()
        art.refresh_from_db()

    assert art.status == Article.Status.PUBLISHED
    # A mensagem de newsletter pendente deve ter sido logada
    assert any(
        'Newsletter pendente para artigo' in record.message
        for record in caplog.records
    ), 'mark_newsletter_pending_on_publish deveria ter logado após publish via Wagtail'


@pytest.mark.django_db
def test_wagtail_publish_idempotent_status_already_published():
    """Se status já é PUBLISHED, o receiver de published não faz save extra desnecessário."""
    site = make_site()
    art = make_article_full(site, slug='wagtail-pub-idempotent', status=Article.Status.PUBLISHED)
    art.published_at = timezone.now()
    art.save()

    original_published_at = art.published_at

    rev = art.save_revision()
    rev.publish()
    art.refresh_from_db()

    # Status continua PUBLISHED, published_at não foi sobrescrito para now()
    assert art.status == Article.Status.PUBLISHED
    assert art.published_at == original_published_at


@pytest.mark.django_db
def test_wagtail_unpublish_idempotent_status_already_not_published():
    """Se status já não é PUBLISHED, o receiver de unpublished não faz nada."""
    site = make_site()
    art = make_article_full(site, slug='wagtail-unpub-idempotent', status=Article.Status.ARCHIVED)
    art.save()

    # Precisamos garantir live=True para que unpublish() funcione
    art.live = True
    art.save()

    art.unpublish()
    art.refresh_from_db()

    # Status continua ARCHIVED (não era PUBLISHED, então o receiver não agiu)
    assert art.status == Article.Status.ARCHIVED


@pytest.mark.django_db
def test_wagtail_publish_changes_nothing_when_already_published():
    """Publicar um artigo repetidamente via Wagtail mantém status e published_at."""
    site = make_site()
    art = make_article_full(site, slug='wagtail-repub', status=Article.Status.PUBLISHED)
    art.published_at = timezone.now()
    art.save()

    original_published_at = art.published_at

    # Primeira publicação
    rev = art.save_revision()
    rev.publish()
    art.refresh_from_db()
    first_published_at = art.published_at

    assert art.status == Article.Status.PUBLISHED

    # Segunda publicação (nova revisão)
    rev2 = art.save_revision()
    rev2.publish()
    art.refresh_from_db()

    assert art.status == Article.Status.PUBLISHED
    # published_at não é sobrescrito pois status já era PUBLISHED
    assert art.published_at == original_published_at
    assert first_published_at == original_published_at
    assert art.published_at == first_published_at
