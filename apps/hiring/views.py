from pathlib import Path

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404

from .models import Application


@staff_member_required
@permission_required('hiring.view_application', raise_exception=True)
def download_resume(request, application_id):
    """Serve o currículo de uma candidatura apenas a staff com permissão.

    Produção: delega o envio ao nginx via X-Accel-Redirect (location interna),
    sem expor o arquivo em /media/. Desenvolvimento (sem nginx): FileResponse.
    """
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
