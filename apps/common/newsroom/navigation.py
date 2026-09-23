"""Registro único da navegação do painel unificado.

Cada item aponta para uma tela nativa do Wagtail ou do Django admin e declara
QUEM pode vê-lo delegando à mesma checagem que a tela de destino aplica:

* telas do Django admin: ``panels.can_access_admin`` (a porta do /admin/) +
  ``ModelAdmin.has_view_or_change_permission`` (a checagem do changelist);
* telas do Wagtail: ``panels.can_access_cms`` (a porta do /cms/) + a
  ``permission_policy`` do próprio viewset/app;
* relatórios e configurações do Wagtail vêm do ``reports_menu``/``settings_menu``
  do próprio Wagtail, que já filtram por permissão (``is_shown``).

Assim o menu nunca oferece o que a tela recusa. E, ao contrário, esconder um
item não protege nada: as views continuam checando no backend.
"""

from dataclasses import dataclass
from typing import Callable

from django.apps import apps
from django.contrib import admin
from django.urls import NoReverseMatch, reverse

from apps.accounts import panels
from apps.common.newsroom import workspaces
from apps.common.newsroom.branding import get_branding

GROUP_WORKSPACE = 'workspace'
GROUP_MANAGEMENT = 'management'
GROUP_ADMIN = 'admin'
GROUP_LABELS = {
    GROUP_WORKSPACE: 'Workspace',
    GROUP_MANAGEMENT: 'Gerenciamento',
    GROUP_ADMIN: 'Administração',
}
GROUP_ORDER = (GROUP_WORKSPACE, GROUP_MANAGEMENT, GROUP_ADMIN)

# Seções recolhíveis no fim da sidebar (fora do fluxo diário).
SECTION_CMS_TOOLS = 'cms_tools'
SECTION_STORED = 'stored'


# ── Predicados de visibilidade ─────────────────────────────────────────────


def _admin_model(app_label, model_name):
    """Visível se a porta do /admin/ abre E o changelist daquele modelo abre."""

    def check(request):
        if not panels.can_access_admin(request.user):
            return False
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            return False
        model_admin = admin.site.get_model_admin(model) if admin.site.is_registered(model) else None
        return bool(model_admin and model_admin.has_view_or_change_permission(request))

    return check


def _superuser_admin_model(app_label, model_name):
    """Recursos guardados: só superusuário, como já era no menu do Unfold."""
    inner = _admin_model(app_label, model_name)
    return lambda request: request.user.is_superuser and inner(request)


def _snippet(app_label, model_name):
    """Mesma regra do IndexView de snippets: qualquer uma das quatro ações."""

    def check(request):
        if not panels.can_access_cms(request.user):
            return False
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            return False
        viewset = getattr(model, 'snippet_viewset', None)
        if viewset is None:
            return False
        return viewset.permission_policy.user_has_any_permission(
            request.user, ['add', 'change', 'delete', 'view'],
        )

    return check


def _wagtail_collection_policy(module_path):
    """Imagens e documentos: mesma regra do ImagesMenuItem/DocumentsMenuItem."""

    def check(request):
        if not panels.can_access_cms(request.user):
            return False
        from importlib import import_module

        policy = import_module(module_path).permission_policy
        return policy.user_has_any_permission(request.user, ['add', 'change', 'delete'])

    return check


def _cms_perm(permission):
    def check(request):
        return panels.can_access_cms(request.user) and request.user.has_perm(permission)

    return check


def _any_panel(request):
    return bool(panels.available_panels(request.user))


# ── Contadores dos selos (uma consulta por selo, só para quem vê o item) ────


def _count_articles(request):
    from apps.news.models import Article

    return Article.objects.count()


def _count_in_review(request):
    from apps.news.editorial import in_review_count

    return in_review_count()


def _count_pending_comments(request):
    from apps.news.models import Comment

    return Comment.objects.filter(is_active=False).count()


def _count_new_messages(request):
    from apps.contact.models import ContactInquiry

    return ContactInquiry.objects.filter(status=ContactInquiry.Status.NEW).count()


# ── Itens ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class NavItem:
    key: str
    label: str
    icon: str
    url_name: str
    group: str
    visible: Callable
    workspace: str | None = None
    badge: Callable | None = None
    # 'alert' pinta o selo de laranja e só aparece com contagem > 0.
    badge_tone: str = ''
    exact: bool = False
    section: str | None = None

    def url(self):
        try:
            return reverse(self.url_name)
        except NoReverseMatch:
            return ''


