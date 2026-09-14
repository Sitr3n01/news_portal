"""Catálogo da página Cursos. O slug de cada curso é fixo: o card leva a Contato com ?curso=<slug>, e o formulário
registra o curso de interesse a partir dele."""

COURSE_GROUPS = [
    {
        'eyebrow': 'Formação profissionalizante',
        'title': 'Cursos com encaminhamento profissional',
        'description': 'Percursos mais completos para quem quer atuar com comunicação, produção e reconhecimento profissional.',
        'courses': [
            {
                'slug': 'comunicador-profissionalizante',
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
                'slug': 'producao-cultural',
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
                'slug': 'jornalismo-cultural',
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
                'slug': 'apresentacao-de-palco-e-eventos',
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
                'slug': 'espanhol-conversacao-e-escrita',
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
                'slug': 'comunicacao-destravada',
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


def find_course(slug):
    """Curso do catálogo com esse slug, ou None para slug vazio ou desconhecido."""
    if not slug:
        return None
    for group in COURSE_GROUPS:
        for course in group['courses']:
            if course['slug'] == slug:
                return course
    return None
