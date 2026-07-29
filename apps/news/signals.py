import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from wagtail.signals import published, unpublished

from .models import Article

logger = logging.getLogger(__name__)


@receiver(published, sender=Article)
def sync_article_status_on_wagtail_publish(sender, instance, **kwargs):
    """Publicar via Wagtail (DraftStateMixin) deve refletir no campo `status`,
    que é o único campo que as queries públicas (views, sitemap, feed,
    newsletter) realmente usam para decidir visibilidade — `live` do Wagtail
    é interno ao painel administrativo e não é lido em nenhum lugar do site
    público."""
    if instance.status != Article.Status.PUBLISHED:
        instance.status = Article.Status.PUBLISHED
        instance.save(update_fields=['status', 'published_at'])


@receiver(unpublished, sender=Article)
def sync_article_status_on_wagtail_unpublish(sender, instance, **kwargs):
    """Despublicar via Wagtail deve tirar o artigo do site público — mapeado
    para Status.ARCHIVED ('removido do site'), não DRAFT, porque despublicar
    remove algo que estava ao vivo, não reverte para rascunho em elaboração."""
    if instance.status == Article.Status.PUBLISHED:
        instance.status = Article.Status.ARCHIVED
        instance.save(update_fields=['status'])


@receiver(post_save, sender=Article)
def mark_newsletter_pending_on_publish(sender, instance, **kwargs):
    """
    Publicar um artigo deixa a newsletter pendente.
    O envio real acontece em background via send_pending_newsletters.
    """
    if instance.status != Article.Status.PUBLISHED:
        return

    if instance.newsletter_sent_at is not None:
        return

    logger.info(
        'Newsletter pendente para artigo pk=%s ("%s"). Rode send_pending_newsletters para processar.',
        instance.pk,
        instance.title,
    )
