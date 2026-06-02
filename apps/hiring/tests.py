import pytest
from django.contrib.auth.models import Permission
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.hiring.forms import ApplicationForm
from apps.hiring.models import Application, Department, JobPosting


@pytest.fixture
def current_site(settings):
    site, _ = Site.objects.update_or_create(
        pk=settings.SITE_ID,
        defaults={'domain': 'testserver', 'name': 'Escola Atual'},
    )
    Site.objects.clear_cache()
    return site


@pytest.mark.django_db
def test_hiring_job_list_filters_current_site(client, current_site):
    other_site = Site.objects.create(domain='jobs.other', name='Vagas Outro Site')
    current_department = Department.objects.create(site=current_site, name='Pedagógico', slug='pedagogico')
    other_department = Department.objects.create(site=other_site, name='Pedagógico', slug='pedagogico')
    JobPosting.objects.create(
        site=current_site,
        department=current_department,
        title='Professor Atual',
        slug='professor',
        description='x',
        requirements='y',
        status=JobPosting.Status.OPEN,
    )
    JobPosting.objects.create(
        site=other_site,
        department=other_department,
        title='Professor Outro Site',
        slug='professor',
        description='x',
        requirements='y',
        status=JobPosting.Status.OPEN,
    )

    response = client.get(reverse('hiring:list'))

    content = response.content.decode()
    assert response.status_code == 200
    assert 'Professor Atual' in content
    assert 'Professor Outro Site' not in content


@pytest.mark.django_db
def test_hiring_job_detail_filters_current_site(client, current_site):
    other_site = Site.objects.create(domain='detail.other', name='Detalhe Outro Site')
    other_department = Department.objects.create(site=other_site, name='Pedagógico', slug='pedagogico')
    JobPosting.objects.create(
        site=other_site,
        department=other_department,
        title='Vaga de outro site',
        slug='vaga-externa',
        description='não vazar',
        requirements='não vazar',
        status=JobPosting.Status.OPEN,
    )

    response = client.get(reverse('hiring:job_detail', args=['vaga-externa']))

    assert response.status_code == 404


@pytest.mark.django_db
def test_job_posting_rejects_department_from_another_site(current_site):
    other_site = Site.objects.create(domain='department.other', name='Departamento Outro Site')
    other_department = Department.objects.create(site=other_site, name='Outro', slug='outro')
    job = JobPosting(
        site=current_site,
        department=other_department,
        title='Vaga inconsistente',
        slug='vaga-inconsistente',
        description='x',
        requirements='y',
        status=JobPosting.Status.OPEN,
    )

    with pytest.raises(ValidationError):
        job.full_clean()


@pytest.fixture
def application(db, tmp_path, settings, current_site):
    settings.MEDIA_ROOT = str(tmp_path)
    settings.DEBUG = False  # força o caminho X-Accel-Redirect (produção)
    department = Department.objects.create(site=current_site, name='TI', slug='ti')
    job = JobPosting.objects.create(
        site=current_site,
        department=department,
        title='Dev',
        slug='dev',
        description='x',
        requirements='y',
        status=JobPosting.Status.OPEN,
    )
    return Application.objects.create(
        job=job,
        first_name='Ana',
        last_name='Silva',
        email='ana@example.com',
        phone='11999999999',
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
    # content_type e extensão dizem PDF, mas o conteúdo não é; deve ser rejeitado.
    upload = SimpleUploadedFile('cv.pdf', b'isto nao e um pdf', content_type='application/pdf')
    form = ApplicationForm(
        data={
            'first_name': 'Ana',
            'last_name': 'Silva',
            'email': 'ana@example.com',
            'phone': '11999999999',
            'cover_letter': '',
        },
        files={'resume': upload},
    )
    assert not form.is_valid()
    assert 'resume' in form.errors
