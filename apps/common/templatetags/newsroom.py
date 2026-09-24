"""Tags da casca do painel unificado — usadas pela visão geral, pelo Wagtail
(templates/wagtailadmin/base.html) e pelo Unfold (templates/admin/nav_sidebar.html
e templates/unfold/helpers/header.html).

As inclusion tags recalculam a navegação a partir de ``request``, então
funcionam em qualquer um dos três contextos sem depender de context processor.
"""

import re
from datetime import timedelta

from django import template
from django.templatetags.static import static
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.html import format_html

from apps.accounts import panels
from apps.common.admin_nav import MANAGEMENT_PERMISSIONS, SCHOOL_PERMISSIONS, can_any
from apps.common.newsroom import workspaces
from apps.common.newsroom.admin_forms import form_bar
from apps.common.newsroom.admin_lists import list_header
from apps.common.newsroom.branding import get_branding
from apps.common.newsroom.editor import editor_bar
from apps.common.newsroom.navigation import build_navigation
from apps.common.newsroom.wagtail_lists import empty_message as wagtail_empty_message
from apps.common.newsroom.wagtail_lists import list_header as wagtail_list_header

register = template.Library()

ICON_SPRITE = 'newsroom/icons.svg'
SELECTED_WORD = re.compile(r'\s+selecionad[oa]s?\b', re.IGNORECASE)


@register.simple_tag
def nr_icon(name, classname=''):
    """Ícone linear do sprite local (sem CDN). Sempre decorativo: o nome
    acessível vem do texto do controle, nunca do desenho."""
    classes = f'nr-icon {classname}'.strip()
    return format_html(
        '<svg class="{}" aria-hidden="true" focusable="false"><use href="{}#nr-{}"></use></svg>',
        classes,
        static(ICON_SPRITE),
        name,
    )


@register.simple_tag
def newsroom_product_name():
    return get_branding()['PRODUCT_NAME']


@register.filter
def nr_relative(value):
    """Data relativa curta em PT-BR ("Há 12 min", "Ontem", "12/09/2026")."""
    if not value:
        return ''
    now = timezone.now()
    delta = now - value
    if delta < timedelta(0):
        return timezone.localtime(value).strftime('%d/%m/%Y %H:%M')
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return 'Agora'
    if seconds < 3600:
        return f'Há {seconds // 60} min'
    if seconds < 86400:
        hours = seconds // 3600
        return f'Há {hours} hora' if hours == 1 else f'Há {hours} horas'
    local_value = timezone.localdate(value)
    days = (timezone.localdate(now) - local_value).days
    if days <= 1:
        return 'Ontem'
    if days < 7:
        return f'Há {days} dias'
    return local_value.strftime('%d/%m/%Y')


def _initials(user):
    name = (user.get_full_name() or user.get_username() or '?').strip()
    return name[:1].upper()


def account_context(request):
    user = request.user
    if panels.can_access_cms(user):
        account_url = reverse('wagtailadmin_account')
    elif panels.can_access_admin(user):
        account_url = reverse('admin:password_change')
    else:
        account_url = ''
    if user.is_superuser:
        role = 'Superusuário'
    else:
        role = user.get_role_display() if hasattr(user, 'get_role_display') else ''
    avatar_url = ''
    avatar = getattr(user, 'avatar', None)
    if avatar:
        try:
            avatar_url = avatar.url
        except ValueError:
            avatar_url = ''
    return {
        'name': user.get_full_name() or user.get_username(),
        'email': user.email,
        'role': role,
        'initial': _initials(user),
        'avatar_url': avatar_url,
        'url': account_url,
    }


def help_context(request, workspace):
    """Central de ajuda = guias de operação existentes, quando a pessoa alcança.

    Os guias vivem no /admin/ (porta: is_staff). Sem guia acessível, a caixa de
    ajuda não aparece — nada de link para lugar nenhum.
    """
    user = request.user
    if not panels.can_access_admin(user):
        return None
    school_guide = can_any(user, SCHOOL_PERMISSIONS)
    management_guide = can_any(user, MANAGEMENT_PERMISSIONS)
    if workspace and workspace.key == workspaces.KOMUNIKI and school_guide:
        return {'url': reverse('admin_school_guide'), 'label': 'Guia Komuniki'}
    if management_guide:
        return {'url': reverse('admin_management_guide'), 'label': 'Guia de gerenciamento'}
    if school_guide:
        return {'url': reverse('admin_school_guide'), 'label': 'Guia Komuniki'}
    return None


