from django.shortcuts import get_object_or_404, redirect, render

from .models import Page, SchoolFeature, SchoolHomeConfig, Testimonial

HOME_FALLBACK = {
    'hero_badge': 'Escola de comunicação, artes e liderança',
    'hero_title': 'Comunicação que gera resultados',
    'hero_subtitle': 'Mentorias e cursos para quem quer se expressar melhor, atuar nos meios audiovisuais, empreender na arte e construir presença com clareza.',
    'visual_eyebrow': 'Komuniki',
    'visual_title': 'Educação para comunicação e artes',
    'visual_footer_title': 'Cursos, mentorias e projetos com aplicação real',
    'visual_footer_text': 'A Komuniki une formação técnica, prática de mercado e acompanhamento próximo para pessoas, artistas, comunicadores e equipes corporativas.',
    'proposal_eyebrow': 'O que fazemos',
    'proposal_title': 'Cursos para comunicação, cultura e presença profissional',
    'proposal_description': 'Criada por Kelly Farias, a Komuniki oferece formações profissionalizantes, cursos livres e mentorias para comunicação, cultura, palco, escrita e autoconfiança.',
    'life_eyebrow': 'Projetos e impacto',
    'life_title': 'Comunicação, cultura e protagonismo',
    'life_description': 'A Komuniki também realiza o projeto social Jovem Comunicador, voltado a jovens em situação de vulnerabilidade social, e promove conexões entre formação, arte e mercado.',
    'team_eyebrow': 'Mentorias com Kelly',
    'team_title': 'Kelly Farias à frente da Komuniki',
    'team_description': 'Jornalista, atriz, radialista, diretora de produção executiva, editora-chefe, mentora e professora de comunicação.',
    'testimonials_eyebrow': 'Alunos',
    'testimonials_title': 'Trajetórias em comunicação e artes',
    'testimonials_description': 'Depoimentos reais podem ser destacados no admin quando a Komuniki quiser publicar relatos de alunos e participantes.',
    'hiring_title': 'Cursos e mentorias',
    'hiring_description': 'Conheça formações para comunicação, artes, apresentação, produção, locução, assessoria e desenvolvimento de estilo de comunicação.',
    'contact_title': 'Conte-nos mais',
    'contact_description': 'Fale com a Komuniki para tirar dúvidas, consultar turmas, solicitar mentorias ou conversar sobre projetos corporativos e culturais.',
}

HOME_FALLBACK_EN = {
    'hero_badge': 'School of communication, arts and leadership',
    'hero_title': 'Communication that drives results',
    'hero_subtitle': 'Mentoring and courses for people who want to express themselves better, work in audiovisual media, build art-driven ventures and communicate with clarity.',
    'visual_eyebrow': 'Komuniki',
    'visual_title': 'Education for communication and the arts',
    'visual_footer_title': 'Courses, mentoring and projects with real-world application',
    'visual_footer_text': 'Komuniki combines technical training, market practice and close guidance for individuals, artists, communicators and corporate teams.',
    'proposal_eyebrow': 'What we do',
    'proposal_title': 'Courses for communication, culture and professional presence',
    'proposal_description': 'Created by Kelly Farias, Komuniki offers professional training, open courses and mentoring in communication, culture, stage presence, writing and self-confidence.',
    'life_eyebrow': 'Projects and impact',
    'life_title': 'Communication, culture and protagonism',
    'life_description': 'Komuniki also runs Jovem Comunicador, a social project for young people in vulnerable situations, and creates connections between training, art and the market.',
    'team_eyebrow': 'Mentoring with Kelly',
    'team_title': 'Kelly Farias leading Komuniki',
    'team_description': 'Journalist, actress, radio host, executive production director, editor-in-chief, mentor and communication teacher.',
    'testimonials_eyebrow': 'Students',
    'testimonials_title': 'Journeys in communication and the arts',
    'testimonials_description': 'Real testimonials can be highlighted in the admin whenever Komuniki wants to publish stories from students and participants.',
    'hiring_title': 'Courses and mentoring',
    'hiring_description': 'Explore training in communication, arts, presenting, production, voice work, press relations and communication style development.',
    'contact_title': 'Tell us more',
    'contact_description': 'Talk to Komuniki to ask questions, check classes, request mentoring or discuss corporate and cultural projects.',
}

