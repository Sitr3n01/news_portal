import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Article, ArticleBlock

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


@receiver(
    [post_save, post_delete],
    sender=ArticleBlock,
    dispatch_uid='news.rebuild_article_content_cache',
)
def rebuild_article_content_cache(sender, instance, **kwargs):
    """Mantém o cache Article.content sincronizado quando blocos mudam.

    O artigo pode já não existir num cascade-delete; nesse caso, ignora.
    """
    article = Article.objects.filter(pk=instance.article_id).first()
    if article is not None:
        article.rebuild_content_cache()
