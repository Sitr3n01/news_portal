from importlib import import_module

import pytest
from django.apps import apps as django_apps
from django.contrib.sites.models import Site
from django.urls import reverse

from apps.common.models import SiteExtension
from apps.school.courses import COURSE_GROUPS
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
def test_school_homepage_shows_course_tracks_linking_to_courses(client, current_site):
    response = client.get(reverse('school:home'))

    content = response.content.decode()
    courses_url = reverse('school:page_detail', args=['cursos'])
    assert response.status_code == 200
    # Mostra as 3 trilhas-resumo, não o catálogo completo
    assert 'Formação profissionalizante' in content
    assert 'Cursos livres' in content
    assert 'Desenvolvimento pessoal' in content
    assert 'Cursos com encaminhamento profissional' in content
    # Os cards-trilha levam à página de cursos
    assert content.count(f'href="{courses_url}"') >= 3
    assert "t('Ver cursos', 'View courses')" in content
    # Título e "Ver cursos" de cada card sublinham ao interagir com o card
    assert content.count('text-slate-950 ed-underline-lines"') == 3
    assert content.count('<span class="ed-underline" data-reveal="fade" x-text="t(\'Ver cursos\'') == 3
    # O catálogo detalhado vive em /cursos e não é duplicado na home
    assert 'Apresentação de Palco e Eventos' not in content
    assert 'Jornalismo Cultural' not in content


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
def test_school_homepage_renders_particle_stage_with_local_three(client, current_site):
    response = client.get(reverse('school:home'))

    content = response.content.decode()
    assert response.status_code == 200
    # O hero é o palco WebGL; a ilustração estática saiu da Home
    assert 'data-particles-scene' in content
    assert 'class="ed-particles" data-particles' in content
    assert 'particles/rca44-geometry.glb' in content
    assert 'particles/land-mask-640x320.bin' in content
    assert 'images/komuniki-editorial-hero.png' not in content
    # O gancho de depuração só existe na prévia local
    assert 'data-particles-debug' not in content
    # three vem da cópia local via import map: a CSP não libera CDN
    assert '<script type="importmap">' in content
    assert 'js/vendor/three-r186/three.module.js' in content
    assert 'js/vendor/three-r186/three.core.js' in content
    assert 'js/school-editorial-particles.js' in content


def _navbar(content):
    return content[content.index('<nav class="ed-nav"'):content.index('</nav>')]


@pytest.mark.django_db
def test_school_homepage_reveals_all_text_with_local_gsap(client, current_site):
    response = client.get(reverse('school:home'))

    content = response.content.decode()
    assert response.status_code == 200
    # GSAP vem da cópia local, como o three: a CSP não libera CDN
    assert 'js/vendor/gsap-3.15.0/gsap.min.js' in content
    assert 'js/vendor/gsap-3.15.0/ScrollTrigger.min.js' in content
    assert 'js/vendor/gsap-3.15.0/SplitText.min.js' in content
    assert 'js/school-editorial-reveal.js' in content
    # O guard de FOUC nasce no <head>, antes de qualquer texto aparecer
    assert "document.documentElement.classList.add('js')" in content
    # Hero no load, com os textos extras em ordem; o resto da página e o rodapé em grupos no scroll
    assert 'data-particles-scene data-reveal-hero' in content
    assert 'data-reveal-lede' in content
    assert 'data-reveal-at="0.7"' in content
    assert content.count('data-reveal="mask"') >= 4
    assert content.count('data-reveal-group') >= 8
    assert '<li data-reveal="fade"><a ' in content
    # A navbar fica estática
    assert 'data-reveal' not in _navbar(content)


@pytest.mark.django_db
def test_school_about_page_reveals_all_text(client, current_site):
    response = client.get(reverse('school:about'))

    content = response.content.decode()
    assert response.status_code == 200
    assert 'data-reveal="mask"' in content
    assert content.count('data-reveal-group') >= 10
    assert '<li data-reveal="fade"><a ' in content
    assert 'data-reveal' not in _navbar(content)


