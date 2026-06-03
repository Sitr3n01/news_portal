from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .admin_roles import ensure_admin_role_groups


@receiver(post_migrate, dispatch_uid='accounts.ensure_admin_role_groups')
def create_admin_role_groups(sender, **kwargs):
    ensure_admin_role_groups()
