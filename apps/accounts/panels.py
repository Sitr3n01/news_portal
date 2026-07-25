"""Fonte única de verdade sobre QUAIS ÁREAS ADMINISTRATIVAS um usuário alcança.

A plataforma tem duas áreas, e o vocabulário aqui é o do usuário final — nunca
"Django", "Wagtail" ou "CMS":

* Publicação de matérias  -> Wagtail  (/cms/)
* Administração do sistema -> Django admin (/admin/)

A tela de login pergunta para onde a pessoa QUER ir; este módulo decide para
onde ela PODE ir. O campo de destino do formulário é conselho, jamais
autorização.

Regra de ouro: os testes de acesso aqui têm de ser byte a byte iguais ao que o
próprio framework aplica na porta. Se divergirem, o login promete um painel que
o painel recusa — e o usuário entra num laço de redirecionamento.

Este módulo importa apenas django.conf/django.urls/django.utils — sem models e
sem apps.common — para poder ser importado de qualquer lugar sem ciclo.
"""

from urllib.parse import urlsplit

from django.conf import settings
from django.shortcuts import resolve_url
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme

PANEL_CMS = 'cms'
PANEL_ADMIN = 'admin'

# Ordem de apresentação e de desempate: publicação vem primeiro porque é o
# fluxo diário da redação; administração é a exceção.
PANEL_ORDER = (PANEL_CMS, PANEL_ADMIN)

PANEL_LABELS = {
    PANEL_CMS: 'Publicação de matérias',
    PANEL_ADMIN: 'Administração do sistema',
}

PANEL_DESCRIPTIONS = {
    PANEL_CMS: 'Escrever, revisar e publicar matérias, com imagens e categorias.',
    PANEL_ADMIN: 'Usuários, permissões, páginas da Komuniki, mensagens e configurações.',
}

# Material Symbols Outlined, já carregado por templates/base_news.html.
PANEL_ICONS = {
    PANEL_CMS: 'edit_note',
    PANEL_ADMIN: 'admin_panel_settings',
}


# ── Portões de acesso ──────────────────────────────────────────────────────
#
# NÃO troque estas checagens por apps.common.admin_nav.can(): aquele helper
# curto-circuita em `user.is_superuser`, que continua True para um superusuário
# INATIVO — enquanto AdminSite.has_permission e ModelBackend.has_perm recusam
# inativos. Usar can() aqui faria o login dizer "você tem os dois painéis",
# redirecionar, o painel recusar e devolver ao login: laço infinito.
#
# admin_nav.can/can_any continua sendo a camada de MOBÍLIA (o que exibir na
# sidebar depois de entrar). Este módulo é a camada de PORTA.

def can_access_admin(user):
    """Espelha django.contrib.admin.AdminSite.has_permission."""
    return bool(user.is_active and user.is_staff)


def can_access_cms(user):
    """Espelha wagtail.admin.auth.require_admin_access.

    Repare que o Wagtail NÃO exige is_staff — só a permissão. Um repórter
    publica sem nunca ser "equipe administrativa" no sentido do Django.
    """
    return bool(user.is_authenticated and user.has_perm('wagtailadmin.access_admin'))


PANEL_ACCESS_TESTS = {
    PANEL_CMS: can_access_cms,
    PANEL_ADMIN: can_access_admin,
}


def available_panels(user):
    """Painéis que este usuário realmente alcança, em PANEL_ORDER."""
    if not getattr(user, 'is_authenticated', False):
        return []
    return [panel for panel in PANEL_ORDER if PANEL_ACCESS_TESTS[panel](user)]


def default_panel(user):
    """O painel óbvio, quando só existe um. None se houver zero ou dois."""
    panels = available_panels(user)
    return panels[0] if len(panels) == 1 else None


# ── URLs dos painéis ───────────────────────────────────────────────────────
#
# Sempre via reverse(): se um dia o CMS sair de /cms/, tudo aqui continua
# correto. Nenhuma string literal de rota neste módulo.