@pytest.mark.django_db
def test_courses_page_reveals_all_text_but_other_cms_pages_stay_static(client, current_site):
    Page.objects.update_or_create(
        site=current_site,
        slug='cursos',
        defaults={'title': 'Cursos', 'content': 'Grade visual.', 'is_published': True},
    )
    Page.objects.create(site=current_site, title='Projeto', slug='projeto', content='Conteúdo', is_published=True)

    courses = client.get(reverse('school:page_detail', args=['cursos'])).content.decode()
    other = client.get(reverse('school:page_detail', args=['projeto'])).content.decode()

    # Cursos densos usam passo menor na cascata; o rodapé entra junto
    assert 'data-reveal-group data-reveal-step="0.1"' in courses
    assert '<li data-reveal="fade"><a ' in courses
    assert 'data-reveal' not in _navbar(courses)
    assert 'data-reveal="' not in other
    assert 'data-reveal-group' not in other


@pytest.mark.django_db
@pytest.mark.parametrize('url_name', ['school:home', 'school:about', 'contact:page', 'school:privacy'])
def test_school_text_links_carry_the_underline_reveal_hooks(client, current_site, url_name):
    content = client.get(reverse(url_name)).content.decode()

    # O traço fica num elemento justo ao texto: o próprio link inline ou um span interno
    assert '<a class="ed-skip" href="#main-content"><span class="ed-underline"' in content
    assert 'class="ed-brand ed-underline"' in content
    assert _navbar(content).count('class="ed-underline"') == 8
    assert content.count('transition-colors ed-underline" x-text=') == 6
    # A coluna Contato do rodapé cabe o e-mail numa linha só
    assert 'lg:col-span-7 ed-footer-columns"' in content
    if url_name == 'school:privacy':
        assert '<span class="ed-underline" x-text="t(\'Falar com a Komuniki\'' in content


@pytest.mark.django_db
@pytest.mark.parametrize('url_name', ['contact:page', 'school:privacy'])
def test_school_pages_outside_the_reveal_keep_text_static(client, current_site, url_name):
    response = client.get(reverse(url_name))

    content = response.content.decode()
    assert response.status_code == 200
    assert 'data-reveal="' not in content
    assert 'data-reveal-group' not in content


@pytest.mark.django_db
def test_school_team_page_redirects_to_news_blog(client, current_site):
    TeamMember.objects.create(site=current_site, name='Maria Atual', title='Direção', is_active=True)

    response = client.get(reverse('school:team_list'))

    assert response.status_code == 302
    assert response['Location'] == reverse('news:list')


@pytest.mark.django_db
def test_school_footer_social_links_follow_site_settings(client, current_site):
    SiteExtension.objects.update_or_create(
        site=current_site,
        defaults={
            'instagram_url': 'https://www.instagram.com/komuniki_config_teste/',
            'youtube_url': 'https://www.youtube.com/@komuniki_config_teste',
        },
    )

    content = client.get(reverse('school:privacy')).content.decode()

    # O rodapé usa os links cadastrados em Configurações do Site
    assert 'href="https://www.instagram.com/komuniki_config_teste/"' in content
    assert 'href="https://www.youtube.com/@komuniki_config_teste"' in content


@pytest.mark.django_db
def test_school_footer_social_links_fall_back_to_official_profiles(client, current_site):
    SiteExtension.objects.update_or_create(site=current_site, defaults={'instagram_url': '', 'youtube_url': ''})

    content = client.get(reverse('school:privacy')).content.decode()

    assert 'href="https://www.instagram.com/komunikiescola/"' in content
    assert 'href="https://youtube.com/@escolakomuniki?si=8AR-FzPrJh8QCbu3"' in content


@pytest.mark.django_db
def test_school_home_title_prefers_seo_title(client, current_site):
    home, _ = SchoolHomeConfig.objects.update_or_create(
        site=current_site,
        defaults={'hero_title': 'Título do hero', 'meta_title': 'Komuniki | Escola de comunicação'},
    )

    content = client.get(reverse('school:home')).content.decode()
    assert '<title>Komuniki | Escola de comunicação</title>' in content

    home.meta_title = ''
    home.save()
    content = client.get(reverse('school:home')).content.decode()
    assert '<title>Komuniki Teste - Título do hero</title>' in content


