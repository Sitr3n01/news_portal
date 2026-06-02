import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Article

logger = logging.getLogger(__name__)


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