NAV_ITEMS = (
    NavItem('overview', 'Visão geral', 'grid', 'panel:dashboard', GROUP_WORKSPACE, _any_panel, exact=True),

    # Blog da Kelly — conteúdo (Wagtail)
    NavItem('articles', 'Notícias', 'news', 'wagtailsnippets_news_article:list', GROUP_WORKSPACE,
            _snippet('news', 'article'), workspaces.KELLY, badge=_count_articles),
    NavItem('review', 'Em revisão', 'clock', 'news_workflow_report', GROUP_WORKSPACE,
            _cms_perm('news.view_article'), workspaces.KELLY, badge=_count_in_review, badge_tone='alert'),

    # Blog da Kelly — gerenciamento
    NavItem('images', 'Biblioteca de mídia', 'image', 'wagtailimages:index', GROUP_MANAGEMENT,
            _wagtail_collection_policy('wagtail.images.permissions'), workspaces.KELLY),
    NavItem('documents', 'Documentos', 'file', 'wagtaildocs:index', GROUP_MANAGEMENT,
            _wagtail_collection_policy('wagtail.documents.permissions'), workspaces.KELLY),
    NavItem('comments', 'Comentários', 'comment', 'wagtailsnippets_news_comment:list', GROUP_MANAGEMENT,
            _snippet('news', 'comment'), workspaces.KELLY, badge=_count_pending_comments, badge_tone='alert'),
    NavItem('newsletter', 'Newsletter', 'mail', 'wagtailsnippets_news_newslettersubscription:list', GROUP_MANAGEMENT,
            _snippet('news', 'newslettersubscription'), workspaces.KELLY),
    NavItem('newsletter_deliveries', 'Entregas da newsletter', 'send', 'wagtailsnippets_news_newsletterdelivery:list',
            GROUP_MANAGEMENT, _snippet('news', 'newsletterdelivery'), workspaces.KELLY),
    NavItem('categories', 'Categorias', 'folder', 'wagtailsnippets_news_category:list', GROUP_MANAGEMENT,
            _snippet('news', 'category'), workspaces.KELLY),
    NavItem('tags', 'Tags', 'tag', 'wagtailsnippets_news_tag:list', GROUP_MANAGEMENT,
            _snippet('news', 'tag'), workspaces.KELLY),
    NavItem('news_home', 'Home do portal', 'home', 'wagtailsnippets_news_newshomeconfig:list', GROUP_MANAGEMENT,
            _snippet('news', 'newshomeconfig'), workspaces.KELLY),

    # Komuniki — conteúdo e atendimento (Django admin)
    NavItem('messages', 'Mensagens', 'inbox', 'admin:contact_contactinquiry_changelist', GROUP_WORKSPACE,
            _admin_model('contact', 'contactinquiry'), workspaces.KOMUNIKI, badge=_count_new_messages, badge_tone='alert'),
    NavItem('school_pages', 'Página Cursos', 'book', 'admin:school_page_changelist', GROUP_WORKSPACE,
            _admin_model('school', 'page'), workspaces.KOMUNIKI),
    NavItem('school_home', 'Home Komuniki', 'home', 'admin:school_schoolhomeconfig_changelist', GROUP_WORKSPACE,
            _admin_model('school', 'schoolhomeconfig'), workspaces.KOMUNIKI),
    NavItem('school_features', 'Blocos da Home', 'blocks', 'admin:school_schoolfeature_changelist', GROUP_WORKSPACE,
            _admin_model('school', 'schoolfeature'), workspaces.KOMUNIKI),

    # Komuniki — gerenciamento
    NavItem('social_accounts', 'Contas de redes sociais', 'share', 'admin:social_socialaccount_changelist',
            GROUP_MANAGEMENT, _admin_model('social', 'socialaccount'), workspaces.KOMUNIKI),
    NavItem('social_posts', 'Posts de redes sociais', 'layers', 'admin:social_socialpost_changelist',
            GROUP_MANAGEMENT, _admin_model('social', 'socialpost'), workspaces.KOMUNIKI),
    NavItem('media_files', 'Arquivos de mídia', 'image', 'admin:media_library_mediafile_changelist',
            GROUP_MANAGEMENT, _admin_model('media_library', 'mediafile'), workspaces.KOMUNIKI),
    NavItem('media_folders', 'Pastas de mídia', 'folder', 'admin:media_library_mediafolder_changelist',
            GROUP_MANAGEMENT, _admin_model('media_library', 'mediafolder'), workspaces.KOMUNIKI),

    # Administração — comum aos dois espaços
    NavItem('users', 'Equipe e usuários', 'users', 'admin:accounts_customuser_changelist', GROUP_ADMIN,
            _admin_model('accounts', 'customuser')),
    NavItem('groups', 'Permissões', 'shield', 'admin:auth_group_changelist', GROUP_ADMIN,
            _admin_model('auth', 'group')),
    NavItem('site_settings', 'Configurações', 'settings', 'wagtailsnippets_common_siteextension:list', GROUP_ADMIN,
            _snippet('common', 'siteextension')),
    # Proteção contra força bruta (django-axes): desbloquear alguém é apagar a
    # tentativa em "Bloqueios de acesso". Sem entrada no menu, a tela só era
    # alcançável digitando a URL. Permissões do app axes: só superusuário.
    NavItem('access_lockouts', 'Bloqueios de acesso', 'shield', 'admin:axes_accessattempt_changelist', GROUP_ADMIN,
            _admin_model('axes', 'accessattempt')),
    NavItem('access_log', 'Histórico de acessos', 'clock', 'admin:axes_accesslog_changelist', GROUP_ADMIN,
            _admin_model('axes', 'accesslog')),
    NavItem('access_failures', 'Falhas de login', 'key', 'admin:axes_accessfailurelog_changelist', GROUP_ADMIN,
            _admin_model('axes', 'accessfailurelog')),

    # Recursos guardados — fora do front atual, só superusuário (como no menu anterior)
    NavItem('testimonials', 'Depoimentos', 'quote', 'admin:school_testimonial_changelist', GROUP_ADMIN,
            _superuser_admin_model('school', 'testimonial'), section=SECTION_STORED),
    NavItem('team', 'Equipe (Komuniki)', 'users', 'admin:school_teammember_changelist', GROUP_ADMIN,
            _superuser_admin_model('school', 'teammember'), section=SECTION_STORED),
    NavItem('jobs', 'Vagas', 'briefcase', 'admin:hiring_jobposting_changelist', GROUP_ADMIN,
            _superuser_admin_model('hiring', 'jobposting'), section=SECTION_STORED),
    NavItem('departments', 'Departamentos', 'building', 'admin:hiring_department_changelist', GROUP_ADMIN,
            _superuser_admin_model('hiring', 'department'), section=SECTION_STORED),
    NavItem('applications', 'Candidaturas', 'file', 'admin:hiring_application_changelist', GROUP_ADMIN,
            _superuser_admin_model('hiring', 'application'), section=SECTION_STORED),
    NavItem('likes', 'Curtidas', 'heart', 'admin:news_articlelike_changelist', GROUP_ADMIN,
            _superuser_admin_model('news', 'articlelike'), section=SECTION_STORED),
    NavItem('bookmarks', 'Favoritos', 'bookmark', 'admin:news_articlebookmark_changelist', GROUP_ADMIN,
            _superuser_admin_model('news', 'articlebookmark'), section=SECTION_STORED),
    # A exportação de e-mails continua no Django admin: lá o CSV neutraliza
    # fórmulas (apps/news/admin._csv_safe) e é restrito a superusuário.
    NavItem('newsletter_legacy', 'Exportar assinantes (CSV)', 'mail', 'admin:news_newslettersubscription_changelist',
            GROUP_ADMIN, _superuser_admin_model('news', 'newslettersubscription'), section=SECTION_STORED),
    NavItem('verification_codes', 'Códigos de verificação', 'key', 'admin:accounts_verificationcode_changelist',
            GROUP_ADMIN, _superuser_admin_model('accounts', 'verificationcode'), section=SECTION_STORED),
    NavItem('google_identities', 'Identidades Google', 'key', 'admin:accounts_googleidentity_changelist',
            GROUP_ADMIN, _superuser_admin_model('accounts', 'googleidentity'), section=SECTION_STORED),
)

