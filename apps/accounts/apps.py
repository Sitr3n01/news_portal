from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Contas'

    def ready(self):
        from . import (
            checks,  # noqa: F401
            signals,  # noqa: F401
        )
