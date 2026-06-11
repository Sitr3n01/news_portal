from django.contrib.sites.models import Site
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import SiteExtension


@receiver(
    [post_save, post_delete], sender=SiteExtension,
    dispatch_uid='common.clear_site_cache_on_extension_change',
)
def clear_site_cache_on_extension_change(sender, **kwargs):
    """Invalida o cache do framework de Sites quando a SiteExtension muda.

    O Django cacheia o Site no processo e o acessor reverso `site.extension` fica
    preso à instância cacheada. Sem limpar, mudanças de configuração (ex.: ligar/
    desligar a seção de redes na home) só apareceriam no front após reiniciar o
    processo. Limpando o cache, a próxima requisição relê a extensão atualizada.
    """
    Site.objects.clear_cache()