SECTION_LABELS = {
    SECTION_CMS_TOOLS: 'Revisão e auditoria',
    SECTION_STORED: 'Recursos guardados',
}

# Itens do menu do Wagtail: rótulo em português claro, ou None para ocultar.
#
# Ocultos da navegação (continuam acessíveis por URL a quem tem permissão):
# * relatórios e sites de *páginas* — o projeto não usa a árvore de páginas do
#   Wagtail (a página padrão foi removida em apps/news/migrations/0023);
# * "Usuários" do Wagtail — a gestão de contas é a do /admin/, que sincroniza
#   cargo e grupos (apps/accounts/admin.py::save_related); editar pela tela do
#   Wagtail pularia essa sincronização.
_WAGTAIL_REPORTS = {
    'noticias-em-revisao': None,  # já é "Em revisão" no grupo Workspace
    'workflows': 'Relatório de revisões',
    'workflow-tasks': 'Relatório de tarefas',
    'site-history': 'Histórico do site',
    'locked-pages': None,
    'aging-pages': None,
    'page-types-usage': None,
}
_WAGTAIL_SETTINGS = {
    'workflows': 'Fluxos de revisão',
    'workflow-tasks': 'Tarefas de revisão',
    'collections': 'Coleções de mídia',
    'groups': 'Grupos e coleções (CMS)',
    'redirects': 'Redirecionamentos',
    'users': None,
    'sites': None,
}


