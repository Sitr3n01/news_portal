import pytest
from django.contrib.sites.models import Site
from django.urls import reverse

from apps.school.models import Page, SchoolFeature, SchoolHomeConfig, TeamMember
from apps.school.models import Testimonial as SchoolTestimonial


@pytest.fixture
def current_site(settings):
    site, _ = Site.objects.update_or_create(
        pk=settings.SITE_ID,
        defaults={'domain': 'testserver', 'name': 'Komuniki Teste'},
    )
    Site.objects.clear_cache()
    return site


@pytest.mark.django_db
def test_school_homepage_uses_cms_backend_content(client, current_site):
    SchoolHomeConfig.objects.update_or_create(
        site=current_site,
        defaults={
            'hero_badge': 'Formação personalizada',
            'hero_title': 'Uma home administrável',
            'hero_subtitle': 'Conteúdo vindo do backend da Komuniki.',
        },
    )
    SchoolFeature.objects.create(
        site=current_site,
        placement=SchoolFeature.Placement.TRUST,
        title='Vínculo real',
        description='Diferencial cadastrado no admin.',
    )
    TeamMember.objects.create(site=current_site, name='Ana Souza', title='Coordenação', is_active=True)
    SchoolTestimonial.objects.create(site=current_site, name='Família Lima', quote='Confiança no cotidiano.', is_featured=True)

    response = client.get(reverse('school:home'))

    assert response.status_code == 200
    assert 'text/html' in response['Content-Type']
    content = response.content.decode()
    assert 'Uma home administrável' in content
    assert 'Vínculo real' in content
    assert 'Ana Souza' not in content
    assert 'Família Lima' in content


@pytest.mark.django_db
def test_school_homepage_does_not_leak_other_site_content(client, current_site):
    other_site = Site.objects.create(domain='other.testserver', name='Outra Escola')
    SchoolFeature.objects.create(
        site=other_site,
        placement=SchoolFeature.Placement.TRUST,
        title='Conteúdo de outro site',
        description='Não deve aparecer.',
    )
    TeamMember.objects.create(site=other_site, name='Professor Outro', title='Outro site', is_active=True)
    SchoolTestimonial.objects.create(site=other_site, name='Depoimento Outro', quote='Outro site.', is_featured=True)

    response = client.get(reverse('school:home'))

    content = response.content.decode()
    assert 'Conteúdo de outro site' not in content
    assert 'Professor Outro' not in content
    assert 'Depoimento Outro' not in content


@pytest.mark.django_db
def test_school_homepage_lists_current_course_cards(client, current_site):
    response = client.get(reverse('school:home'))

    content = response.content.decode()
    assert response.status_code == 200
    assert 'Comunicador Profissionalizante' in content
    assert 'Produção Cultural' in content
    assert 'Jornalismo Cultural' in content
    assert 'Apresentação de Palco e Eventos' in content
    assert 'Espanhol' in content
    assert 'Comunicação Destravada' in content


@pytest.mark.django_db
def test_school_team_page_redirects_to_news_blog(client, current_site):
    TeamMember.objects.create(site=current_site, name='Maria Atual', title='Direção', is_active=True)

    response = client.get(reverse('school:team_list'))

    assert response.status_code == 302
    assert response['Location'] == reverse('news:list')


@pytest.mark.django_db
def test_school_page_detail_uses_current_site_for_duplicate_slug(client, current_site):
    other_site = Site.objects.create(domain='pages.other', name='Páginas Outro Site')
    Page.objects.create(site=current_site, title='Projeto', slug='projeto', content='Conteúdo do site atual', is_published=True)
    Page.objects.create(site=other_site, title='Projeto', slug='projeto', content='Conteúdo de outro site', is_published=True)

    response = client.get(reverse('school:page_detail', args=['projeto']))

    content = response.content.decode()
    assert response.status_code == 200
    assert 'Conteúdo do site atual' in content
    assert 'Conteúdo de outro site' not in content


@pytest.mark.django_db
def test_courses_page_renders_komuniki_course_cards(client, current_site):
    Page.objects.update_or_create(
        site=current_site,
        slug='cursos',
        defaults={
            'title': 'Cursos',
            'content': 'Conteúdo administrativo substituído pela grade visual.',
            'is_published': True,
        },
    )

    response = client.get(reverse('school:page_detail', args=['cursos']))

    content = response.content.decode()
    assert response.status_code == 200
    assert 'Comunicador Profissionalizante' in content
    assert '350 horas' in content
    assert 'Produção Cultural' in content
    assert 'Comunicação Destravada' in content
    assert 'Vencedor do Prêmio Paulo Freire de Educação 2024' in content