# O nome do módulo começa com número, então não dá para usar import comum
real_public_data = import_module('apps.school.migrations.0010_komuniki_real_public_data')

SEEDED_SITE_EXTENSION = {
    'tagline': 'Moldando o futuro, inspirando mentes.',
    'primary_email': 'contato@exemplo.edu.br',
    'phone_number': '(11) 99999-9999',
    'address': 'Rua da Educação, 123, São Paulo - SP',
    'facebook_url': 'https://facebook.com/exemplo',
    'instagram_url': 'https://instagram.com/exemplo',
    'youtube_url': 'https://www.youtube.com/channel/UCidKmbl0ENPRl5vy70-GwfA',
    'social_section_enabled': True,
    'social_section_title': 'TESTE FASE 11 — Redes Sociais Kelly',
}


@pytest.mark.django_db
def test_real_public_data_migration_replaces_seeded_values(current_site):
    Site.objects.filter(pk=current_site.pk).update(name='Escola e Portal de Notícias')
    SiteExtension.objects.update_or_create(site=current_site, defaults=SEEDED_SITE_EXTENSION)
    SchoolFeature.objects.update_or_create(
        site=current_site,
        placement=SchoolFeature.Placement.TRUST,
        title='Projeto Jovem Comunicador',
        defaults={'description': 'Iniciativa social.', 'is_active': True},
    )

    real_public_data.apply_real_public_data(django_apps, None)
    real_public_data.apply_real_public_data(django_apps, None)  # rodar de novo não muda nada

    extension = SiteExtension.objects.get(site=current_site)
    assert Site.objects.get(pk=current_site.pk).name == 'Komuniki'
    assert extension.tagline == 'Comunicação que gera resultados'
    assert extension.primary_email == 'komunikicomunicacao@gmail.com'
    assert extension.phone_number == '(61) 92003-8428'
    assert extension.address == 'QI 11 Bloco A Comércio Local salas 102/104 Guará 1\nBrasília DF, 70274-530, BR'
    assert extension.facebook_url == ''
    assert extension.instagram_url == 'https://www.instagram.com/komunikiescola/'
    assert extension.youtube_url == 'https://youtube.com/@escolakomuniki?si=8AR-FzPrJh8QCbu3'
    assert extension.social_section_enabled is False
    assert extension.social_section_title == 'Acompanhe a Komuniki nas redes'
    assert not SchoolFeature.objects.get(
        site=current_site, placement=SchoolFeature.Placement.TRUST, title='Projeto Jovem Comunicador',
    ).is_active


@pytest.mark.django_db
def test_real_public_data_migration_keeps_values_edited_in_admin(current_site):
    SiteExtension.objects.update_or_create(
        site=current_site,
        defaults={
            'instagram_url': 'https://www.instagram.com/outra_conta/',
            'phone_number': '(61) 3333-4444',
            'facebook_url': 'https://www.facebook.com/Komunikicomunicacao/',
            'social_section_enabled': True,
            'social_section_title': 'Nossas redes',
        },
    )

    real_public_data.apply_real_public_data(django_apps, None)

    extension = SiteExtension.objects.get(site=current_site)
    assert extension.instagram_url == 'https://www.instagram.com/outra_conta/'
    assert extension.phone_number == '(61) 3333-4444'
    assert extension.facebook_url == 'https://www.facebook.com/Komunikicomunicacao/'
    assert extension.social_section_enabled is True
    assert extension.social_section_title == 'Nossas redes'


@pytest.mark.django_db
def test_migrated_database_starts_with_the_real_public_data(settings):
    extension = SiteExtension.objects.get(site_id=settings.SITE_ID)

    assert extension.instagram_url == 'https://www.instagram.com/komunikiescola/'
    assert extension.youtube_url == 'https://youtube.com/@escolakomuniki?si=8AR-FzPrJh8QCbu3'
    assert not SchoolFeature.objects.get(
        site_id=settings.SITE_ID, placement=SchoolFeature.Placement.TRUST, title='Projeto Jovem Comunicador',
    ).is_active


