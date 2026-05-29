import pytest
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.hiring.forms import ApplicationForm
from apps.hiring.models import Application, Department, JobPosting


@pytest.mark.django_db
def test_hiring_job_list(client):
    url = reverse('hiring:list')
    response = client.get(url)
    assert response.status_code == 200
    assert 'text/html' in response['Content-Type']


@pytest.fixture
def application(db, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    settings.DEBUG = False  # força o caminho X-Accel-Redirect (produção)
    department = Department.objects.create(name='TI', slug='ti')
    job = JobPosting.objects.create(
        department=department, title='Dev', slug='dev',
        description='x', requirements='y', status=JobPosting.Status.OPEN,
    )
    return Application.objects.create(
        job=job, first_name='Ana', last_name='Silva',
        email='ana@example.com', phone='11999999999',
        resume=SimpleUploadedFile('cv.pdf', b'%PDF-1.4 conteudo', content_type='application/pdf'),
    )


@pytest.mark.django_db
def test_download_resume_anonymous_blocked(client, application):
    url = reverse('hiring:download_resume', args=[application.pk])
    response = client.get(url)
    # staff_member_required redireciona quem não é staff para o login do admin
    assert response.status_code in (302, 403)
    assert 'X-Accel-Redirect' not in response


@pytest.mark.django_db
def test_download_resume_staff_without_perm_forbidden(client, django_user_model, application):
    user = django_user_model.objects.create_user(username='editor', password='x', is_staff=True)
    client.force_login(user)
    url = reverse('hiring:download_resume', args=[application.pk])
    response = client.get(url)
    assert response.status_code == 403
    assert 'X-Accel-Redirect' not in response


@pytest.mark.django_db
def test_download_resume_staff_with_perm_ok(client, django_user_model, application):
    user = django_user_model.objects.create_user(username='rh', password='x', is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename='view_application'))
    client.force_login(user)
    url = reverse('hiring:download_resume', args=[application.pk])
    response = client.get(url)
    assert response.status_code == 200
    # Nunca expõe o caminho público; serve apenas via location interna do nginx
    assert response['X-Accel-Redirect'].startswith('/protected/hiring/resumes/')


@pytest.mark.django_db
def test_clean_resume_rejects_spoofed_content(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    # content_type e extensão dizem PDF, mas o conteúdo não é — deve ser rejeitado.
    upload = SimpleUploadedFile('cv.pdf', b'isto nao e um pdf', content_type='application/pdf')
    form = ApplicationForm(
        data={
            'first_name': 'Ana', 'last_name': 'Silva',
            'email': 'ana@example.com', 'phone': '11999999999',
            'cover_letter': '',
        },
        files={'resume': upload},
    )
    assert not form.is_valid()
    assert 'resume' in form.errors
