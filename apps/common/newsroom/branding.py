"""Identidade visual do painel, configurável por ``settings.NEWSROOM``.

Nenhum template escreve o nome do produto à mão: todos leem daqui. Para trocar
a marca, sobrescreva as chaves em ``settings.NEWSROOM`` — as ausentes caem nos
padrões abaixo.
"""

from django.conf import settings

DEFAULT_BRANDING = {
    # "news" + "room" aparecem juntos no logotipo; o sufixo vem em cinza.
    'NAME': 'news',
    'NAME_SUFFIX': 'room',
    # Texto dentro do quadrado preto do logotipo.
    'MARK': 'n.',
    # Nome por extenso, usado no <title> das páginas.
    'PRODUCT_NAME': 'Newsroom',
}

DEFAULT_WORKSPACES = {
    'kelly': {
        'label': 'Blog da Kelly',
        'initial': 'K',
        'tone': 'blue',
        'public_url_setting': 'KELLY_BLOG_PUBLIC_URL',
    },
    'komuniki': {
        'label': 'Komuniki',
        'initial': 'Ko',
        'tone': 'green',
        'public_url_setting': 'KOMUNIKI_PUBLIC_URL',
    },
}


def _config():
    return getattr(settings, 'NEWSROOM', {}) or {}


def get_branding():
    branding = dict(DEFAULT_BRANDING)
    branding.update(_config().get('BRANDING', {}))
    return branding


def get_workspace_config():
    configured = _config().get('WORKSPACES', {})
    merged = {}
    for key, defaults in DEFAULT_WORKSPACES.items():
        merged[key] = {**defaults, **configured.get(key, {})}
    return merged
