from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ApplicationForm
from .models import Application, JobPosting


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


def job_list(request):
    jobs = JobPosting.objects.filter(status=JobPosting.Status.OPEN)
    return render(request, 'hiring/job_list.html', {'jobs': jobs})

def job_detail(request, slug):
    job = get_object_or_404(JobPosting, slug=slug, status=JobPosting.Status.OPEN)

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            if not Application.objects.filter(job=job, email=email).exists():
                application = form.save(commit=False)
                application.job = job
                application.save()
            messages.success(request, 'Sua candidatura foi enviada com sucesso!')
            return redirect('hiring:job_detail', slug=job.slug)
    else:
        form = ApplicationForm()

    return render(request, 'hiring/job_detail.html', {'job': job, 'form': form})
