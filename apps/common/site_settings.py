from .models import SiteExtension


def get_site_settings(site):
    """SiteExtension do site, lida do banco a cada chamada; None sem site ou sem configuração.

    Não use `site.extension`: o Django guarda o Site em cache no processo, e o acessor reverso fica preso a essa
    instância. Com vários workers do gunicorn, uma edição salva em um deles não chegava aos outros até cada um ser
    reciclado, e uma migração de dados não chegava a nenhum.
    """
    # RequestSite (sem o app de Sites) não tem pk nem configuração
    if getattr(site, 'pk', None) is None:
        return None
    return SiteExtension.objects.filter(site=site).first()
