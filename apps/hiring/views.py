from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404

from .models import Application


def _can_view_applications(request):
    """A MESMA regra da tela de Candidaturas do admin (ApplicationAdmin).

    Candidaturas são recurso guardado, só de superusuário no admin e no menu.
    A rota conferia só `hiring.view_application` — que o Administrador Geral
    recebe — e baixava currículos que a tela dele recusava com 403. Perguntar
    ao próprio ModelAdmin impede que as duas regras voltem a divergir.
    """
    return admin.site.get_model_admin(Application).has_view_permission(request)


@staff_member_required
def download_resume(request, application_id):
    """Serve o currículo de uma candidatura a quem pode abrir as Candidaturas.

    Produção: delega o envio ao nginx via X-Accel-Redirect (location interna),
    sem expor o arquivo em /media/. Desenvolvimento (sem nginx): FileResponse.
    """
    # Antes de buscar o objeto: quem não pode ver recebe 403 para qualquer ID,
    # sem distinguir candidatura existente de inexistente.
    if not _can_view_applications(request):
        raise PermissionDenied
    application = get_object_or_404(Application, pk=application_id)
    if not application.resume:
        raise Http404('Currículo não encontrado.')

    filename = Path(application.resume.name).name

    if settings.DEBUG:
        return FileResponse(application.resume.open('rb'), as_attachment=True, filename=filename)

    response = HttpResponse()
    response['Content-Type'] = ''  # deixa o nginx definir o tipo a partir do arquivo
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['X-Accel-Redirect'] = f'/protected/{application.resume.name}'
    return response
