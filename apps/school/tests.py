import pytest
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils.html import escapejs

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
def test_school_homepage_exposes_bilingual_cms_content(client, current_site):
    SchoolHomeConfig.objects.update_or_create(
        site=current_site,
        defaults={
            'hero_title': 'Home em português',
            'hero_title_en': 'Editable English home',
            'hero_subtitle': 'Texto principal em português.',
            'hero_subtitle_en': 'Main English text.',
            'proposal_description': 'Descrição em português.',
            'proposal_description_en': 'English proposal description.',
        },
    )
    SchoolFeature.objects.create(
        site=current_site,
        placement=SchoolFeature.Placement.TRUST,
        title='Bloco em português',
        title_en='English feature block',
        description='Descrição do bloco em português.',
        description_en='English feature description.',
    )
    SchoolTestimonial.objects.create(
        site=current_site,
        name='Aluno Teste',
        relationship='Aluno',
        relationship_en='Student',
        quote='Depoimento em português.',
        quote_en='English testimonial quote.',
        is_featured=True,
    )

    response = client.get(reverse('school:home'))

    content = response.content.decode()
    assert response.status_code == 200
    assert 'Editable English home' in content
    assert 'English proposal description.' in content
    assert 'English feature block' in content
    assert 'English testimonial quote.' in content
    assert 'Student' in content


@pytest.mark.django_db
def test_school_homepage_bilingual_fields_fall_back_to_portuguese(client, current_site):
    SchoolHomeConfig.objects.update_or_create(
        site=current_site,
        defaults={
            'hero_title': 'Custom PT fallback title',
            'hero_title_en': '',
        },
    )
    SchoolFeature.objects.create(
        site=current_site,
        placement=SchoolFeature.Placement.TRUST,
        title='Custom PT fallback block',
        title_en='',
        description='Custom PT fallback description.',
        description_en='',
    )

    response = client.get(reverse('school:home'))

    content = response.content.decode()
    assert response.status_code == 200
    assert "t('Custom PT fallback title', 'Custom PT fallback title')" in content
    assert "t('Custom PT fallback block', 'Custom PT fallback block')" in content


@pytest.mark.django_db
def test_school_homepage_exposes_legacy_communicator_translation(client, current_site):
    description_en = 'A 420-hour course for people who want to become professionals in communication.'
    SchoolFeature.objects.create(
        site=current_site,
        placement=SchoolFeature.Placement.LIFE,
        title='Comunicador',
        title_en='Communicator',
        description='Curso de 420 horas para quem quer se profissionalizar na área de comunicação.',
        description_en=description_en,
    )

    response = client.get(reverse('school:home'))

    content = response.content.decode()
    assert response.status_code == 200
    assert 'Communicator' in content
    assert escapejs(description_en) in content


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
    assert 'Professional Communicator' in content
    assert 'Unlocked Communication' in content


@pytest.mark.django_db
def test_school_homepage_renders_kelly_intro_block(client, current_site):
    response = client.get(reverse('school:home'))

    content = response.content.decode()
    assert response.status_code == 200
    assert 'Kelly Farias, CEO da Komuniki' in content
    assert 'Jornalista, atriz, radialista' in content
    assert 'Kelly Farias, CEO of Komuniki' in content
    assert 'images/kelly-farias-komuniki.jpeg' in content


@pytest.mark.django_db
def test_school_team_page_redirects_to_news_blog(client, current_site):
    TeamMember.objects.create(site=current_site, name='Maria Atual', title='Direção', is_active=True)

    response = client.get(reverse('school:team_list'))

    assert response.status_code == 302
    assert response['Location'] == reverse('news:list')


@pytest.mark.django_db
def test_school_privacy_page_renders_transparent_bilingual_policy(client, current_site):
    response = client.get(reverse('school:privacy'))

    content = response.content.decode()
    assert response.status_code == 200
    assert 'Como a Komuniki trata dados no site' in content
    assert 'How Komuniki handles data on this site' in content
    assert 'Dados enviados por formulários' in content
    assert 'Data sent through forms' in content
    assert 'Registros técnicos e compartilhamento' in content
    assert 'Technical logs and sharing' in content
    assert 'Retenção, correção e remoção' in content
    assert 'Retention, correction and deletion' in content


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
