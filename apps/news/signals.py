import logging

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse
from wagtail.contrib.redirects.models import Redirect
from wagtail.signals import published, unpublished

from .models import Article

logger = logging.getLogger(__name__)


@receiver(published, sender=Article)
def sync_article_status_on_wagtail_publish(sender, instance, **kwargs):
    """Publicar via Wagtail (DraftStateMixin) deve refletir no campo `status`,
    que é o único campo que as queries públicas (views, sitemap, feed,
    newsletter) realmente usam para decidir visibilidade — `live` do Wagtail
    é interno ao painel administrativo e não é lido em nenhum lugar do site
    público.

    O Wagtail 7.4 manda `published` também ao AGENDAR ("Agendar publicação":
    PublishRevisionAction._after_publish roda mesmo com go_live_at no futuro),
    com a notícia ainda fora do ar. Marcar `status` nesse momento punha a
    notícia agendada no site (e na fila da newsletter) antes da hora. Só conta
    quando ela entra no ar de fato; na hora marcada, o `publish_scheduled`
    publica a revisão e o sinal chega de novo, já com `live=True`."""
    if not instance.live:
        return
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


# Estados em que o endereço da notícia já foi público: publicada, ou retirada
# do ar depois de publicada. Rascunho nunca teve endereço público.
_PUBLIC_STATUSES = (Article.Status.PUBLISHED, Article.Status.ARCHIVED)


def _article_path(slug):
    return reverse('news:article_detail', kwargs={'slug': slug})


def redirect_article_path(old_path, new_path):
    """301 de ``old_path`` para ``new_path``, sem cadeias nem laços.

    * redirecionamentos que levavam ao endereço antigo passam a levar direto
      ao novo (a -> b -> c vira a -> c e b -> c);
    * um redirecionamento automático que partia do NOVO endereço é removido —
      o endereço voltou a ser de uma notícia (trocar b de volta para a).
    """
    old_key = Redirect.normalise_path(old_path)
    new_key = Redirect.normalise_path(new_path)
    if old_key == new_key:
        return
    with transaction.atomic():
        Redirect.objects.filter(old_path=new_key, automatically_created=True).delete()
        Redirect.objects.filter(redirect_link=old_path).update(redirect_link=new_path)
        Redirect.objects.update_or_create(
            old_path=old_key, site=None,
            defaults={
                'redirect_link': new_path,
                'redirect_page': None,
                'is_permanent': True,
                'automatically_created': True,
            },
        )


@receiver(pre_save, sender=Article)
def remember_public_path_before_slug_change(sender, instance, raw=False, update_fields=None, **kwargs):
    """Guarda o endereço antigo quando o slug de uma notícia já pública muda.

    Numa notícia no ar, editar só gera revisão: a linha (e o slug público) só
    muda quando a revisão é PUBLICADA — é nesse save que o redirecionamento
    nasce, nunca num rascunho.
    """
    instance._previous_public_path = None
    if raw or instance.pk is None:
        return
    if update_fields is not None and 'slug' not in update_fields:
        return
    previous = sender._base_manager.filter(pk=instance.pk).values('slug', 'status').first()
    if previous and previous['status'] in _PUBLIC_STATUSES and previous['slug'] != instance.slug:
        instance._previous_public_path = _article_path(previous['slug'])


@receiver(post_save, sender=Article)
def redirect_old_public_path(sender, instance, raw=False, **kwargs):
    old_path = getattr(instance, '_previous_public_path', None)
    instance._previous_public_path = None
    if raw or not old_path:
        return
    new_path = instance.get_absolute_url()
    redirect_article_path(old_path, new_path)
    logger.info('Endereço da notícia pk=%s mudou: %s agora redireciona para %s.', instance.pk, old_path, new_path)
