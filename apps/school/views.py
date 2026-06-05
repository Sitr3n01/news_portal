from django.shortcuts import get_object_or_404, redirect, render

from .models import Page, SchoolFeature, SchoolHomeConfig, TeamMember, Testimonial

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

TRUST_FEATURES_FALLBACK = [
    {'title': 'Mentorias com Kelly Farias', 'description': 'Acompanhamento para desenvolver presença, estilo de comunicação e clareza na expressão.', 'tone': 'emerald'},
    {'title': 'Cursos online, híbridos e presenciais', 'description': 'Formações flexíveis para comunicação, artes, liderança e produção.', 'tone': 'slate'},
    {'title': 'Atuação corporativa', 'description': 'Mentorias, palestras e comunicação interna para equipes e projetos.', 'tone': 'emerald'},
    {'title': 'Projeto Jovem Comunicador', 'description': 'Iniciativa social voltada a jovens em situação de vulnerabilidade social.', 'tone': 'slate'},
]

PROPOSAL_FEATURES_FALLBACK = [
    {'title': 'Comunicador Profissionalizante', 'description': 'Formação de 350 horas em 18 meses, com encaminhamento para registro profissional de Comunicador.', 'tone': 'emerald'},
    {'title': 'Produção Cultural', 'description': 'Formação de 250 horas em 12 meses, com encaminhamento para registro profissional Diretor de produção.', 'tone': 'slate'},
    {'title': 'Jornalismo Cultural', 'description': 'Curso livre de 30 horas para jornalistas, influenciadores e produtores de conteúdo.', 'tone': 'emerald'},
    {'title': 'Apresentação de Palco e Eventos', 'description': 'Curso livre de 50 horas com técnicas de apresentação e condução de eventos.', 'tone': 'slate'},
    {'title': 'Espanhol – Conversação e Escrita', 'description': 'Curso livre para desenvolvimento da comunicação oral e escrita.', 'tone': 'emerald'},
    {'title': 'Comunicação Destravada', 'description': '20 horas em curso coletivo ou mentoria individual para oratória, comunicação e autoconfiança.', 'tone': 'slate'},
]

LIFE_FEATURES_FALLBACK = [
    {'title': 'Comunicador Profissionalizante', 'description': 'Formação de 350 horas, com encaminhamento para registro profissional de Comunicador.', 'tone': 'emerald'},
    {'title': 'Arte e empreendedorismo', 'description': 'Formações como Artista Empreendedor, Estilo de Comunicação e Conexão.', 'tone': 'white'},
    {'title': 'Eventos e palestras', 'description': 'Encontros, fórum de protagonismo juvenil e experiências formativas ao vivo.', 'tone': 'white'},
    {'title': 'Certificação e registro profissional', 'description': 'Cursos com certificação e consulta de disponibilidade para autorização via sindicatos.', 'tone': 'slate'},
]

COURSE_AWARD = 'Vencedor do Prêmio Paulo Freire de Educação 2024'
COURSE_PROPOSAL_TITLE = 'Cursos para comunicação, cultura e presença profissional'
COURSE_PROPOSAL_DESCRIPTION = 'Conheça formações profissionalizantes, cursos livres e mentorias para comunicar melhor, produzir cultura, conduzir eventos e destravar sua expressão.'

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
                if detail['label'] in {'Carga horária', 'Duração', 'Formato'}
            ]
            description = course['summary']
            if detail_values:
                description = f'{description} {" · ".join(detail_values)}.'
            cards.append({
                'title': course['title'],
                'description': description,
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
        'course_proposal_description': COURSE_PROPOSAL_DESCRIPTION,
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
