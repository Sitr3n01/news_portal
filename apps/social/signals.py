from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import SocialPost


@receiver(post_delete, sender=SocialPost, dispatch_uid='social.delete_thumbnail_file')
def delete_thumbnail_file(sender, instance, **kwargs):
    """Remove o arquivo de miniatura do disco quando o post é excluído,
    evitando arquivos órfãos no volume de mídia (limite de 50GB da VPS)."""
    thumb = instance.thumbnail_image
    if thumb:
        try:
            thumb.delete(save=False)
        except Exception:
            pass
