"""Views do painel unificado. FBV, como manda docs/ai/development_rules.md §2.

A porta continua sendo ``apps.accounts.panels``: só entra na visão geral quem
alcança pelo menos uma área administrativa. Quem não alcança nenhuma recebe a
mesma explicação de sempre (``panel:no_access``).
"""

from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from wagtail.admin.auth import require_admin_access

from apps.accounts import panels
from apps.common.newsroom import dashboard as dashboard_data
from apps.common.newsroom import workspaces
from apps.common.newsroom.navigation import available_workspaces, build_navigation, current_workspace


@login_required(login_url='panel:login')
@require_http_methods(['GET'])
def dashboard(request):
    if not panels.available_panels(request.user):
        return redirect('panel:no_access')

    workspace = current_workspace(request)
    workspace_key = workspace.key if workspace else None
    listing = dashboard_data.list_context(request, workspace_key)

    # Busca, filtros e paginação via HTMX: devolve só a região de resultados,
    # sem recalcular navegação, indicadores e atividade a cada tecla.
    if getattr(request, 'htmx', False) and listing is not None:
        return render(request, 'newsroom/partials/results.html', {'listing': listing})

    navigation = build_navigation(request)
    context = {
        'nav': navigation,
        'workspace': workspace,
        'listing': listing,
        'page_title': 'Visão geral',
        **dashboard_data.overview_context(request, workspace_key),
    }
    return render(request, 'newsroom/dashboard.html', context)


@login_required(login_url='panel:login')
@require_POST
def switch_workspace(request):
    """Guarda na sessão o espaço escolhido — só entre os que a pessoa enxerga."""
    requested = request.POST.get('workspace', '')
    allowed = {ws.key for ws in available_workspaces(request)}
    if requested in allowed:
        request.session[workspaces.SESSION_KEY] = requested
    return redirect('panel:dashboard')


# ── Páginas iniciais antigas ───────────────────────────────────────────────
#
# /cms/ e /admin/ deixam de ter página inicial própria: as duas levam à visão
# geral. Os redirecionamentos continuam atrás das MESMAS portas de antes
# (require_admin_access do Wagtail e admin_view do Django), para que quem não
# alcança a área receba exatamente a resposta de sempre — login ou "sem acesso".


@require_admin_access
@require_GET
def cms_home_redirect(request):
    return redirect('panel:dashboard')


@require_GET
def _admin_index_redirect(request):
    return redirect('panel:dashboard')


admin_index_redirect = admin.site.admin_view(_admin_index_redirect)