HOME_FALLBACK.update({f'{field}_en': value for field, value in HOME_FALLBACK_EN.items()})

TRUST_FEATURES_FALLBACK = [
    {
        'title': 'Mentorias com Kelly Farias',
        'title_en': 'Mentoring with Kelly Farias',
        'description': 'Acompanhamento para desenvolver presença, estilo de comunicação e clareza na expressão.',
        'description_en': 'Guidance to develop presence, communication style and clarity of expression.',
        'tone': 'emerald',
    },
    {
        'title': 'Cursos online, híbridos e presenciais',
        'title_en': 'Online, hybrid and in-person courses',
        'description': 'Formações flexíveis para comunicação, artes, liderança e produção.',
        'description_en': 'Flexible training in communication, arts, leadership and production.',
        'tone': 'slate',
    },
    {
        'title': 'Atuação corporativa',
        'title_en': 'Corporate work',
        'description': 'Mentorias, palestras e comunicação interna para equipes e projetos.',
        'description_en': 'Mentoring, talks and internal communication for teams and projects.',
        'tone': 'emerald',
    },
    {
        'title': 'Projeto Jovem Comunicador',
        'title_en': 'Jovem Comunicador project',
        'description': 'Iniciativa social voltada a jovens em situação de vulnerabilidade social.',
        'description_en': 'A social initiative for young people in vulnerable situations.',
        'tone': 'slate',
    },
]

PROPOSAL_FEATURES_FALLBACK = [
    {
        'title': 'Comunicador Profissionalizante',
        'title_en': 'Professional Communicator',
        'description': 'Formação de 350 horas em 18 meses, com encaminhamento para registro profissional de Comunicador.',
        'description_en': 'A 350-hour, 18-month program with guidance toward professional Communicator registration.',
        'tone': 'emerald',
    },
    {
        'title': 'Produção Cultural',
        'title_en': 'Cultural Production',
        'description': 'Formação de 250 horas em 12 meses, com encaminhamento para registro profissional Diretor de produção.',
        'description_en': 'A 250-hour, 12-month program with guidance toward professional Production Director registration.',
        'tone': 'slate',
    },
    {
        'title': 'Jornalismo Cultural',
        'title_en': 'Cultural Journalism',
        'description': 'Curso livre de 30 horas para jornalistas, influenciadores e produtores de conteúdo.',
        'description_en': 'A 30-hour open course for journalists, influencers and content producers.',
        'tone': 'emerald',
    },
    {
        'title': 'Apresentação de Palco e Eventos',
        'title_en': 'Stage and Event Presenting',
        'description': 'Curso livre de 50 horas com técnicas de apresentação e condução de eventos.',
        'description_en': 'A 50-hour open course with presenting and event-hosting techniques.',
        'tone': 'slate',
    },
    {
        'title': 'Espanhol – Conversação e Escrita',
        'title_en': 'Spanish - Conversation and Writing',
        'description': 'Curso livre para desenvolvimento da comunicação oral e escrita.',
        'description_en': 'An open course to develop oral and written communication.',
        'tone': 'emerald',
    },
    {
        'title': 'Comunicação Destravada',
        'title_en': 'Unlocked Communication',
        'description': '20 horas em curso coletivo ou mentoria individual para oratória, comunicação e autoconfiança.',
        'description_en': '20 hours in a group course or individual mentoring for public speaking, communication and self-confidence.',
        'tone': 'slate',
    },
]

LIFE_FEATURES_FALLBACK = [
    {
        'title': 'Comunicador Profissionalizante',
        'title_en': 'Professional Communicator',
        'description': 'Formação de 350 horas, com encaminhamento para registro profissional de Comunicador.',
        'description_en': 'A 350-hour program with guidance toward professional Communicator registration.',
        'tone': 'emerald',
    },
    {
        'title': 'Arte e empreendedorismo',
        'title_en': 'Art and entrepreneurship',
        'description': 'Formações como Artista Empreendedor, Estilo de Comunicação e Conexão.',
        'description_en': 'Training such as Entrepreneur Artist, Communication Style and Connection.',
        'tone': 'white',
    },
    {
        'title': 'Eventos e palestras',
        'title_en': 'Events and talks',
        'description': 'Encontros, fórum de protagonismo juvenil e experiências formativas ao vivo.',
        'description_en': 'Meetups, a youth protagonism forum and live training experiences.',
        'tone': 'white',
    },
    {
        'title': 'Certificação e registro profissional',
        'title_en': 'Certification and professional registration',
        'description': 'Cursos com certificação e consulta de disponibilidade para autorização via sindicatos.',
        'description_en': 'Courses with certification and availability checks for authorization through unions.',
        'tone': 'slate',
    },
]

