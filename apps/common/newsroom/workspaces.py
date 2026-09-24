"""Espaços de trabalho do painel: Blog da Kelly e Komuniki.

Os dois portais compartilham o mesmo ``Site`` (SITE_ID = 1) e se separam por
aplicação — ``apps.news`` é o Blog da Kelly, ``apps.school``/``apps.contact``/
``apps.social`` são a Komuniki. O espaço de trabalho é, portanto, um recorte da
navegação e da visão geral: escolhe quais ferramentas, indicadores e atividades
aparecem. Não é autorização — cada tela continua checando a própria permissão.

A escolha fica na sessão. Um espaço só é oferecido a quem enxerga pelo menos
uma ferramenta dele.
"""

from dataclasses import dataclass

from django.conf import settings

from apps.common.newsroom.branding import get_workspace_config

KELLY = 'kelly'
KOMUNIKI = 'komuniki'
ORDER = (KELLY, KOMUNIKI)
SESSION_KEY = 'newsroom_workspace'


@dataclass(frozen=True)
class Workspace:
    key: str
    label: str
    initial: str
    tone: str
    public_url: str


def get_workspace(key):
    config = get_workspace_config().get(key)
    if config is None:
        return None
    return Workspace(
        key=key,
        label=config['label'],
        initial=config['initial'],
        tone=config['tone'],
        public_url=getattr(settings, config.get('public_url_setting', ''), '') or '',
    )


def all_workspaces():
    return [get_workspace(key) for key in ORDER]
