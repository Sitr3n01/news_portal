"""Catálogo da página Cursos. O slug de cada curso é fixo: o card leva à página detalhada do curso, cujo CTA segue
para Contato com ?curso=<slug>, e o formulário registra o curso de interesse a partir dele. Cada texto tem a versão
em inglês ao lado, com o sufixo _en (em listas de string simples, como "intro", "body" e "lines", cada item virou
{'text': ..., 'text_en': ...} para manter o par). A chave "page" guarda o conteúdo da página detalhada de cada
curso, incluindo sua tradução; find_course() é usado por apps.school.views.course_detail e por apps.contact.
meta_description não tem _en: é renderizada só no servidor (Django), e o idioma da página é uma preferência só do
cliente (Alpine/localStorage, ver static/js/school-editorial.js) que não chega até a view."""

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
                'page': {
                    'hero_tagline': 'Transforme sua comunicação em uma habilidade profissional.',
                    'hero_tagline_en': 'Turn your communication into a professional skill.',
                    'hero_cta_label': 'Tenho interesse neste curso',
                    'hero_cta_label_en': "I'm interested in this course",
                    'meta_description': (
                        'Formação profissionalizante de 350 horas em rádio, TV, publicidade e comunicação, com estágio '
                        'supervisionado e encaminhamento profissional na Escola Komuniki.'
                    ),
                    'intro': [
                        {
                            'text': (
                                'Comunicar bem é mais do que falar com desenvoltura. É compreender a mensagem, adaptar a '
                                'linguagem ao público, desenvolver presença e utilizar voz, expressão e repertório de '
                                'maneira consciente.'
                            ),
                            'text_en': (
                                'Communicating well is more than speaking with ease. It means understanding the message, '
                                'adapting language to the audience, developing presence, and using voice, expression and '
                                'repertoire consciously.'
                            ),
                        },
                        {
                            'text': (
                                'O Curso de Comunicador Profissionalizante da Escola Komuniki foi desenvolvido para quem '
                                'deseja ingressar ou se aperfeiçoar no universo da comunicação, explorando possibilidades '
                                'relacionadas a rádio, televisão, publicidade, eventos, produção de conteúdo e diferentes '
                                'plataformas.'
                            ),
                            'text_en': (
                                "The Komuniki School's Professional Communicator course was designed for anyone who wants "
                                'to enter or grow within the world of communication, exploring possibilities in radio, '
                                'television, advertising, events, content production and different platforms.'
                            ),
                        },
                    ],
                    'sections': [
                        {
                            'kind': 'cards',
                            'eyebrow': 'Áreas de formação',
                            'eyebrow_en': 'Training areas',
                            'title': 'Uma formação para diferentes formas de comunicar',
                            'title_en': 'One training, many ways to communicate',
                            'lead': (
                                'Durante a formação, o aluno entra em contato com diferentes áreas da comunicação e '
                                'desenvolve recursos que podem ser utilizados diante de um microfone, de uma câmera, '
                                'de uma plateia ou na produção de conteúdos. A proposta é unir conhecimento, prática e '
                                'desenvolvimento da expressão para construir uma comunicação cada vez mais clara, '
                                'segura e adequada ao contexto profissional.'
                            ),
                            'lead_en': (
                                'Throughout the training, students engage with different areas of communication and '
                                'build skills they can use in front of a microphone, a camera, an audience, or when '
                                'producing content. The aim is to combine knowledge, practice and the development of '
                                'expression to build communication that is clearer, more confident and better suited '
                                'to a professional context.'
                            ),
                            'items': [
                                {
                                    'title': 'Rádio e Locução',
                                    'title_en': 'Radio and Voiceover',
                                    'body': (
                                        'Desenvolvimento de voz, dicção, leitura, interpretação e técnicas de locução '
                                        'aplicadas ao rádio e a outras formas de comunicação sonora. O objetivo é '
                                        'compreender como ritmo, intenção, articulação e interpretação modificam a '
                                        'maneira como uma mensagem é recebida.'
                                    ),
                                    'body_en': (
                                        'Development of voice, diction, reading, interpretation and voiceover '
                                        'techniques applied to radio and other forms of audio communication. The '
                                        'goal is to understand how rhythm, intent, articulation and delivery change '
                                        'the way a message is received.'
                                    ),
                                },
                                {
                                    'title': 'Televisão e Apresentação',
                                    'title_en': 'Television and Presenting',
                                    'body': (
                                        'Postura diante das câmeras, apresentação, entrevistas, construção de textos e '
                                        'comunicação para conteúdos audiovisuais — saber o que dizer e também como '
                                        'transmitir a mensagem de forma natural, organizada e compreensível.'
                                    ),
                                    'body_en': (
                                        'On-camera posture, presenting, interviews, script writing and communication '
                                        'for audiovisual content — knowing what to say, and also how to deliver the '
                                        'message in a natural, organized and clear way.'
                                    ),
                                },
                                {
                                    'title': 'Publicidade e Comunicação',
                                    'title_en': 'Advertising and Communication',
                                    'body': (
                                        'Fundamentos ligados à publicidade, comunicação com diferentes públicos, '
                                        'criação de conteúdos e desenvolvimento de mensagens, ampliando a percepção '
                                        'sobre como linguagem, público e objetivo se relacionam.'
                                    ),
                                    'body_en': (
                                        'Fundamentals of advertising, communicating with different audiences, '
                                        'content creation and message development, broadening the understanding of '
                                        'how language, audience and objective relate to one another.'
                                    ),
                                },
                                {
                                    'title': 'Legislação e Ética Profissional',
                                    'title_en': 'Law and Professional Ethics',
                                    'body': (
                                        'Conhecimentos sobre legislação, ética e responsabilidade profissional, '
                                        'contribuindo para uma atuação mais consciente no mercado de comunicação.'
                                    ),
                                    'body_en': (
                                        'Knowledge of law, ethics and professional responsibility, contributing to a '
                                        'more conscious approach to working in the communication field.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'prose',
                            'eyebrow': 'Formação prática',
                            'eyebrow_en': 'Hands-on training',
                            'title': 'Técnica, prática e desenvolvimento pessoal',
                            'title_en': 'Technique, practice and personal development',
                            'body': [
                                {
                                    'text': (
                                        'Ao longo das 350 horas, o estudante é estimulado a desenvolver não apenas '
                                        'conhecimentos técnicos, mas também aspectos importantes para sua presença como '
                                        'comunicador — voz, postura, expressão, interpretação, segurança para falar e '
                                        'capacidade de organizar uma mensagem.'
                                    ),
                                    'text_en': (
                                        'Throughout the 350 hours, students are encouraged to develop not only '
                                        'technical knowledge but also qualities that matter for their presence as '
                                        'communicators — voice, posture, expression, delivery, confidence when '
                                        'speaking and the ability to organize a message.'
                                    ),
                                },
                                {
                                    'text': 'A formação possui conteúdo teórico, atividades práticas, vivências relacionadas ao mercado e estágio supervisionado.',
                                    'text_en': 'The course combines theoretical content, hands-on activities, real-world experiences and supervised internship.',
                                },
                            ],
                        },
                        {
                            'kind': 'list',
                            'eyebrow': 'Público',
                            'eyebrow_en': "Who it's for",
                            'title': 'Para quem é este curso?',
                            'title_en': 'Who is this course for?',
                            'lead': 'O Comunicador Profissionalizante pode ser uma opção para quem deseja:',
                            'lead_en': 'The Professional Communicator course can be a good fit for anyone who wants to:',
                            'items': [
                                {'text': 'Trabalhar com rádio e locução', 'text_en': 'Work with radio and voiceover'},
                                {'text': 'Desenvolver apresentação para televisão e vídeo', 'text_en': 'Develop presenting skills for television and video'},
                                {'text': 'Apresentar programas, projetos ou eventos', 'text_en': 'Host programs, projects or events'},
                                {'text': 'Produzir conteúdo para plataformas digitais', 'text_en': 'Produce content for digital platforms'},
                                {'text': 'Atuar com publicidade e comunicação', 'text_en': 'Work in advertising and communication'},
                                {'text': 'Desenvolver mais segurança diante das câmeras', 'text_en': 'Build more confidence on camera'},
                                {'text': 'Aprimorar voz, postura e expressão', 'text_en': 'Improve voice, posture and expression'},
                                {'text': 'Transformar uma habilidade de comunicação em atividade profissional', 'text_en': 'Turn a communication skill into a profession'},
                                {'text': 'Desenvolver confiança para falar diante de outras pessoas', 'text_en': 'Build confidence speaking in front of others'},
                            ],
                            'note': (
                                'Não é necessário chegar ao curso sabendo apresentar ou dominando técnicas '
                                'profissionais de comunicação: a formação existe justamente para desenvolver essas '
                                'competências ao longo do processo.'
                            ),
                            'note_en': (
                                "You don't need to already know how to present or master professional communication "
                                'techniques before joining: the course exists precisely to develop these skills '
                                'along the way.'
                            ),
                        },
                        {
                            'kind': 'list',
                            'eyebrow': 'Diferenciais',
                            'eyebrow_en': 'Highlights',
                            'title': 'Diferenciais da formação',
                            'title_en': 'What sets this course apart',
                            'items': [
                                {'text': '350 horas de formação profissionalizante', 'text_en': '350 hours of professional training'},
                                {'text': 'Formação multidisciplinar em comunicação', 'text_en': 'Multidisciplinary training in communication'},
                                {'text': 'Integração entre conteúdo teórico e atividades práticas', 'text_en': 'Theory and hands-on practice combined'},
                                {'text': 'Desenvolvimento de voz, postura e expressão', 'text_en': 'Voice, posture and expression development'},
                                {'text': 'Experiências relacionadas ao ambiente profissional', 'text_en': 'Experiences connected to the professional environment'},
                                {'text': 'Professores e profissionais com experiência na área', 'text_en': 'Teachers and working professionals in the field'},
                                {'text': 'Estágio supervisionado', 'text_en': 'Supervised internship'},
                                {'text': 'Certificação ao final da formação', 'text_en': 'Certificate upon completion'},
                                {'text': 'Orientação para os próximos passos profissionais', 'text_en': 'Guidance on next professional steps'},
                                {'text': 'Encaminhamento para registro profissional de Comunicador', 'text_en': 'Guidance toward professional Communicator registration'},
                            ],
                        },
                    ],
                    'final_cta': {
                        'title': 'Sua voz pode ser o começo de uma nova profissão.',
                        'title_en': 'Your voice can be the start of a new profession.',
                        'text': (
                            'Uma boa comunicação pode informar, apresentar, representar ideias, conduzir conversas e '
                            'criar conexões. Na Komuniki, a proposta é ajudar o aluno a transformar essa capacidade em '
                            'técnica, repertório e presença profissional.'
                        ),
                        'text_en': (
                            'Good communication can inform, present, represent ideas, guide conversations and build '
                            'connections. At Komuniki, the goal is to help students turn that ability into technique, '
                            'repertoire and professional presence.'
                        ),
                        'primary_label': 'Quero saber mais sobre o curso',
                        'primary_label_en': 'I want to know more about the course',
                        'secondary_label': 'Falar com a Komuniki',
                        'secondary_label_en': 'Talk to Komuniki',
                    },
                },
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
                'page': {
                    'hero_tagline': 'Aprenda a transformar ideias culturais em projetos.',
                    'hero_tagline_en': 'Learn how to turn cultural ideas into projects.',
                    'hero_cta_label': 'Tenho interesse neste curso',
                    'hero_cta_label_en': "I'm interested in this course",
                    'meta_description': (
                        'Formação profissionalizante de 250 horas em planejamento, organização e execução de projetos '
                        'culturais, com encaminhamento profissional na Escola Komuniki.'
                    ),
                    'intro': [
                        {
                            'text': (
                                'Por trás de apresentações, eventos, projetos artísticos e diferentes iniciativas '
                                'culturais existe um trabalho de planejamento, organização e execução.'
                            ),
                            'text_en': (
                                'Behind every performance, event, artistic project and cultural initiative lies work '
                                'of planning, organization and execution.'
                            ),
                        },
                        {
                            'text': (
                                'O Curso de Produção Cultural da Escola Komuniki é uma formação profissionalizante '
                                'voltada para quem deseja compreender melhor esse processo e se preparar para participar '
                                'da realização de projetos culturais.'
                            ),
                            'text_en': (
                                "The Komuniki School's Cultural Production course is a professional training program "
                                'for anyone who wants to better understand this process and prepare to take part in '
                                'producing cultural projects.'
                            ),
                        },
                    ],
                    'sections': [
                        {
                            'kind': 'cards',
                            'eyebrow': 'Como o curso é organizado',
                            'eyebrow_en': 'How the course is organized',
                            'title': 'Da ideia à realização',
                            'title_en': 'From idea to reality',
                            'lead': (
                                'Produzir cultura exige enxergar um projeto como um conjunto de etapas: organizar '
                                'ideias, compreender necessidades, trabalhar com pessoas, acompanhar processos e '
                                'contribuir para que aquilo que foi planejado aconteça. A formação busca desenvolver '
                                'essa visão mais ampla da produção.'
                            ),
                            'lead_en': (
                                'Producing culture means seeing a project as a set of stages: organizing ideas, '
                                'understanding needs, working with people, following processes and helping what was '
                                'planned actually happen. The course aims to build this broader view of production.'
                            ),
                            'items': [
                                {
                                    'title': 'Planejamento',
                                    'title_en': 'Planning',
                                    'body': (
                                        'Projetos precisam começar com clareza sobre aquilo que se deseja realizar. O '
                                        'aluno desenvolve uma visão mais organizada sobre objetivos, necessidades, '
                                        'prioridades e etapas de uma produção.'
                                    ),
                                    'body_en': (
                                        'Projects need to start with clarity about what is meant to be achieved. '
                                        "Students develop a more organized view of a production's goals, needs, "
                                        'priorities and stages.'
                                    ),
                                },
                                {
                                    'title': 'Organização',
                                    'title_en': 'Organization',
                                    'body': (
                                        'Produção também significa acompanhar diversas partes de um mesmo projeto. '
                                        'Desenvolver organização ajuda o profissional a lidar com informações, '
                                        'equipes, demandas e diferentes momentos de uma iniciativa cultural.'
                                    ),
                                    'body_en': (
                                        'Production also means keeping track of many parts of the same project at '
                                        'once. Building organizational skills helps professionals handle '
                                        'information, teams, demands and the different moments of a cultural '
                                        'initiative.'
                                    ),
                                },
                                {
                                    'title': 'Execução',
                                    'title_en': 'Execution',
                                    'body': (
                                        'Planejar é apenas parte do trabalho. A produção cultural também exige '
                                        'acompanhar a realização do projeto e responder às necessidades que surgem '
                                        'durante a execução.'
                                    ),
                                    'body_en': (
                                        'Planning is only part of the job. Cultural production also requires '
                                        'following the project through and responding to needs that come up during '
                                        'execution.'
                                    ),
                                },
                                {
                                    'title': 'Comunicação',
                                    'title_en': 'Communication',
                                    'body': (
                                        'Um produtor está constantemente em contato com pessoas. Artistas, '
                                        'profissionais, equipes e participantes de um projeto precisam compreender o '
                                        'que está acontecendo e qual é o papel de cada um: comunicação e organização '
                                        'caminham juntas.'
                                    ),
                                    'body_en': (
                                        "A producer is constantly in contact with people. Artists, professionals, "
                                        "teams and everyone involved in a project need to understand what's "
                                        'happening and what their role is: communication and organization go hand '
                                        'in hand.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'list',
                            'eyebrow': 'Público',
                            'eyebrow_en': "Who it's for",
                            'title': 'Para quem é este curso?',
                            'title_en': 'Who is this course for?',
                            'lead': 'A formação pode interessar a quem deseja:',
                            'lead_en': 'This course may be a good fit for anyone who wants to:',
                            'items': [
                                {'text': 'Trabalhar com projetos culturais', 'text_en': 'Work with cultural projects'},
                                {'text': 'Participar da organização de eventos e iniciativas artísticas', 'text_en': 'Take part in organizing events and artistic initiatives'},
                                {'text': 'Compreender melhor os processos de produção', 'text_en': 'Better understand production processes'},
                                {'text': 'Transformar uma ideia cultural em um projeto organizado', 'text_en': 'Turn a cultural idea into an organized project'},
                                {'text': 'Atuar nos bastidores de produções', 'text_en': 'Work behind the scenes of productions'},
                                {'text': 'Desenvolver capacidade de planejamento e organização', 'text_en': 'Build planning and organizational skills'},
                                {'text': 'Ampliar conhecimentos sobre o setor cultural', 'text_en': 'Broaden their knowledge of the cultural sector'},
                            ],
                            'note': (
                                'Também pode ser interessante para artistas e comunicadores que desejam compreender '
                                'melhor o que acontece além do palco ou da criação artística.'
                            ),
                            'note_en': (
                                'It can also be valuable for artists and communicators who want to better understand '
                                'what happens beyond the stage or the creative work itself.'
                            ),
                        },
                        {
                            'kind': 'prose',
                            'eyebrow': 'Formação profissionalizante',
                            'eyebrow_en': 'Professional training',
                            'title': 'Um percurso de 250 horas',
                            'title_en': 'A 250-hour course',
                            'body': [
                                {
                                    'text': (
                                        'Distribuído ao longo de 12 meses, o curso oferece um percurso mais aprofundado '
                                        'para quem deseja se preparar para atividades relacionadas à produção cultural.'
                                    ),
                                    'text_en': (
                                        'Spread across 12 months, the course offers a deeper path for anyone '
                                        'preparing to work in cultural production.'
                                    ),
                                },
                                {
                                    'text': 'A formação possui encaminhamento para registro profissional de Diretor de Produção.',
                                    'text_en': 'The course includes guidance toward professional Production Director registration.',
                                },
                            ],
                        },
                    ],
                    'final_cta': {
                        'title': 'Cultura também precisa de quem faça acontecer.',
                        'title_en': 'Culture also needs people who make it happen.',
                        'text': (
                            'Uma ideia pode iniciar um projeto. A produção é o trabalho que ajuda essa ideia a '
                            'encontrar organização, pessoas e caminhos para se tornar realidade.'
                        ),
                        'text_en': (
                            'An idea can start a project. Production is the work that helps that idea find '
                            'organization, people and a path to becoming reality.'
                        ),
                        'primary_label': 'Quero saber mais sobre Produção Cultural',
                        'primary_label_en': 'I want to know more about Cultural Production',
                        'secondary_label': 'Falar com a Komuniki',
                        'secondary_label_en': 'Talk to Komuniki',
                    },
                },
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
                'page': {
                    'hero_tagline': 'Transforme cultura, arte e conhecimento em informação.',
                    'hero_tagline_en': 'Turn culture, art and knowledge into information.',
                    'hero_cta_label': 'Quero conhecer o Jornalismo Cultural',
                    'hero_cta_label_en': 'I want to learn about Cultural Journalism',
                    'meta_description': (
                        'Curso livre de 30 horas em jornalismo cultural: apuração, entrevistas, texto jornalístico e '
                        'cobertura de eventos para profissionais de Comunicação.'
                    ),
                    'intro': [
                        {
                            'text': (
                                'Cultura também é notícia. Cinema, música, teatro, literatura, artes visuais, patrimônio, '
                                'festivais e diferentes manifestações culturais produzem histórias que podem ser '
                                'pesquisadas, documentadas e apresentadas ao público por meio do jornalismo.'
                            ),
                            'text_en': (
                                'Culture is news too. Film, music, theater, literature, visual arts, heritage, '
                                'festivals and other forms of cultural expression produce stories that can be '
                                'researched, documented and brought to the public through journalism.'
                            ),
                        },
                        {
                            'text': (
                                'O Curso de Jornalismo Cultural da Escola Komuniki é uma formação de 30 horas voltada ao '
                                'desenvolvimento da produção jornalística aplicada ao universo da cultura, arte, '
                                'entretenimento e patrimônio. Durante o curso, o aluno entra em contato com diferentes '
                                'etapas da cobertura cultural e desenvolve recursos para pesquisar pautas, realizar '
                                'entrevistas, produzir matérias, acompanhar eventos e transformar acontecimentos '
                                'culturais em conteúdo.'
                            ),
                            'text_en': (
                                "The Komuniki School's Cultural Journalism course is a 30-hour program focused on "
                                'developing journalistic production applied to culture, art, entertainment and '
                                'heritage. Throughout the course, students engage with the different stages of '
                                'cultural coverage and build the skills to research story ideas, conduct interviews, '
                                'produce articles, cover events and turn cultural happenings into content.'
                            ),
                        },
                    ],
                    'sections': [
                        {
                            'kind': 'prose',
                            'eyebrow': 'Por que jornalismo cultural',
                            'eyebrow_en': 'Why cultural journalism',
                            'title': 'Cultura também precisa ser pesquisada, contextualizada e contada',
                            'title_en': 'Culture also needs to be researched, put in context and told',
                            'body': [
                                {
                                    'text': (
                                        'Produzir conteúdo cultural vai além de divulgar que um evento aconteceu ou dizer '
                                        'se uma obra é boa ou ruim. O jornalismo cultural procura compreender contextos, '
                                        'identificar histórias, ouvir pessoas envolvidas e transformar essas informações '
                                        'em conteúdos que ajudem o público a conhecer melhor uma obra, um artista, um '
                                        'movimento ou um acontecimento.'
                                    ),
                                    'text_en': (
                                        'Producing cultural content goes beyond announcing that an event happened or '
                                        'saying whether a work is good or bad. Cultural journalism seeks to '
                                        'understand context, find stories, listen to the people involved and turn '
                                        'that information into content that helps the audience get to know a work, '
                                        'an artist, a movement or an event.'
                                    ),
                                },
                                {
                                    'text': 'Para isso, é necessário desenvolver repertório, capacidade de pesquisa e domínio das ferramentas jornalísticas.',
                                    'text_en': "To do this, it's necessary to build repertoire, research skills and a solid command of journalistic tools.",
                                },
                            ],
                        },
                        {
                            'kind': 'cards',
                            'eyebrow': 'Conteúdo do curso',
                            'eyebrow_en': 'Course content',
                            'title': 'O que você vai desenvolver',
                            'title_en': 'What you will develop',
                            'items': [
                                {
                                    'title': 'Fundamentos do jornalismo cultural',
                                    'title_en': 'Fundamentals of cultural journalism',
                                    'body': (
                                        'Características da cobertura jornalística voltada para cultura, observando '
                                        'esse universo também como fonte de pautas, histórias e informação.'
                                    ),
                                    'body_en': (
                                        'The traits of journalistic coverage focused on culture, looking at this '
                                        'world also as a source of story ideas, narratives and information.'
                                    ),
                                },
                                {
                                    'title': 'Apuração e pesquisa de pautas culturais',
                                    'title_en': 'Research and cultural story development',
                                    'body': (
                                        'Pesquisar contexto, buscar informações, identificar fontes e compreender '
                                        'aquilo que será abordado: ferramentas para encontrar e estruturar pautas '
                                        'culturais.'
                                    ),
                                    'body_en': (
                                        'Researching context, gathering information, identifying sources and '
                                        'understanding the subject at hand: tools for finding and structuring '
                                        'cultural stories.'
                                    ),
                                },
                                {
                                    'title': 'Produção de matérias e reportagens',
                                    'title_en': 'Producing articles and features',
                                    'body': (
                                        'Organização das informações e construção de matérias e reportagens que '
                                        'apresentem acontecimentos culturais de forma clara, contextualizada e '
                                        'interessante.'
                                    ),
                                    'body_en': (
                                        'Organizing information and building articles and features that present '
                                        'cultural events in a clear, well-contextualized and engaging way.'
                                    ),
                                },
                                {
                                    'title': 'Entrevistas com artistas e agentes culturais',
                                    'title_en': 'Interviewing artists and cultural players',
                                    'body': (
                                        'Preparar perguntas, pesquisar previamente o entrevistado, saber ouvir e '
                                        'identificar caminhos durante a conversa com artistas, produtores e gestores '
                                        'culturais.'
                                    ),
                                    'body_en': (
                                        'Preparing questions, researching the interviewee beforehand, knowing how '
                                        'to listen and finding direction during conversations with artists, '
                                        'producers and cultural managers.'
                                    ),
                                },
                                {
                                    'title': 'Texto jornalístico',
                                    'title_en': 'Journalistic writing',
                                    'body': (
                                        'Técnicas de escrita jornalística e organização textual aplicadas à produção '
                                        'de conteúdo cultural, com clareza, contexto e escolha das informações.'
                                    ),
                                    'body_en': (
                                        'Journalistic writing techniques and text organization applied to cultural '
                                        'content production, with clarity, context and careful choice of '
                                        'information.'
                                    ),
                                },
                                {
                                    'title': 'Cobertura de eventos culturais',
                                    'title_en': 'Covering cultural events',
                                    'body': (
                                        'Observar o evento, identificar informações importantes, conversar com '
                                        'fontes e organizar tudo em uma narrativa: a lógica de acompanhamento e '
                                        'cobertura de shows, festivais, espetáculos e exposições.'
                                    ),
                                    'body_en': (
                                        'Observing the event, identifying important information, talking to '
                                        'sources and organizing it all into a narrative: the logic behind '
                                        'following and covering shows, festivals, performances and exhibitions.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'cards',
                            'eyebrow': 'Plataformas',
                            'eyebrow_en': 'Platforms',
                            'title': 'Jornalismo em diferentes plataformas',
                            'title_en': 'Journalism across different platforms',
                            'items': [
                                {
                                    'title': 'Rádio',
                                    'title_en': 'Radio',
                                    'body': 'Construção de conteúdos culturais pensando nas características da comunicação sonora.',
                                    'body_en': 'Building cultural content with the traits of audio communication in mind.',
                                },
                                {
                                    'title': 'Televisão e audiovisual',
                                    'title_en': 'Television and audiovisual',
                                    'body': 'Produção de informação considerando imagem, apresentação e linguagem audiovisual.',
                                    'body_en': 'Producing information with image, presenting and audiovisual language in mind.',
                                },
                                {
                                    'title': 'Mídias digitais',
                                    'title_en': 'Digital media',
                                    'body': (
                                        'Adaptação da comunicação jornalística para plataformas digitais e novos '
                                        'formatos de consumo de informação.'
                                    ),
                                    'body_en': (
                                        'Adapting journalistic communication for digital platforms and new formats '
                                        'of information consumption.'
                                    ),
                                },
                                {
                                    'title': 'Redes sociais',
                                    'title_en': 'Social media',
                                    'body': (
                                        'Conteúdos culturais que informam e contextualizam sem abandonar os '
                                        'princípios da comunicação jornalística.'
                                    ),
                                    'body_en': (
                                        'Cultural content that informs and provides context without abandoning the '
                                        'principles of journalistic communication.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'quote',
                            'title': 'Como encontrar uma boa pauta cultural?',
                            'title_en': 'How do you find a good cultural story?',
                            'lead': (
                                'Nem toda pauta precisa começar em um grande lançamento. Uma manifestação cultural '
                                'local, um projeto independente, um artista, uma tradição, um patrimônio ou uma '
                                'transformação dentro de determinada cena também podem gerar histórias relevantes. O '
                                'jornalista cultural aprende a observar aquilo que acontece ao seu redor e a '
                                'perguntar:'
                            ),
                            'lead_en': (
                                "Not every story needs to start with a big release. A local cultural expression, an "
                                'independent project, an artist, a tradition, a piece of heritage or a shift within '
                                "a given scene can also produce stories worth telling. Cultural journalists learn "
                                "to observe what's happening around them and to ask:"
                            ),
                            'lines': [
                                {'text': 'Que história existe aqui?', 'text_en': 'What story is here?'},
                                {'text': 'Por que ela importa?', 'text_en': 'Why does it matter?'},
                                {'text': 'Quem precisa ser ouvido?', 'text_en': 'Who needs to be heard?'},
                                {'text': 'Como essa história pode ser apresentada ao público?', 'text_en': 'How can this story be presented to the public?'},
                            ],
                        },
                        {
                            'kind': 'prose',
                            'eyebrow': 'Responsabilidade',
                            'eyebrow_en': 'Responsibility',
                            'title': 'Ética e responsabilidade',
                            'title_en': 'Ethics and responsibility',
                            'body': [
                                {
                                    'text': (
                                        'A comunicação cultural também envolve responsabilidade. Produzir conteúdos '
                                        'sobre pessoas, obras, comunidades e manifestações culturais exige cuidado com '
                                        'informações, fontes e contextos: por isso, ética e responsabilidade fazem parte '
                                        'da formação.'
                                    ),
                                    'text_en': (
                                        "Cultural communication also carries responsibility. Producing content "
                                        'about people, works, communities and cultural expressions requires care '
                                        "with information, sources and context: that's why ethics and "
                                        'responsibility are part of the course.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'list',
                            'eyebrow': 'Público',
                            'eyebrow_en': "Who it's for",
                            'title': 'Para quem é o curso?',
                            'title_en': 'Who is this course for?',
                            'lead': (
                                'O Jornalismo Cultural é voltado para profissionais da área de Comunicação que '
                                'desejam aprofundar sua capacidade de produzir conteúdos relacionados à cultura. '
                                'Pode ser especialmente interessante para:'
                            ),
                            'lead_en': (
                                'Cultural Journalism is aimed at Communication professionals who want to deepen '
                                'their ability to produce culture-related content. It can be especially valuable '
                                'for:'
                            ),
                            'items': [
                                {'text': 'Jornalistas', 'text_en': 'Journalists'},
                                {'text': 'Comunicadores', 'text_en': 'Communicators'},
                                {'text': 'Produtores culturais', 'text_en': 'Cultural producers'},
                                {'text': 'Profissionais da cultura', 'text_en': 'Culture professionals'},
                                {'text': 'Artistas e agentes culturais', 'text_en': 'Artists and cultural players'},
                                {'text': 'Criadores de conteúdo', 'text_en': 'Content creators'},
                                {'text': 'Assessores de comunicação', 'text_en': 'Communication advisors'},
                                {'text': 'Profissionais que trabalham com divulgação cultural', 'text_en': 'Professionals working in cultural promotion'},
                                {'text': 'Pessoas da área de Comunicação interessadas em cobertura cultural', 'text_en': 'Communication professionals interested in cultural coverage'},
                            ],
                        },
                    ],
                    'final_cta': {
                        'title': 'Do acontecimento à história.',
                        'title_en': 'From event to story.',
                        'text': (
                            'Todos os dias, artistas, produtores, grupos e comunidades criam projetos que '
                            'movimentam a cultura. O jornalismo cultural ajuda essas histórias a encontrarem '
                            'público, contexto e registro. Na Komuniki, a proposta é desenvolver ferramentas para '
                            'que o aluno aprenda a observar a cultura como pauta e transformar pesquisa, entrevistas '
                            'e acontecimentos em informação.'
                        ),
                        'text_en': (
                            'Every day, artists, producers, groups and communities create projects that move '
                            'culture forward. Cultural journalism helps these stories find an audience, context '
                            'and record. At Komuniki, the goal is to build the tools for students to learn to see '
                            'culture as a source of stories and turn research, interviews and events into '
                            'information.'
                        ),
                        'highlight': (
                            'Cultura também é notícia. Aprenda a pesquisar, entrevistar, produzir e contar as '
                            'histórias que acontecem dentro e fora dos palcos.'
                        ),
                        'highlight_en': (
                            'Culture is news too. Learn to research, interview, produce and tell the stories that '
                            'happen on and off the stage.'
                        ),
                        'primary_label': 'Quero conhecer o Jornalismo Cultural',
                        'primary_label_en': 'I want to learn about Cultural Journalism',
                        'secondary_label': 'Consultar próximas turmas',
                        'secondary_label_en': 'Check upcoming class dates',
                    },
                },
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
                'page': {
                    'hero_tagline': 'Desenvolva presença para conduzir eventos com segurança.',
                    'hero_tagline_en': 'Build the presence to host events with confidence.',
                    'hero_cta_label': 'Tenho interesse neste curso',
                    'hero_cta_label_en': "I'm interested in this course",
                    'meta_description': (
                        'Curso livre de 50 horas em apresentação de palco e eventos: presença, voz, condução e '
                        'adaptação para mestres de cerimônia na Escola Komuniki.'
                    ),
                    'intro': [
                        {
                            'text': (
                                'Estar no palco significa assumir a responsabilidade de conduzir a atenção do público. '
                                'Uma boa apresentação precisa orientar, informar, conectar diferentes momentos de um '
                                'evento e transmitir segurança para quem está acompanhando.'
                            ),
                            'text_en': (
                                "Being on stage means taking on the responsibility of guiding the audience's "
                                'attention. A good presentation needs to orient, inform, connect the different '
                                'moments of an event and convey confidence to those watching.'
                            ),
                        },
                        {
                            'text': (
                                'O Curso de Apresentação de Palco e Eventos da Komuniki é voltado para quem deseja '
                                'desenvolver técnicas de apresentação e melhorar sua atuação diante de uma plateia.'
                            ),
                            'text_en': (
                                "Komuniki's Stage and Event Presenting course is for anyone who wants to develop "
                                'presenting techniques and improve their performance in front of an audience.'
                            ),
                        },
                    ],
                    'sections': [
                        {
                            'kind': 'cards',
                            'eyebrow': 'Competências',
                            'eyebrow_en': 'Skills',
                            'title': 'Muito além de simplesmente falar no palco',
                            'title_en': 'Far more than just talking on stage',
                            'lead': (
                                'Apresentar envolve voz, postura, atenção e capacidade de adaptação. O apresentador '
                                'precisa compreender o momento, comunicar informações com clareza e manter uma '
                                'relação constante com o público. A formação busca desenvolver essas competências de '
                                'maneira aplicada à condução de eventos.'
                            ),
                            'lead_en': (
                                'Presenting involves voice, posture, attentiveness and the ability to adapt. '
                                'Presenters need to read the moment, communicate information clearly and keep a '
                                'constant connection with the audience. The course develops these skills with a '
                                'practical focus on hosting events.'
                            ),
                            'items': [
                                {
                                    'title': 'Presença',
                                    'title_en': 'Presence',
                                    'body': (
                                        'O modo como o apresentador ocupa o espaço influencia diretamente a '
                                        'percepção do público. Postura, expressão e segurança fazem parte da '
                                        'construção dessa presença.'
                                    ),
                                    'body_en': (
                                        "The way a presenter occupies the space directly shapes how the audience "
                                        'perceives them. Posture, expression and confidence all help build that '
                                        'presence.'
                                    ),
                                },
                                {
                                    'title': 'Voz e clareza',
                                    'title_en': 'Voice and clarity',
                                    'body': (
                                        'Uma mensagem precisa ser compreendida. Desenvolver articulação, ritmo e '
                                        'intenção ajuda a tornar a comunicação mais clara e agradável.'
                                    ),
                                    'body_en': (
                                        'A message needs to be understood. Developing articulation, rhythm and '
                                        'intent makes communication clearer and more engaging.'
                                    ),
                                },
                                {
                                    'title': 'Condução',
                                    'title_en': 'Hosting',
                                    'body': (
                                        'Eventos possuem etapas, transições e diferentes participantes. O '
                                        'apresentador atua como um elo entre esses momentos, ajudando o público a '
                                        'acompanhar o que está acontecendo.'
                                    ),
                                    'body_en': (
                                        'Events have stages, transitions and different participants. The presenter '
                                        'acts as the link between these moments, helping the audience follow what '
                                        'is happening.'
                                    ),
                                },
                                {
                                    'title': 'Adaptação',
                                    'title_en': 'Adapting on the fly',
                                    'body': (
                                        'Nem toda apresentação acontece exatamente como planejado. Ter domínio da '
                                        'comunicação ajuda a responder com mais segurança às situações que podem '
                                        'surgir durante um evento.'
                                    ),
                                    'body_en': (
                                        'Not every presentation goes exactly as planned. Mastering communication '
                                        'helps you respond with more confidence to whatever comes up during an '
                                        'event.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'list',
                            'eyebrow': 'Público',
                            'eyebrow_en': "Who it's for",
                            'title': 'Para quem é?',
                            'title_en': 'Who is it for?',
                            'lead': 'O curso pode ser interessante para quem deseja:',
                            'lead_en': 'This course can be a good fit for anyone who wants to:',
                            'items': [
                                {'text': 'Apresentar eventos', 'text_en': 'Host events'},
                                {'text': 'Atuar como mestre de cerimônias', 'text_en': 'Work as a master of ceremonies'},
                                {'text': 'Desenvolver segurança no palco', 'text_en': 'Build confidence on stage'},
                                {'text': 'Melhorar postura e expressão', 'text_en': 'Improve posture and expression'},
                                {'text': 'Falar diante de públicos', 'text_en': 'Speak in front of audiences'},
                                {'text': 'Conduzir apresentações profissionais', 'text_en': 'Lead professional presentations'},
                                {'text': 'Ampliar habilidades de comunicação presencial', 'text_en': 'Broaden their in-person communication skills'},
                            ],
                            'note': (
                                'Também pode ajudar profissionais que já precisam participar de apresentações e '
                                'desejam se sentir mais preparados nesses momentos.'
                            ),
                            'note_en': (
                                'It can also help professionals who already need to take part in presentations and '
                                'want to feel more prepared for these moments.'
                            ),
                        },
                    ],
                    'final_cta': {
                        'title': 'O palco começa antes do microfone.',
                        'title_en': 'The stage begins before the microphone.',
                        'text': (
                            'Segurança não significa simplesmente perder o nervosismo. Significa desenvolver '
                            'recursos para saber como agir, comunicar e conduzir uma apresentação mesmo diante da '
                            'pressão.'
                        ),
                        'text_en': (
                            "Confidence doesn't simply mean losing your nerves. It means building the tools to "
                            'know how to act, communicate and lead a presentation even under pressure.'
                        ),
                        'primary_label': 'Quero desenvolver minha apresentação',
                        'primary_label_en': 'I want to develop my presenting skills',
                        'secondary_label': 'Consultar próximas turmas',
                        'secondary_label_en': 'Check upcoming class dates',
                    },
                },
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
                'page': {
                    'hero_tagline': 'Desenvolva sua comunicação em espanhol.',
                    'hero_tagline_en': 'Develop your communication in Spanish.',
                    'hero_cta_label': 'Tenho interesse neste curso',
                    'hero_cta_label_en': "I'm interested in this course",
                    'meta_description': (
                        'Curso livre de espanhol com foco em conversação e escrita, para desenvolver comunicação '
                        'oral e escrita na Escola Komuniki.'
                    ),
                    'intro': [
                        {
                            'text': 'Aprender um idioma significa desenvolver novas possibilidades de comunicação.',
                            'text_en': 'Learning a language means opening up new possibilities for communication.',
                        },
                        {
                            'text': (
                                'O curso de Espanhol – Conversação e Escrita da Komuniki trabalha o desenvolvimento da '
                                'expressão oral e escrita para quem deseja ampliar sua capacidade de se comunicar em '
                                'espanhol.'
                            ),
                            'text_en': (
                                "Komuniki's Spanish – Conversation and Writing course develops spoken and written "
                                'expression for anyone who wants to expand their ability to communicate in Spanish.'
                            ),
                        },
                    ],
                    'sections': [
                        {
                            'kind': 'cards',
                            'eyebrow': 'Como o curso é organizado',
                            'eyebrow_en': 'How the course is organized',
                            'title': 'Falar, compreender e se expressar',
                            'title_en': 'Speak, understand and express yourself',
                            'lead': (
                                'Conhecer palavras e regras é importante, mas utilizar um idioma exige transformar '
                                'esse conhecimento em comunicação. A proposta do curso é trabalhar espanhol a partir '
                                'de duas dimensões complementares: conversação e escrita.'
                            ),
                            'lead_en': (
                                'Knowing words and rules matters, but using a language means turning that knowledge '
                                'into communication. The course approaches Spanish through two complementary '
                                'dimensions: conversation and writing.'
                            ),
                            'items': [
                                {
                                    'title': 'Conversação',
                                    'title_en': 'Conversation',
                                    'body': (
                                        'A prática oral ajuda o aluno a desenvolver mais naturalidade ao formular '
                                        'frases, participar de conversas e expressar ideias em espanhol.'
                                    ),
                                    'body_en': (
                                        'Speaking practice helps students form sentences, take part in '
                                        'conversations and express ideas in Spanish more naturally.'
                                    ),
                                },
                                {
                                    'title': 'Escrita',
                                    'title_en': 'Writing',
                                    'body': (
                                        'A comunicação escrita permite organizar melhor o pensamento e desenvolver '
                                        'maior familiaridade com estruturas e vocabulário do idioma.'
                                    ),
                                    'body_en': (
                                        'Written communication helps organize thinking and build greater '
                                        'familiarity with the structures and vocabulary of the language.'
                                    ),
                                },
                                {
                                    'title': 'Vocabulário',
                                    'title_en': 'Vocabulary',
                                    'body': (
                                        'Ampliar o repertório de palavras e expressões oferece mais recursos para '
                                        'lidar com diferentes situações de comunicação.'
                                    ),
                                    'body_en': (
                                        'Expanding a repertoire of words and expressions provides more resources '
                                        'for handling different communication situations.'
                                    ),
                                },
                                {
                                    'title': 'Segurança para se comunicar',
                                    'title_en': 'Confidence to communicate',
                                    'body': (
                                        'Aprender um idioma também envolve aceitar o processo de tentativa, prática '
                                        'e desenvolvimento: a experiência ajuda a utilizar o que se aprende com '
                                        'progressivamente mais segurança.'
                                    ),
                                    'body_en': (
                                        'Learning a language also means embracing a process of trial, practice '
                                        'and growth: experience helps you use what you learn with increasing '
                                        'confidence.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'list',
                            'eyebrow': 'Público',
                            'eyebrow_en': "Who it's for",
                            'title': 'Para quem é?',
                            'title_en': 'Who is it for?',
                            'lead': 'O curso pode atender pessoas que desejam:',
                            'lead_en': 'This course can suit anyone who wants to:',
                            'items': [
                                {'text': 'Desenvolver conversação em espanhol', 'text_en': 'Develop conversation skills in Spanish'},
                                {'text': 'Aprimorar a comunicação escrita', 'text_en': 'Improve written communication'},
                                {'text': 'Ampliar vocabulário', 'text_en': 'Expand their vocabulary'},
                                {'text': 'Praticar o idioma', 'text_en': 'Practice the language'},
                                {'text': 'Utilizar espanhol em situações pessoais, acadêmicas ou profissionais', 'text_en': 'Use Spanish in personal, academic or professional situations'},
                                {'text': 'Desenvolver mais confiança para se expressar', 'text_en': 'Build more confidence expressing themselves'},
                            ],
                        },
                    ],
                    'final_cta': {
                        'title': 'Um novo idioma amplia suas possibilidades de comunicação.',
                        'title_en': 'A new language expands your possibilities for communication.',
                        'text': (
                            'Aprender espanhol não significa apenas conhecer uma nova língua. Também significa '
                            'poder acessar novas pessoas, conteúdos, culturas e experiências.'
                        ),
                        'text_en': (
                            'Learning Spanish is not just about knowing a new language. It also means gaining '
                            'access to new people, content, cultures and experiences.'
                        ),
                        'primary_label': 'Quero saber mais sobre o curso de Espanhol',
                        'primary_label_en': 'I want to know more about the Spanish course',
                        'secondary_label': 'Consultar próximas turmas',
                        'secondary_label_en': 'Check upcoming class dates',
                    },
                },
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
                'page': {
                    'hero_tagline': 'Fale com segurança. Comunique-se com clareza. Desbloqueie sua voz.',
                    'hero_tagline_en': 'Speak with confidence. Communicate with clarity. Unlock your voice.',
                    'hero_cta_label': 'Quero destravar minha comunicação',
                    'hero_cta_label_en': 'I want to unlock my communication',
                    'meta_description': (
                        'Método premiado de comunicação e oratória: 20 horas em curso coletivo ou mentoria '
                        'individual para falar com clareza e segurança na Escola Komuniki.'
                    ),
                    'intro': [
                        {
                            'text': (
                                'Ter uma boa ideia é importante. Conseguir transmiti-la com clareza, presença e '
                                'segurança pode fazer toda a diferença.'
                            ),
                            'text_en': (
                                'Having a good idea matters. Being able to convey it with clarity, presence and '
                                'confidence can make all the difference.'
                            ),
                        },
                        {
                            'text': (
                                'O Comunicação Destravada é um método desenvolvido para pessoas que desejam se expressar '
                                'melhor em situações profissionais, acadêmicas e pessoais — seja em uma apresentação, '
                                'reunião, entrevista, vídeo, evento ou simplesmente em uma conversa importante.'
                            ),
                            'text_en': (
                                'Comunicação Destravada (Unlocked Communication) is a method built for people who '
                                'want to express themselves better in professional, academic and personal '
                                'situations — whether in a presentation, meeting, interview, video, event, or '
                                'simply an important conversation.'
                            ),
                        },
                        {
                            'text': (
                                'Mais do que ensinar técnicas para "falar bem", a proposta é desenvolver uma comunicação '
                                'mais consciente, natural e autêntica, trabalhando expressão, voz, presença e confiança.'
                            ),
                            'text_en': (
                                'Rather than just teaching techniques to "speak well," the goal is to develop '
                                'communication that is more conscious, natural and authentic, working on '
                                'expression, voice, presence and confidence.'
                            ),
                        },
                    ],
                    'sections': [
                        {
                            'kind': 'prose',
                            'eyebrow': 'Sobre o método',
                            'eyebrow_en': 'About the method',
                            'title': 'Comunicação também se desenvolve',
                            'title_en': 'Communication can be developed too',
                            'body': [
                                {
                                    'text': (
                                        'Nem toda dificuldade para se comunicar acontece porque faltam ideias. Às vezes '
                                        'sabemos exatamente o que queremos dizer, mas temos dificuldade para organizar o '
                                        'pensamento, encontramos bloqueios na hora de falar, sentimos insegurança diante '
                                        'de outras pessoas ou simplesmente não conseguimos transmitir a mensagem da '
                                        'maneira que imaginamos.'
                                    ),
                                    'text_en': (
                                        "Difficulty communicating doesn't always come from a lack of ideas. "
                                        'Sometimes we know exactly what we want to say, but struggle to organize '
                                        "our thoughts, hit a block when it's time to speak, feel insecure around "
                                        "other people, or simply can't get the message across the way we pictured "
                                        'it.'
                                    ),
                                },
                                {
                                    'text': (
                                        'A comunicação pode ser observada, praticada e desenvolvida. O Comunicação '
                                        'Destravada trabalha justamente esse processo: ajudar cada participante a '
                                        'compreender melhor a própria forma de se expressar e desenvolver recursos para '
                                        'comunicar suas ideias com maior clareza e segurança.'
                                    ),
                                    'text_en': (
                                        'Communication can be observed, practiced and developed. Comunicação '
                                        'Destravada focuses on exactly this process: helping each participant '
                                        'better understand their own way of expressing themselves and build the '
                                        'tools to communicate their ideas with greater clarity and confidence.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'cards',
                            'eyebrow': 'O método',
                            'eyebrow_en': 'The method',
                            'title': 'O que você desenvolve durante o curso?',
                            'title_en': 'What do you develop during the course?',
                            'items': [
                                {
                                    'title': 'Fala e expressão',
                                    'title_en': 'Speech and expression',
                                    'body': (
                                        'Construção da fala, articulação, clareza e naturalidade para apresentar um '
                                        'pensamento de forma compreensível, sem depender de falas decoradas ou de um '
                                        'estilo artificial de comunicação.'
                                    ),
                                    'body_en': (
                                        'Building speech, articulation, clarity and naturalness to present a '
                                        'thought in an understandable way, without relying on memorized lines or '
                                        'an artificial style of communication.'
                                    ),
                                },
                                {
                                    'title': 'Voz e comunicação',
                                    'title_en': 'Voice and communication',
                                    'body': (
                                        'Ritmo, pausas, entonação, volume e articulação podem modificar completamente '
                                        'a maneira como uma mensagem é percebida: recursos para usar a própria voz de '
                                        'forma mais consciente.'
                                    ),
                                    'body_en': (
                                        'Rhythm, pauses, intonation, volume and articulation can completely change '
                                        'how a message is perceived: tools for using your own voice more '
                                        'consciously.'
                                    ),
                                },
                                {
                                    'title': 'Segurança para falar',
                                    'title_en': 'Confidence to speak',
                                    'body': (
                                        'O objetivo não é eliminar a insegurança, mas desenvolver recursos para que '
                                        'ela deixe de impedir a comunicação, compreendendo melhor as próprias '
                                        'reações diante de câmera, público ou apresentações.'
                                    ),
                                    'body_en': (
                                        "The goal isn't to eliminate insecurity, but to build the tools so it no "
                                        'longer gets in the way of communication, by better understanding your '
                                        'own reactions in front of a camera, an audience or a presentation.'
                                    ),
                                },
                                {
                                    'title': 'Comunicação não verbal',
                                    'title_en': 'Non-verbal communication',
                                    'body': (
                                        'Postura, gestos, expressão facial, olhar e maneira de ocupar um espaço '
                                        'também participam da mensagem: uma presença mais consciente e coerente com '
                                        'aquilo que se deseja transmitir.'
                                    ),
                                    'body_en': (
                                        'Posture, gestures, facial expression, eye contact and the way you occupy '
                                        'a space are also part of the message: a presence that is more conscious '
                                        'and consistent with what you want to convey.'
                                    ),
                                },
                                {
                                    'title': 'Comunicação para vídeos e redes sociais',
                                    'title_en': 'Communication for video and social media',
                                    'body': (
                                        'Recursos para se posicionar, organizar uma mensagem e comunicar de maneira '
                                        'mais natural em vídeos e conteúdos digitais, cada vez mais relevante para '
                                        'criadores, profissionais e empreendedores.'
                                    ),
                                    'body_en': (
                                        'Tools for positioning yourself, organizing a message and communicating '
                                        'more naturally in videos and digital content — increasingly relevant for '
                                        'creators, professionals and entrepreneurs.'
                                    ),
                                },
                                {
                                    'title': 'Falar em público',
                                    'title_en': 'Public speaking',
                                    'body': (
                                        'Organizar a mensagem, compreender o público, trabalhar presença e conduzir '
                                        'a comunicação em apresentações, palestras, reuniões e eventos de forma mais '
                                        'estruturada e segura.'
                                    ),
                                    'body_en': (
                                        'Organizing the message, understanding the audience, working on presence '
                                        'and leading communication in presentations, talks, meetings and events in '
                                        'a more structured and confident way.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'callout_award',
                            'eyebrow': 'Reconhecimento',
                            'eyebrow_en': 'Recognition',
                            'title': 'Método premiado',
                            'title_en': 'Recognized method',
                            'badge_title': 'Prêmio Paulo Freire de Educação — CLDF 2024',
                            'badge_title_en': 'Prêmio Paulo Freire de Educação — CLDF 2024',
                            'badge_intro': (
                                'A metodologia Comunicação Destravada recebeu o Prêmio Paulo Freire de Educação, '
                                'concedido pela Câmara Legislativa do Distrito Federal em 2024.'
                            ),
                            'badge_intro_en': (
                                'The Comunicação Destravada methodology received the Prêmio Paulo Freire de '
                                'Educação (Paulo Freire Education Award), granted by the Legislative Chamber of '
                                'the Federal District (Brasília) in 2024.'
                            ),
                            'body': [
                                {
                                    'text': (
                                        'O reconhecimento representa um marco na trajetória do método e em sua proposta '
                                        'de utilizar a comunicação como instrumento de desenvolvimento.'
                                    ),
                                    'text_en': (
                                        "The recognition marks a milestone in the method's journey and in its "
                                        'mission to use communication as a tool for personal development.'
                                    ),
                                },
                                {
                                    'text': (
                                        'Essa experiência faz parte do trabalho desenvolvido pela Komuniki para '
                                        'aproximar técnica, expressão, educação e desenvolvimento pessoal.'
                                    ),
                                    'text_en': (
                                        "This achievement is part of Komuniki's broader work to bring together "
                                        'technique, expression, education and personal development.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'prose',
                            'eyebrow': 'Formatos',
                            'eyebrow_en': 'Formats',
                            'title': 'Curso coletivo ou mentoria individual',
                            'title_en': 'Group course or individual mentoring',
                            'body': [
                                {
                                    'text': (
                                        'Pessoas diferentes possuem desafios diferentes ao se comunicar. Por isso, o '
                                        'Comunicação Destravada pode acontecer tanto em formato coletivo quanto por meio '
                                        'de mentoria individual.'
                                    ),
                                    'text_en': (
                                        "Different people face different challenges when communicating. That's "
                                        'why Comunicação Destravada is available both as a group course and as '
                                        'individual mentoring.'
                                    ),
                                },
                                {
                                    'text': (
                                        'No curso coletivo, a experiência permite desenvolver a comunicação também por '
                                        'meio da interação, observação e prática com outras pessoas. Na mentoria '
                                        'individual, o acompanhamento pode ser direcionado às necessidades específicas '
                                        'de comunicação do participante.'
                                    ),
                                    'text_en': (
                                        'In the group course, the experience also builds communication through '
                                        'interaction, observation and practice with others. In individual '
                                        "mentoring, the guidance can be tailored to the participant's specific "
                                        'communication needs.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'list',
                            'eyebrow': 'Público',
                            'eyebrow_en': "Who it's for",
                            'title': 'Para quem é o Comunicação Destravada?',
                            'title_en': 'Who is Comunicação Destravada for?',
                            'lead': 'O método pode ser interessante para:',
                            'lead_en': 'The method can be valuable for:',
                            'items': [
                                {'text': 'Pessoas que sentem medo ou vergonha de falar em público', 'text_en': 'People who feel fear or embarrassment speaking in public'},
                                {'text': 'Profissionais que desejam melhorar sua comunicação', 'text_en': 'Professionals who want to improve their communication'},
                                {'text': 'Empreendedores que precisam apresentar ideias e negócios', 'text_en': 'Entrepreneurs who need to pitch ideas and businesses'},
                                {'text': 'Professores, palestrantes e líderes', 'text_en': 'Teachers, speakers and leaders'},
                                {'text': 'Criadores de conteúdo', 'text_en': 'Content creators'},
                                {'text': 'Pessoas que produzem vídeos ou conteúdos para redes sociais', 'text_en': 'People who produce videos or content for social media'},
                                {'text': 'Quem sente dificuldade durante apresentações, entrevistas ou reuniões', 'text_en': 'Anyone who struggles during presentations, interviews or meetings'},
                                {'text': 'Quem tem boas ideias, mas encontra dificuldade para organizá-las ao falar', 'text_en': 'Anyone with good ideas who struggles to organize them out loud'},
                                {
                                    'text': 'Pessoas que desejam desenvolver mais segurança e presença ao se expressar',
                                    'text_en': 'People who want to build more confidence and presence when expressing themselves',
                                },
                            ],
                            'note': (
                                'Você não precisa trabalhar profissionalmente com comunicação para desenvolver sua '
                                'forma de comunicar. A comunicação está presente em praticamente todos os ambientes '
                                'em que precisamos apresentar uma ideia, defender um ponto de vista, explicar algo, '
                                'ensinar, liderar ou simplesmente ser compreendidos.'
                            ),
                            'note_en': (
                                "You don't need to work professionally in communication to develop the way you "
                                'communicate. Communication is present in nearly every setting where we need to '
                                'present an idea, defend a point of view, explain something, teach, lead, or '
                                'simply be understood.'
                            ),
                        },
                        {
                            'kind': 'quote',
                            'title': 'Não existe apenas uma maneira correta de comunicar',
                            'title_en': 'There is no single right way to communicate',
                            'lead': (
                                'Desenvolver comunicação não significa criar um personagem, copiar o estilo de outra '
                                'pessoa ou abandonar sua personalidade. Cada pessoa possui voz, repertório, ritmo e '
                                'maneira própria de se expressar. O objetivo é compreender melhor esses recursos e '
                                'utilizá-los de maneira consciente.'
                            ),
                            'lead_en': (
                                "Developing your communication doesn't mean creating a character, copying someone "
                                "else's style or abandoning your personality. Every person has their own voice, "
                                'repertoire, rhythm and way of expressing themselves. The goal is to better '
                                'understand these resources and use them consciously.'
                            ),
                            'lines': [
                                {'text': 'Você não precisa nascer comunicador.', 'text_en': "You don't need to be a born communicator."},
                                {'text': 'Comunicação também se aprende, se pratica e se desenvolve.', 'text_en': 'Communication can also be learned, practiced and developed.'},
                            ],
                        },
                    ],
                    'final_cta': {
                        'title': 'Encontre mais liberdade para expressar suas ideias.',
                        'title_en': 'Find more freedom to express your ideas.',
                        'text': (
                            'Uma comunicação mais clara pode transformar a maneira como você apresenta seu '
                            'trabalho, participa de uma reunião, grava um vídeo ou simplesmente conversa com outras '
                            'pessoas. O primeiro passo é aprender a reconhecer e desenvolver os recursos que você '
                            'já possui.'
                        ),
                        'text_en': (
                            'Clearer communication can transform the way you present your work, take part in a '
                            'meeting, record a video, or simply talk with other people. The first step is '
                            'learning to recognize and develop the resources you already have.'
                        ),
                        'primary_label': 'Quero destravar minha comunicação',
                        'primary_label_en': 'I want to unlock my communication',
                        'secondary_label': 'Falar com a Komuniki',
                        'secondary_label_en': 'Talk to Komuniki',
                    },
                },
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


def find_course_group(slug):
    """Grupo/trilha (com eyebrow bilíngue) ao qual o curso desse slug pertence, ou None."""
    for group in COURSE_GROUPS:
        for course in group['courses']:
            if course['slug'] == slug:
                return group
    return None


# Hífen condicional (U+00AD): invisível, só aparece se o navegador realmente quebrar a linha ali. O
# CSS "hyphens: auto" existe, mas depende de um dicionário de hifenização nem sempre presente no
# navegador; para os títulos compridos que já quebraram no meio da palavra (sem respeitar sílaba),
# a separação abaixo é explícita e correta em português, e funciona em qualquer navegador.
_TITLE_HYPHENATION = {
    'Profissionalizante': 'Profissionali­zante',
    'Apresentação': 'Apresenta­ção',
    'Conversação': 'Conversa­ção',
}


def hero_title_for_display(title):
    """course['title'] com hífen condicional nas palavras compridas conhecidas, só para o H1 da
    página do curso. Não mexe no valor original: breadcrumb, cards e <title> continuam exatos."""
    for word, hyphenated in _TITLE_HYPHENATION.items():
        title = title.replace(word, hyphenated)
    return title