def shell_context(request):
    """Contexto comum de sidebar e topbar, memorizado por requisição."""
    cached = getattr(request, '_newsroom_shell', None)
    if cached is not None:
        return cached
    navigation = build_navigation(request)
    context = {
        'nav': navigation,
        'account': account_context(request),
        'help': help_context(request, navigation['workspace']),
        'dashboard_url': reverse('panel:dashboard'),
        'workspace_switch_url': reverse('panel:workspace'),
        'logout_url': reverse('panel:logout'),
        'login_url': reverse('panel:login'),
    }
    request._newsroom_shell = context
    return context


@register.inclusion_tag('newsroom/partials/sidebar.html', takes_context=True)
def newsroom_sidebar(context):
    request = context['request']
    return {**shell_context(request), 'request': request, 'csrf_token': context.get('csrf_token')}


@register.inclusion_tag('newsroom/partials/topbar.html', takes_context=True)
def newsroom_topbar(context, page_title='', crumbs=None):
    request = context['request']
    shell = shell_context(request)
    return {
        **shell,
        'request': request,
        'csrf_token': context.get('csrf_token'),
        'page_title': page_title or shell['nav']['active_label'],
        'crumbs': crumbs or [],
    }


def _admin_crumbs(context):
    """Trilha das telas do Django admin: lista do modelo › objeto aberto."""
    opts = context.get('opts')
    obj = context.get('original') or context.get('object')
    crumbs = []
    if opts is not None:
        changelist = f'admin:{opts.app_label}_{opts.model_name}_changelist'
        try:
            url = reverse(changelist)
        except NoReverseMatch:
            url = ''
        # Nos formulários, quem só pode adicionar não abre a lista (403).
        if not context.get('has_view_permission', True):
            url = ''
        crumbs.append({'label': str(opts.verbose_name_plural).capitalize(), 'url': url})
        if obj is not None and not isinstance(obj, str):
            crumbs.append({'label': str(obj), 'url': ''})
        elif context.get('add'):
            crumbs.append({'label': f'Adicionar {opts.verbose_name}', 'url': ''})
    elif context.get('title'):
        crumbs.append({'label': str(context['title']), 'url': ''})
    return crumbs


@register.inclusion_tag('newsroom/partials/topbar.html', takes_context=True)
def newsroom_admin_topbar(context):
    crumbs = _admin_crumbs(context)
    return newsroom_topbar(context, page_title=crumbs[-1]['label'] if crumbs else '', crumbs=crumbs)


@register.inclusion_tag('newsroom/partials/menu_toggle.html')
def newsroom_menu_toggle(classname=''):
    return {'classname': classname}


@register.simple_tag(takes_context=True)
def nr_editor_bar(context):
    """Dados da barra única do editor (templates/newsroom/editor/header.html)."""
    return editor_bar(context)


@register.simple_tag(takes_context=True)
def nr_wagtail_list_header(context):
    """Dados do cabeçalho das listagens do Wagtail (templates/newsroom/wagtail/list_header.html)."""
    return wagtail_list_header(context)


@register.simple_tag(takes_context=True)
def nr_wagtail_empty_message(context):
    """Frase de lista vazia das listagens do Wagtail, ou None (fica a do Wagtail)."""
    return wagtail_empty_message(context)


@register.simple_tag(takes_context=True)
def nr_admin_list_header(context):
    """Dados do cabeçalho das listas do Django admin (templates/admin/includes/model_list_help.html)."""
    return list_header(context)


@register.simple_tag(takes_context=True)
def nr_admin_form_bar(context):
    """Dados da barra dos formulários do Django admin (templates/admin/includes/form_bar.html)."""
    return form_bar(context)


@register.filter
def nr_action_label(label):
    """Rótulo curto de uma ação em massa na barra de seleção: sem o
    "selecionadas" da descrição do Django, que a barra já diz ("Arquivar
    mensagens selecionadas" vira "Arquivar mensagens")."""
    return SELECTED_WORD.sub('', str(label)).strip()
