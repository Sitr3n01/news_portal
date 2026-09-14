import pytest
from django.urls import reverse

from apps.common import turnstile

from .models import ContactInquiry


def mock_turnstile(monkeypatch, *, valid=True):
    monkeypatch.setattr(turnstile, 'verify_turnstile', lambda token, remote_ip='': valid and token == 'valid-token')


@pytest.mark.django_db
def test_contact_page_get(client):
    url = reverse('contact:page')
    response = client.get(url)
    assert response.status_code == 200
    assert 'text/html' in response['Content-Type']


@pytest.mark.django_db
def test_contact_page_post(client, monkeypatch):
    url = reverse('contact:page')
    mock_turnstile(monkeypatch)
    data = {
        'name': 'Test User',
        'email': 'test@example.com',
        'phone': '11999999999',
        'subject': 'general',
        'message': 'This is a test message.',
        'cf-turnstile-response': 'valid-token',
    }
    response = client.post(url, data)
    assert response.status_code == 302 # redirect on success
    assert ContactInquiry.objects.count() == 1
    assert ContactInquiry.objects.first().name == 'Test User'


@pytest.mark.django_db
def test_contact_page_rejects_invalid_turnstile(client, monkeypatch):
    url = reverse('contact:page')
    mock_turnstile(monkeypatch, valid=False)
    data = {
        'name': 'Test User',
        'email': 'test@example.com',
        'phone': '11999999999',
        'subject': 'general',
        'message': 'This is a test message.',
        'cf-turnstile-response': 'bad-token',
    }

    response = client.post(url, data)

    assert response.status_code == 200
    assert ContactInquiry.objects.count() == 0
    assert 'Confirme a verificação anti-bot' in response.content.decode()


@pytest.mark.django_db
def test_contact_page_rejects_missing_turnstile(client, monkeypatch):
    url = reverse('contact:page')
    mock_turnstile(monkeypatch, valid=False)

    response = client.post(url, {
        'name': 'Test User',
        'email': 'test@example.com',
        'phone': '11999999999',
        'subject': 'general',
        'message': 'This is a test message.',
    })

    assert response.status_code == 200
    assert ContactInquiry.objects.count() == 0


@pytest.mark.django_db
def test_contact_page_tags_the_course_chosen_on_the_courses_page(client):
    response = client.get(reverse('contact:page'), {'curso': 'jornalismo-cultural'})

    content = response.content.decode()
    assert response.status_code == 200
    assert '<span class="ed-tag" x-text="t(\'Jornalismo Cultural\', \'Cultural Journalism\')">Jornalismo Cultural</span>' in content
    assert 'name="course_interest" value="jornalismo-cultural"' in content
    # O assunto já vem em "Cursos e inscrições"
    assert '<option value="admissions" selected x-text=' in content


@pytest.mark.django_db
def test_contact_page_ignores_a_course_outside_the_catalog(client):
    content = client.get(reverse('contact:page'), {'curso': '<script>alert(1)</script>'}).content.decode()

    assert 'Curso de interesse' not in content
    assert 'name="course_interest"' not in content
    assert '<script>alert(1)</script>' not in content


def _inquiry_with_course(client, monkeypatch, course_interest):
    mock_turnstile(monkeypatch)
    response = client.post(reverse('contact:page'), {
        'name': 'Test User',
        'email': 'test@example.com',
        'phone': '',
        'subject': 'admissions',
        'course_interest': course_interest,
        'message': 'Quero saber das próximas turmas.',
        'cf-turnstile-response': 'valid-token',
    })
    assert response.status_code == 302
    return ContactInquiry.objects.get()


@pytest.mark.django_db
def test_contact_page_post_records_the_course_of_interest(client, monkeypatch):
    assert _inquiry_with_course(client, monkeypatch, 'jornalismo-cultural').course_interest == 'Jornalismo Cultural'


@pytest.mark.django_db
def test_contact_page_post_drops_a_course_outside_the_catalog(client, monkeypatch):
    assert _inquiry_with_course(client, monkeypatch, 'curso-inventado').course_interest == ''


@pytest.mark.django_db
def test_admin_lists_and_filters_the_course_of_interest(admin_client, current_site):
    ContactInquiry.objects.create(
        site=current_site,
        name='Maria',
        email='maria@example.com',
        subject='admissions',
        course_interest='Jornalismo Cultural',
        message='Quero saber das turmas.',
    )

    response = admin_client.get(reverse('admin:contact_contactinquiry_changelist'))

    content = response.content.decode()
    assert response.status_code == 200
    assert 'Curso de interesse' in content
    assert 'Jornalismo Cultural' in content