COURSE_AWARD = 'Vencedor do Prêmio Paulo Freire de Educação 2024'
COURSE_PROPOSAL_TITLE = 'Cursos para comunicação, cultura e presença profissional'
COURSE_PROPOSAL_TITLE_EN = 'Courses for communication, culture and professional presence'
COURSE_PROPOSAL_DESCRIPTION = 'Conheça formações profissionalizantes, cursos livres e mentorias para comunicar melhor, produzir cultura, conduzir eventos e destravar sua expressão.'
COURSE_PROPOSAL_DESCRIPTION_EN = 'Explore professional training, open courses and mentoring to communicate better, produce culture, host events and unlock your expression.'

COURSE_DETAIL_HOME_LABELS = {'Carga horária', 'Duração', 'Formato'}
COURSE_DETAIL_VALUE_TRANSLATIONS = {
    '350 horas': '350 hours',
    '18 meses': '18 months',
    '250 horas': '250 hours',
    '12 meses': '12 months',
    '30 horas': '30 hours',
    '50 horas': '50 hours',
    'Curso Livre': 'Open course',
    '20 horas': '20 hours',
    'Curso coletivo ou mentoria individual': 'Group course or individual mentoring',
}
COURSE_TRANSLATIONS = {
    'Comunicador Profissionalizante': {
        'title': 'Professional Communicator',
        'summary': 'Training to develop repertoire, presence and practical communication skills.',
    },
    'Produção Cultural': {
        'title': 'Cultural Production',
        'summary': 'Training for planning, organizing and delivering cultural projects.',
    },
    'Jornalismo Cultural': {
        'title': 'Cultural Journalism',
        'summary': 'For journalists, influencers and content producers.',
    },
    'Apresentação de Palco e Eventos': {
        'title': 'Stage and Event Presenting',
        'summary': 'Presenting and event-hosting techniques.',
    },
    'Espanhol – Conversação e Escrita': {
        'title': 'Spanish - Conversation and Writing',
        'summary': 'Development of oral and written communication.',
    },
    'Comunicação Destravada': {
        'title': 'Unlocked Communication',
        'summary': 'Development of public speaking, communication and self-confidence.',
    },
}

COURSE_GROUPS = [
    {
        'eyebrow': 'Formação profissionalizante',
        'title': 'Cursos com encaminhamento profissional',
        'description': 'Percursos mais completos para quem quer atuar com comunicação, produção e reconhecimento profissional.',
        'courses': [
            {
                'title': 'Comunicador Profissionalizante',
                'summary': 'Formação para desenvolver repertório, presença e prática de comunicação.',
                'details': [
                    {'label': 'Carga horária', 'value': '350 horas'},
                    {'label': 'Duração', 'value': '18 meses'},
                    {'label': 'Requisito', 'value': 'Ensino Médio completo'},
                ],
                'notes': ['Encaminhamento para registro profissional de Comunicador'],
                'highlight': True,
            },
            {
                'title': 'Produção Cultural',
                'summary': 'Formação para planejamento, organização e execução de projetos culturais.',
                'details': [
                    {'label': 'Carga horária', 'value': '250 horas'},
                    {'label': 'Duração', 'value': '12 meses'},
                    {'label': 'Requisito', 'value': 'Ensino Médio completo'},
                ],
                'notes': ['Encaminhamento para registro profissional Diretor de produção'],
                'highlight': True,
            },
        ],
    },
    {
        'eyebrow': 'Cursos livres',
        'title': 'Aprofundamentos para comunicação, palco e escrita',
        'description': 'Cursos objetivos para públicos específicos que querem técnica, segurança e prática aplicada.',
        'courses': [
            {
                'title': 'Jornalismo Cultural',
                'summary': 'Para jornalistas, influenciadores e produtores de conteúdo.',
                'details': [
                    {'label': 'Carga horária', 'value': '30 horas'},
                    {'label': 'Requisito', 'value': 'Graduação na área de Comunicação'},
                ],
                'notes': [],
                'highlight': False,
            },
            {
                'title': 'Apresentação de Palco e Eventos',
                'summary': 'Técnicas de apresentação e condução de eventos.',
                'details': [
                    {'label': 'Carga horária', 'value': '50 horas'},
                    {'label': 'Requisito', 'value': 'Ensino Médio completo'},
                ],
                'notes': [],
                'highlight': False,
            },
            {
                'title': 'Espanhol – Conversação e Escrita',
                'summary': 'Desenvolvimento da comunicação oral e escrita.',
                'details': [
                    {'label': 'Formato', 'value': 'Curso Livre'},
                    {'label': 'Requisito', 'value': 'Ensino Fundamental completo'},
                ],
                'notes': [],
                'highlight': False,
            },
        ],
    },
    {
        'eyebrow': 'Desenvolvimento pessoal e comunicação',
        'title': 'Comunicação com clareza, presença e autoconfiança',
        'description': 'Experiências para destravar a fala, organizar ideias e fortalecer a expressão pessoal.',
        'courses': [
            {
                'title': 'Comunicação Destravada',
                'summary': 'Desenvolvimento da oratória, comunicação e autoconfiança.',
                'details': [
                    {'label': 'Carga horária', 'value': '20 horas'},
                    {'label': 'Formato', 'value': 'Curso coletivo ou mentoria individual'},
                ],
                'notes': [],
                'highlight': True,
            },
        ],
    },
]