def panel_root(panel):
    """Prefixo da área, sempre com barra final ('/cms/', '/admin/')."""
    name = 'wagtailadmin_home' if panel == PANEL_CMS else 'admin:index'
    root = reverse(name)
    return root if root.endswith('/') else root + '/'


def panel_url(panel):
    """Para onde mandar o usuário ao escolher este painel."""
    return panel_root(panel)


def _normalize_path(url):
    """Extrai o caminho de uma URL e garante barra final.

    A barra final é o que impede '/administracao/' e '/adminfoo' de casarem
    com o prefixo '/admin/'.
    """
    path = urlsplit(url or '').path or '/'
    if not path.startswith('/'):
        path = '/' + path
    return path if path.endswith('/') else path + '/'


def panel_for_url(url):
    """Classifica uma URL: a qual painel ela pertence, se é que pertence.

    Devolve None para endereços do site público — que qualquer pessoa
    autenticada pode visitar.
    """
    path = _normalize_path(url)
    for panel in PANEL_ORDER:
        root = panel_root(panel)
        if path == root or path.startswith(root):
            return panel
    return None


def _auth_paths():
    """Caminhos de autenticação — destinos proibidos para um `next`.

    Mandar alguém recém-autenticado de volta para uma tela de login gera laço;
    mandar para o logout desfaz o login que acabou de acontecer.
    """
    paths = set()
    for name in ('panel:login', 'panel:logout', 'accounts:login', 'accounts:logout'):
        try:
            paths.add(_normalize_path(reverse(name)))
        except NoReverseMatch:
            continue
    for panel in PANEL_ORDER:
        root = panel_root(panel)
        paths.add(_normalize_path(root + 'login/'))
        paths.add(_normalize_path(root + 'logout/'))
    return paths


def is_auth_path(url):
    return _normalize_path(url) in _auth_paths()


def is_safe_next(url, request):
    """Aceita apenas destinos internos — barra open redirect."""
    if not url:
        return False
    return url_has_allowed_host_and_scheme(
        url=url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )


# ── Apresentação ───────────────────────────────────────────────────────────

def panel_cards(user):
    """Dados dos cards de destino, prontos para o template."""
    reachable = set(available_panels(user)) if user is not None else set()
    return [
        {
            'key': panel,
            'label': PANEL_LABELS[panel],
            'description': PANEL_DESCRIPTIONS[panel],
            'icon': PANEL_ICONS[panel],
            'url': panel_url(panel),
            'allowed': panel in reachable,
        }
        for panel in PANEL_ORDER
    ]


def panel_label(panel):
    return PANEL_LABELS.get(panel, '')


# ── Destino pós-login ──────────────────────────────────────────────────────

def no_access_url(panel=''):
    url = reverse('panel:no_access')
    return f'{url}?painel={panel}' if panel else url


def post_login_target(user, request, next_url='', chosen_panel=''):
    """Onde este usuário aterrissa. Regra única, em um lugar só.

    Precedência:
      1. `next` — se for interno, não for tela de autenticação e o usuário
         alcançar o destino. Pedir um painel proibido leva à página de
         "sem acesso", nunca a um desvio silencioso: quem clicou num link
         precisa saber por que não chegou lá.
      2. o painel escolhido no formulário, se de fato permitido.
      3. único painel disponível -> entra direto; dois -> escolhe na tela.
      4. nenhum painel -> portal público.
    """
    allowed = available_panels(user)

    if next_url and is_safe_next(next_url, request) and not is_auth_path(next_url):
        target_panel = panel_for_url(next_url)
        if target_panel is None or target_panel in allowed:
            return next_url
        return no_access_url(target_panel)

    if chosen_panel in allowed:
        return panel_url(chosen_panel)

    if len(allowed) == 1:
        return panel_url(allowed[0])
    if len(allowed) > 1:
        return reverse('panel:picker')

    return resolve_url(settings.LOGIN_REDIRECT_URL)
