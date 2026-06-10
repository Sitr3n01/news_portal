from django.db.models.signals import post_delete, post_migrate
from django.dispatch import receiver

from .admin_roles import ensure_admin_role_groups
from .models import CustomUser


@receiver(post_migrate, dispatch_uid='accounts.ensure_admin_role_groups')
def create_admin_role_groups(sender, **kwargs):
    ensure_admin_role_groups()


@receiver(post_delete, sender=CustomUser, dispatch_uid='accounts.delete_avatar_file')
def delete_avatar_file(sender, instance, **kwargs):
    """Remove o arquivo do avatar do disco quando a conta é excluída,
    evitando arquivos órfãos no volume de mídia (limite de 50GB da VPS)."""
    avatar = instance.avatar
    if avatar:
        try:
            avatar.delete(save=False)
        except Exception:
            pass
