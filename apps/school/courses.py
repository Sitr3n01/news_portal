"""Catálogo da página Cursos. O slug de cada curso é fixo: o card leva a Contato com ?curso=<slug>, e o formulário
registra o curso de interesse a partir dele. Cada texto tem a versão em inglês ao lado, com o sufixo _en."""

COURSE_GROUPS = [
    {
        'eyebrow': 'Formação profissionalizante',
        'eyebrow_en': 'Professional training',
        'title': 'Cursos com encaminhamento profissional',
        'title_en': 'Courses with professional pathways',
        'description': 'Percursos mais completos para quem quer atuar com comunicação, produção e reconhecimento profissional.',
        'description_en': 'More complete tracks for those who want to work in communication and production with professional recognition.',
        'courses': [
            {
                'slug': 'comunicador-profissionalizante',
                'title': 'Comunicador Profissionalizante',
                'title_en': 'Professional Communicator',
                'summary': 'Formação para desenvolver repertório, presença e prática de comunicação.',
                'summary_en': 'Training to build repertoire, presence and communication practice.',
                'details': [
                    {'label': 'Carga horária', 'label_en': 'Course hours', 'value': '350 horas', 'value_en': '350 hours'},
                    {'label': 'Duração', 'label_en': 'Duration', 'value': '18 meses', 'value_en': '18 months'},
                    {'label': 'Requisito', 'label_en': 'Requirement', 'value': 'Ensino Médio completo', 'value_en': 'Completed high school'},
                ],
                'notes': [
                    {'text': 'Encaminhamento para registro profissional de Comunicador', 'text_en': 'Guidance toward professional Communicator registration'},
                ],
                'highlight': True,
            },
            {
                'slug': 'producao-cultural',
                'title': 'Produção Cultural',
                'title_en': 'Cultural Production',
                'summary': 'Formação para planejamento, organização e execução de projetos culturais.',
                'summary_en': 'Training in planning, organizing and running cultural projects.',
                'details': [
                    {'label': 'Carga horária', 'label_en': 'Course hours', 'value': '250 horas', 'value_en': '250 hours'},
                    {'label': 'Duração', 'label_en': 'Duration', 'value': '12 meses', 'value_en': '12 months'},
                    {'label': 'Requisito', 'label_en': 'Requirement', 'value': 'Ensino Médio completo', 'value_en': 'Completed high school'},
                ],
                'notes': [
                    {'text': 'Encaminhamento para registro profissional Diretor de produção', 'text_en': 'Guidance toward professional Production Director registration'},
                ],
                'highlight': True,
            },
        ],
    },
    {
        'eyebrow': 'Cursos livres',
        'eyebrow_en': 'Open courses',
        'title': 'Aprofundamentos para comunicação, palco e escrita',
        'title_en': 'Deep dives into communication, stage and writing',
        'description': 'Cursos objetivos para públicos específicos que querem técnica, segurança e prática aplicada.',
        'description_en': 'Focused courses for specific audiences who want technique, confidence and applied practice.',
        'courses': [
            {
                'slug': 'jornalismo-cultural',
                'title': 'Jornalismo Cultural',
                'title_en': 'Cultural Journalism',
                'summary': 'Para jornalistas, influenciadores e produtores de conteúdo.',
                'summary_en': 'For journalists, influencers and content producers.',
                'details': [
                    {'label': 'Carga horária', 'label_en': 'Course hours', 'value': '30 horas', 'value_en': '30 hours'},
                    {'label': 'Requisito', 'label_en': 'Requirement', 'value': 'Graduação na área de Comunicação', 'value_en': 'Degree in Communication'},
                ],
                'notes': [],
                'highlight': False,
            },
            {
                'slug': 'apresentacao-de-palco-e-eventos',
                'title': 'Apresentação de Palco e Eventos',
                'title_en': 'Stage and Event Presenting',
                'summary': 'Técnicas de apresentação e condução de eventos.',
                'summary_en': 'Presenting and event-hosting techniques.',
                'details': [
                    {'label': 'Carga horária', 'label_en': 'Course hours', 'value': '50 horas', 'value_en': '50 hours'},
                    {'label': 'Requisito', 'label_en': 'Requirement', 'value': 'Ensino Médio completo', 'value_en': 'Completed high school'},
                ],
                'notes': [],
                'highlight': False,
            },
            {
                'slug': 'espanhol-conversacao-e-escrita',
                'title': 'Espanhol – Conversação e Escrita',
                'title_en': 'Spanish – Conversation and Writing',
                'summary': 'Desenvolvimento da comunicação oral e escrita.',
                'summary_en': 'Development of oral and written communication.',
                'details': [
                    {'label': 'Formato', 'label_en': 'Format', 'value': 'Curso Livre', 'value_en': 'Open course'},
                    {'label': 'Requisito', 'label_en': 'Requirement', 'value': 'Ensino Fundamental completo', 'value_en': 'Completed middle school'},
                ],
                'notes': [],
                'highlight': False,
            },
        ],
    },
    {
        'eyebrow': 'Desenvolvimento pessoal e comunicação',
        'eyebrow_en': 'Personal development and communication',
        'title': 'Comunicação com clareza, presença e autoconfiança',
        'title_en': 'Communication with clarity, presence and self-confidence',
        'description': 'Experiências para destravar a fala, organizar ideias e fortalecer a expressão pessoal.',
        'description_en': 'Experiences to unlock your speech, organize ideas and strengthen personal expression.',
        'courses': [
            {
                'slug': 'comunicacao-destravada',
                'title': 'Comunicação Destravada',
                'title_en': 'Unlocked Communication',
                'summary': 'Desenvolvimento da oratória, comunicação e autoconfiança.',
                'summary_en': 'Development of public speaking, communication and self-confidence.',
                'details': [
                    {'label': 'Carga horária', 'label_en': 'Course hours', 'value': '20 horas', 'value_en': '20 hours'},
                    {'label': 'Formato', 'label_en': 'Format', 'value': 'Curso coletivo ou mentoria individual', 'value_en': 'Group course or individual mentoring'},
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