def test_course_catalog_has_english_for_every_text():
    missing = []
    for group in COURSE_GROUPS:
        texts = [(group, 'eyebrow'), (group, 'title'), (group, 'description')]
        for course in group['courses']:
            texts += [(course, 'title'), (course, 'summary')]
            texts += [(detail, key) for detail in course['details'] for key in ('label', 'value')]
            texts += [(note, 'text') for note in course['notes']]
        missing += [item[key] for item, key in texts if not item.get(f'{key}_en')]

    assert missing == []


@pytest.mark.django_db
def test_courses_page_offers_english_for_the_catalog(client, current_site):
    Page.objects.update_or_create(site=current_site, slug='cursos', defaults={'title': 'Cursos', 'is_published': True})

    content = client.get(reverse('school:page_detail', args=['cursos'])).content.decode()

    # Cada texto do catálogo vai para o x-text com a versão em inglês, que o Alpine mostra ao trocar o idioma
    assert "t('Jornalismo Cultural', 'Cultural Journalism')" in content
    assert "t('Carga horária', 'Course hours')" in content
    assert "t('Encaminhamento para registro profissional de Comunicador', 'Guidance toward professional Communicator registration')" in content
    assert "'Winner of the 2024 Paulo Freire Education Award'" in content


@pytest.mark.django_db
def test_contact_course_tag_offers_the_english_course_name(client, current_site):
    content = client.get(reverse('contact:page') + '?curso=jornalismo-cultural').content.decode()

    assert "t('Jornalismo Cultural', 'Cultural Journalism')" in content


@pytest.mark.django_db
def test_contact_subjects_offer_english_labels(client, current_site):
    content = client.get(reverse('contact:page')).content.decode()

    assert "t('Cursos e inscrições', 'Courses and enrollment')" in content
    assert "t('Outro', 'Other')" in content


@pytest.mark.django_db
def test_footer_tagline_offers_english(client, current_site):
    # A migração common.0010 preenche o slogan real em inglês
    content = client.get(reverse('school:privacy')).content.decode()

    assert "t('Comunicação que gera resultados', 'Communication that drives results')" in content


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
    # Cada card de curso leva a Contato com o slug do curso, com traço por linha no título e crescimento ao interagir
    contact_url = reverse('contact:page')
    for slug in ['comunicador-profissionalizante', 'producao-cultural', 'jornalismo-cultural',
                 'apresentacao-de-palco-e-eventos', 'espanhol-conversacao-e-escrita', 'comunicacao-destravada']:
        assert f'<a href="{contact_url}?curso={slug}" class="ed-card flex min-h-72 flex-col rounded-[1.75rem] p-6 focus:outline-none ed-grow"' in content
    assert content.count('text-slate-950 ed-underline-lines" data-reveal="fade"') == 6


@pytest.mark.django_db
def test_school_call_to_action_buttons_grow_on_interaction(client, current_site):
    Page.objects.update_or_create(
        site=current_site,
        slug='cursos',
        defaults={'title': 'Cursos', 'content': 'Grade visual.', 'is_published': True},
    )

    home = client.get(reverse('school:home')).content.decode()
    about = client.get(reverse('school:about')).content.decode()
    courses = client.get(reverse('school:page_detail', args=['cursos'])).content.decode()

    # "Conte-nos mais", "Conheça os cursos" e "Fale com a Komuniki" crescem; navbar e menu móvel entram na conta
    assert _navbar(home).count('class="ed-button ed-grow') == 2
    assert home.count('ed-button ed-grow') == 7
    assert about.count('ed-button ed-grow') == 4
    assert courses.count('ed-button ed-grow') == 5
    # "Ver cursos" e "Ir para notícias", fora do pedido, continuam sem crescer
    assert 'focus:outline-none ed-button ed-button-outline">' in courses
    assert 'focus:outline-none ed-button ed-button-white">' in courses