def _wagtail_tool_items(request):
    """Relatórios e configurações do Wagtail, filtrados pelo próprio Wagtail.

    Vêm do ``reports_menu`` e do ``settings_menu`` — os mesmos objetos que
    alimentavam a sidebar original, com o ``is_shown`` de cada item — para que
    nenhuma tela registrada por hook (inclusive em upgrades futuros) fique sem
    caminho de navegação: item desconhecido entra com o rótulo do próprio Wagtail.
    """
    if not panels.can_access_cms(request.user):
        return []
    from wagtail.admin.menu import reports_menu, settings_menu

    items = []
    for menu, labels, icon in ((reports_menu, _WAGTAIL_REPORTS, 'chart'), (settings_menu, _WAGTAIL_SETTINGS, 'sliders')):
        for menu_item in sorted(menu.menu_items_for_request(request), key=lambda i: i.order):
            label = labels.get(menu_item.name, str(menu_item.label))
            if label is None:
                continue
            items.append({
                'key': f'wagtail-{menu_item.name}',
                'label': label,
                'icon': icon,
                'url': menu_item.url,
            })
    return items


# ── Montagem por requisição ────────────────────────────────────────────────


def _visible_items(request):
    cached = getattr(request, '_newsroom_visible_items', None)
    if cached is not None:
        return cached
    visible = []
    for item in NAV_ITEMS:
        if item.visible(request):
            url = item.url()
            if url:
                visible.append((item, url))
    request._newsroom_visible_items = visible
    return visible


def available_workspaces(request):
    keys = {item.workspace for item, _url in _visible_items(request) if item.workspace}
    return [ws for ws in workspaces.all_workspaces() if ws.key in keys]


def _matches(path, url, exact):
    if exact:
        return path == url
    return path == url or path.startswith(url)


def _active_item(request):
    """O item cuja URL é o prefixo mais longo do caminho atual."""
    path = request.path
    best = None
    best_len = -1
    for item, url in _visible_items(request):
        if _matches(path, url, item.exact) and len(url) > best_len:
            best, best_len = item, len(url)
    return best


def current_workspace(request):
    """Espaço exibido: o da tela atual, senão o da sessão, senão o primeiro."""
    available = available_workspaces(request)
    if not available:
        return None
    by_key = {ws.key: ws for ws in available}

    active = _active_item(request)
    if active is not None and active.workspace in by_key:
        return by_key[active.workspace]

    session = getattr(request, 'session', None)
    chosen = session.get(workspaces.SESSION_KEY) if session is not None else None
    return by_key.get(chosen, available[0])


def _badge(request, item):
    if item.badge is None:
        return None
    count = item.badge(request)
    if item.badge_tone == 'alert' and not count:
        return None
    return {'count': count, 'tone': item.badge_tone}


def _entry(request, item, url, active_item):
    return {
        'key': item.key,
        'label': item.label,
        'icon': item.icon,
        'url': url,
        'active': item is active_item,
        'badge': _badge(request, item),
    }


def build_navigation(request):
    """Tudo o que a sidebar precisa para uma requisição, já filtrado."""
    cached = getattr(request, '_newsroom_navigation', None)
    if cached is not None:
        return cached

    workspace = current_workspace(request)
    active_item = _active_item(request)
    ws_key = workspace.key if workspace else None

    groups = {key: [] for key in GROUP_ORDER}
    sections = {SECTION_CMS_TOOLS: [], SECTION_STORED: []}
    for item, url in _visible_items(request):
        if item.workspace and item.workspace != ws_key:
            continue
        entry = _entry(request, item, url, active_item)
        if item.section:
            sections[item.section].append(entry)
        else:
            groups[item.group].append(entry)

    path = request.path
    tools = _wagtail_tool_items(request)
    for tool in tools:
        tool['active'] = active_item is None and path.startswith(tool['url'])
        tool['badge'] = None
    sections[SECTION_CMS_TOOLS] = tools

    navigation = {
        'branding': get_branding(),
        'workspace': workspace,
        'workspaces': available_workspaces(request),
        'groups': [
            {'key': key, 'label': GROUP_LABELS[key], 'items': groups[key]}
            for key in GROUP_ORDER if groups[key]
        ],
        'sections': [
            {
                'key': key,
                'label': SECTION_LABELS[key],
                'items': sections[key],
                'open': any(entry['active'] for entry in sections[key]),
            }
            for key in (SECTION_CMS_TOOLS, SECTION_STORED) if sections[key]
        ],
        'active_label': _active_label(active_item, tools, path),
    }
    request._newsroom_navigation = navigation
    return navigation


def _active_label(active_item, tools, path):
    if active_item is not None:
        return active_item.label
    for tool in tools:
        if path.startswith(tool['url']):
            return tool['label']
    return ''


def is_item_visible(request, key):
    """Atalho para testes e para a visão geral decidirem links condicionais."""
    return any(item.key == key for item, _url in _visible_items(request))


def item_url(request, key):
    for item, url in _visible_items(request):
        if item.key == key:
            return url
    return ''