def _features_for_site(site, placement, fallback):
    features = list(
        SchoolFeature.on_site
        .filter(site=site, placement=placement, is_active=True)
        .order_by('order', 'title')
    )
    return features or fallback


def _course_features_for_home():
    cards = []
    for group_index, group in enumerate(COURSE_GROUPS):
        for course_index, course in enumerate(group['courses']):
            detail_values = [
                detail['value']
                for detail in course['details']
                if detail['label'] in COURSE_DETAIL_HOME_LABELS
            ]
            detail_values_en = [
                COURSE_DETAIL_VALUE_TRANSLATIONS.get(value, value)
                for value in detail_values
            ]
            course_translation = COURSE_TRANSLATIONS.get(course['title'], {})
            description = course['summary']
            description_en = course_translation.get('summary', course['summary'])
            if detail_values:
                description = f'{description} {" · ".join(detail_values)}.'
            if detail_values_en:
                description_en = f'{description_en} {" · ".join(detail_values_en)}.'
            cards.append({
                'title': course['title'],
                'title_en': course_translation.get('title', course['title']),
                'description': description,
                'description_en': description_en,
                'tone': 'slate' if (group_index + course_index) % 2 else 'emerald',
            })
    return cards


def home(request):
    site = request.site
    home_config = (
        SchoolHomeConfig.on_site
        .filter(site=site, is_active=True)
        .first()
        or HOME_FALLBACK
    )
    trust_features = _features_for_site(site, SchoolFeature.Placement.TRUST, TRUST_FEATURES_FALLBACK)
    proposal_features = _course_features_for_home()
    life_features = _features_for_site(site, SchoolFeature.Placement.LIFE, LIFE_FEATURES_FALLBACK)
    testimonials = Testimonial.on_site.filter(site=site, is_featured=True)[:3]
    return render(request, 'school/home.html', {
        'home_config': home_config,
        'trust_features': trust_features,
        'hero_features': trust_features[:2],
        'proposal_features': proposal_features,
        'course_proposal_title': COURSE_PROPOSAL_TITLE,
        'course_proposal_title_en': COURSE_PROPOSAL_TITLE_EN,
        'course_proposal_description': COURSE_PROPOSAL_DESCRIPTION,
        'course_proposal_description_en': COURSE_PROPOSAL_DESCRIPTION_EN,
        'life_features': life_features,
        'testimonials': testimonials,
    })


def page_detail(request, slug):
    page = get_object_or_404(Page.on_site, site=request.site, slug=slug, is_published=True)
    context = {'page': page}
    if page.slug == 'cursos':
        context.update({
            'course_award': COURSE_AWARD,
            'course_groups': COURSE_GROUPS,
        })
    return render(request, 'school/page_detail.html', context)


def team_list(request):
    return redirect('news:list')


def privacy(request):
    return render(request, 'school/privacy.html')


def about(request):
    return render(request, 'school/about.html')
