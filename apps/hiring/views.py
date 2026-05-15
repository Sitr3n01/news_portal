from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ApplicationForm
from .models import Application, JobPosting


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
