from django.apps import AppConfig


class NewsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.news'
    verbose_name = 'Notícias'

    def ready(self):
        import apps.news.signals  # noqa: F401 — registra sinal de auto-envio de newsletter
