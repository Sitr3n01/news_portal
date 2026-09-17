"""Catálogo da página Cursos. O slug de cada curso é fixo: o card leva à página detalhada do curso, cujo CTA segue
para Contato com ?curso=<slug>, e o formulário registra o curso de interesse a partir dele. Cada texto tem a versão
em inglês ao lado, com o sufixo _en. A chave "page" guarda o conteúdo (só em português, ainda sem tradução aprovada)
da página detalhada de cada curso; find_course() é usado por apps.school.views.course_detail e por apps.contact."""

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
                    'hero_cta_label': 'Tenho interesse neste curso',
                    'meta_description': (
                        'Formação profissionalizante de 350 horas em rádio, TV, publicidade e comunicação, com estágio '
                        'supervisionado e encaminhamento profissional na Escola Komuniki.'
                    ),
                    'intro': [
                        (
                            'Comunicar bem é mais do que falar com desenvoltura. É compreender a mensagem, adaptar a '
                            'linguagem ao público, desenvolver presença e utilizar voz, expressão e repertório de '
                            'maneira consciente.'
                        ),
                        (
                            'O Curso de Comunicador Profissionalizante da Escola Komuniki foi desenvolvido para quem '
                            'deseja ingressar ou se aperfeiçoar no universo da comunicação, explorando possibilidades '
                            'relacionadas a rádio, televisão, publicidade, eventos, produção de conteúdo e diferentes '
                            'plataformas.'
                        ),
                    ],
                    'sections': [
                        {
                            'kind': 'cards',
                            'eyebrow': 'Áreas de formação',
                            'title': 'Uma formação para diferentes formas de comunicar',
                            'lead': (
                                'Durante a formação, o aluno entra em contato com diferentes áreas da comunicação e '
                                'desenvolve recursos que podem ser utilizados diante de um microfone, de uma câmera, '
                                'de uma plateia ou na produção de conteúdos. A proposta é unir conhecimento, prática e '
                                'desenvolvimento da expressão para construir uma comunicação cada vez mais clara, '
                                'segura e adequada ao contexto profissional.'
                            ),
                            'items': [
                                {
                                    'title': 'Rádio e Locução',
                                    'body': (
                                        'Desenvolvimento de voz, dicção, leitura, interpretação e técnicas de locução '
                                        'aplicadas ao rádio e a outras formas de comunicação sonora. O objetivo é '
                                        'compreender como ritmo, intenção, articulação e interpretação modificam a '
                                        'maneira como uma mensagem é recebida.'
                                    ),
                                },
                                {
                                    'title': 'Televisão e Apresentação',
                                    'body': (
                                        'Postura diante das câmeras, apresentação, entrevistas, construção de textos e '
                                        'comunicação para conteúdos audiovisuais — saber o que dizer e também como '
                                        'transmitir a mensagem de forma natural, organizada e compreensível.'
                                    ),
                                },
                                {
                                    'title': 'Publicidade e Comunicação',
                                    'body': (
                                        'Fundamentos ligados à publicidade, comunicação com diferentes públicos, '
                                        'criação de conteúdos e desenvolvimento de mensagens, ampliando a percepção '
                                        'sobre como linguagem, público e objetivo se relacionam.'
                                    ),
                                },
                                {
                                    'title': 'Legislação e Ética Profissional',
                                    'body': (
                                        'Conhecimentos sobre legislação, ética e responsabilidade profissional, '
                                        'contribuindo para uma atuação mais consciente no mercado de comunicação.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'prose',
                            'eyebrow': 'Formação prática',
                            'title': 'Técnica, prática e desenvolvimento pessoal',
                            'body': [
                                (
                                    'Ao longo das 350 horas, o estudante é estimulado a desenvolver não apenas '
                                    'conhecimentos técnicos, mas também aspectos importantes para sua presença como '
                                    'comunicador — voz, postura, expressão, interpretação, segurança para falar e '
                                    'capacidade de organizar uma mensagem.'
                                ),
                                'A formação possui conteúdo teórico, atividades práticas, vivências relacionadas ao mercado e estágio supervisionado.',
                            ],
                        },
                        {
                            'kind': 'list',
                            'eyebrow': 'Público',
                            'title': 'Para quem é este curso?',
                            'lead': 'O Comunicador Profissionalizante pode ser uma opção para quem deseja:',
                            'items': [
                                'Trabalhar com rádio e locução',
                                'Desenvolver apresentação para televisão e vídeo',
                                'Apresentar programas, projetos ou eventos',
                                'Produzir conteúdo para plataformas digitais',
                                'Atuar com publicidade e comunicação',
                                'Desenvolver mais segurança diante das câmeras',
                                'Aprimorar voz, postura e expressão',
                                'Transformar uma habilidade de comunicação em atividade profissional',
                                'Desenvolver confiança para falar diante de outras pessoas',
                            ],
                            'note': (
                                'Não é necessário chegar ao curso sabendo apresentar ou dominando técnicas '
                                'profissionais de comunicação: a formação existe justamente para desenvolver essas '
                                'competências ao longo do processo.'
                            ),
                        },
                        {
                            'kind': 'list',
                            'eyebrow': 'Diferenciais',
                            'title': 'Diferenciais da formação',
                            'items': [
                                '350 horas de formação profissionalizante',
                                'Formação multidisciplinar em comunicação',
                                'Integração entre conteúdo teórico e atividades práticas',
                                'Desenvolvimento de voz, postura e expressão',
                                'Experiências relacionadas ao ambiente profissional',
                                'Professores e profissionais com experiência na área',
                                'Estágio supervisionado',
                                'Certificação ao final da formação',
                                'Orientação para os próximos passos profissionais',
                                'Encaminhamento para registro profissional de Comunicador',
                            ],
                        },
                    ],
                    'final_cta': {
                        'title': 'Sua voz pode ser o começo de uma nova profissão.',
                        'text': (
                            'Uma boa comunicação pode informar, apresentar, representar ideias, conduzir conversas e '
                            'criar conexões. Na Komuniki, a proposta é ajudar o aluno a transformar essa capacidade em '
                            'técnica, repertório e presença profissional.'
                        ),
                        'primary_label': 'Quero saber mais sobre o curso',
                        'secondary_label': 'Falar com a Komuniki',
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
                    'hero_cta_label': 'Tenho interesse neste curso',
                    'meta_description': (
                        'Formação profissionalizante de 250 horas em planejamento, organização e execução de projetos '
                        'culturais, com encaminhamento profissional na Escola Komuniki.'
                    ),
                    'intro': [
                        (
                            'Por trás de apresentações, eventos, projetos artísticos e diferentes iniciativas '
                            'culturais existe um trabalho de planejamento, organização e execução.'
                        ),
                        (
                            'O Curso de Produção Cultural da Escola Komuniki é uma formação profissionalizante '
                            'voltada para quem deseja compreender melhor esse processo e se preparar para participar '
                            'da realização de projetos culturais.'
                        ),
                    ],
                    'sections': [
                        {
                            'kind': 'cards',
                            'eyebrow': 'Como o curso é organizado',
                            'title': 'Da ideia à realização',
                            'lead': (
                                'Produzir cultura exige enxergar um projeto como um conjunto de etapas: organizar '
                                'ideias, compreender necessidades, trabalhar com pessoas, acompanhar processos e '
                                'contribuir para que aquilo que foi planejado aconteça. A formação busca desenvolver '
                                'essa visão mais ampla da produção.'
                            ),
                            'items': [
                                {
                                    'title': 'Planejamento',
                                    'body': (
                                        'Projetos precisam começar com clareza sobre aquilo que se deseja realizar. O '
                                        'aluno desenvolve uma visão mais organizada sobre objetivos, necessidades, '
                                        'prioridades e etapas de uma produção.'
                                    ),
                                },
                                {
                                    'title': 'Organização',
                                    'body': (
                                        'Produção também significa acompanhar diversas partes de um mesmo projeto. '
                                        'Desenvolver organização ajuda o profissional a lidar com informações, '
                                        'equipes, demandas e diferentes momentos de uma iniciativa cultural.'
                                    ),
                                },
                                {
                                    'title': 'Execução',
                                    'body': (
                                        'Planejar é apenas parte do trabalho. A produção cultural também exige '
                                        'acompanhar a realização do projeto e responder às necessidades que surgem '
                                        'durante a execução.'
                                    ),
                                },
                                {
                                    'title': 'Comunicação',
                                    'body': (
                                        'Um produtor está constantemente em contato com pessoas. Artistas, '
                                        'profissionais, equipes e participantes de um projeto precisam compreender o '
                                        'que está acontecendo e qual é o papel de cada um: comunicação e organização '
                                        'caminham juntas.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'list',
                            'eyebrow': 'Público',
                            'title': 'Para quem é este curso?',
                            'lead': 'A formação pode interessar a quem deseja:',
                            'items': [
                                'Trabalhar com projetos culturais',
                                'Participar da organização de eventos e iniciativas artísticas',
                                'Compreender melhor os processos de produção',
                                'Transformar uma ideia cultural em um projeto organizado',
                                'Atuar nos bastidores de produções',
                                'Desenvolver capacidade de planejamento e organização',
                                'Ampliar conhecimentos sobre o setor cultural',
                            ],
                            'note': (
                                'Também pode ser interessante para artistas e comunicadores que desejam compreender '
                                'melhor o que acontece além do palco ou da criação artística.'
                            ),
                        },
                        {
                            'kind': 'prose',
                            'eyebrow': 'Formação profissionalizante',
                            'title': 'Um percurso de 250 horas',
                            'body': [
                                (
                                    'Distribuído ao longo de 12 meses, o curso oferece um percurso mais aprofundado '
                                    'para quem deseja se preparar para atividades relacionadas à produção cultural.'
                                ),
                                'A formação possui encaminhamento para registro profissional de Diretor de Produção.',
                            ],
                        },
                    ],
                    'final_cta': {
                        'title': 'Cultura também precisa de quem faça acontecer.',
                        'text': (
                            'Uma ideia pode iniciar um projeto. A produção é o trabalho que ajuda essa ideia a '
                            'encontrar organização, pessoas e caminhos para se tornar realidade.'
                        ),
                        'primary_label': 'Quero saber mais sobre Produção Cultural',
                        'secondary_label': 'Falar com a Komuniki',
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
                    'hero_cta_label': 'Quero conhecer o Jornalismo Cultural',
                    'meta_description': (
                        'Curso livre de 30 horas em jornalismo cultural: apuração, entrevistas, texto jornalístico e '
                        'cobertura de eventos para profissionais de Comunicação.'
                    ),
                    'intro': [
                        (
                            'Cultura também é notícia. Cinema, música, teatro, literatura, artes visuais, patrimônio, '
                            'festivais e diferentes manifestações culturais produzem histórias que podem ser '
                            'pesquisadas, documentadas e apresentadas ao público por meio do jornalismo.'
                        ),
                        (
                            'O Curso de Jornalismo Cultural da Escola Komuniki é uma formação de 30 horas voltada ao '
                            'desenvolvimento da produção jornalística aplicada ao universo da cultura, arte, '
                            'entretenimento e patrimônio. Durante o curso, o aluno entra em contato com diferentes '
                            'etapas da cobertura cultural e desenvolve recursos para pesquisar pautas, realizar '
                            'entrevistas, produzir matérias, acompanhar eventos e transformar acontecimentos '
                            'culturais em conteúdo.'
                        ),
                    ],
                    'sections': [
                        {
                            'kind': 'prose',
                            'eyebrow': 'Por que jornalismo cultural',
                            'title': 'Cultura também precisa ser pesquisada, contextualizada e contada',
                            'body': [
                                (
                                    'Produzir conteúdo cultural vai além de divulgar que um evento aconteceu ou dizer '
                                    'se uma obra é boa ou ruim. O jornalismo cultural procura compreender contextos, '
                                    'identificar histórias, ouvir pessoas envolvidas e transformar essas informações '
                                    'em conteúdos que ajudem o público a conhecer melhor uma obra, um artista, um '
                                    'movimento ou um acontecimento.'
                                ),
                                'Para isso, é necessário desenvolver repertório, capacidade de pesquisa e domínio das ferramentas jornalísticas.',
                            ],
                        },
                        {
                            'kind': 'cards',
                            'eyebrow': 'Conteúdo do curso',
                            'title': 'O que você vai desenvolver',
                            'items': [
                                {
                                    'title': 'Fundamentos do jornalismo cultural',
                                    'body': (
                                        'Características da cobertura jornalística voltada para cultura, observando '
                                        'esse universo também como fonte de pautas, histórias e informação.'
                                    ),
                                },
                                {
                                    'title': 'Apuração e pesquisa de pautas culturais',
                                    'body': (
                                        'Pesquisar contexto, buscar informações, identificar fontes e compreender '
                                        'aquilo que será abordado: ferramentas para encontrar e estruturar pautas '
                                        'culturais.'
                                    ),
                                },
                                {
                                    'title': 'Produção de matérias e reportagens',
                                    'body': (
                                        'Organização das informações e construção de matérias e reportagens que '
                                        'apresentem acontecimentos culturais de forma clara, contextualizada e '
                                        'interessante.'
                                    ),
                                },
                                {
                                    'title': 'Entrevistas com artistas e agentes culturais',
                                    'body': (
                                        'Preparar perguntas, pesquisar previamente o entrevistado, saber ouvir e '
                                        'identificar caminhos durante a conversa com artistas, produtores e gestores '
                                        'culturais.'
                                    ),
                                },
                                {
                                    'title': 'Texto jornalístico',
                                    'body': (
                                        'Técnicas de escrita jornalística e organização textual aplicadas à produção '
                                        'de conteúdo cultural, com clareza, contexto e escolha das informações.'
                                    ),
                                },
                                {
                                    'title': 'Cobertura de eventos culturais',
                                    'body': (
                                        'Observar o evento, identificar informações importantes, conversar com '
                                        'fontes e organizar tudo em uma narrativa: a lógica de acompanhamento e '
                                        'cobertura de shows, festivais, espetáculos e exposições.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'cards',
                            'eyebrow': 'Plataformas',
                            'title': 'Jornalismo em diferentes plataformas',
                            'items': [
                                {'title': 'Rádio', 'body': 'Construção de conteúdos culturais pensando nas características da comunicação sonora.'},
                                {'title': 'Televisão e audiovisual', 'body': 'Produção de informação considerando imagem, apresentação e linguagem audiovisual.'},
                                {
                                    'title': 'Mídias digitais',
                                    'body': (
                                        'Adaptação da comunicação jornalística para plataformas digitais e novos '
                                        'formatos de consumo de informação.'
                                    ),
                                },
                                {
                                    'title': 'Redes sociais',
                                    'body': (
                                        'Conteúdos culturais que informam e contextualizam sem abandonar os '
                                        'princípios da comunicação jornalística.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'quote',
                            'title': 'Como encontrar uma boa pauta cultural?',
                            'lead': (
                                'Nem toda pauta precisa começar em um grande lançamento. Uma manifestação cultural '
                                'local, um projeto independente, um artista, uma tradição, um patrimônio ou uma '
                                'transformação dentro de determinada cena também podem gerar histórias relevantes. O '
                                'jornalista cultural aprende a observar aquilo que acontece ao seu redor e a '
                                'perguntar:'
                            ),
                            'lines': [
                                'Que história existe aqui?',
                                'Por que ela importa?',
                                'Quem precisa ser ouvido?',
                                'Como essa história pode ser apresentada ao público?',
                            ],
                        },
                        {
                            'kind': 'prose',
                            'eyebrow': 'Responsabilidade',
                            'title': 'Ética e responsabilidade',
                            'body': [
                                (
                                    'A comunicação cultural também envolve responsabilidade. Produzir conteúdos '
                                    'sobre pessoas, obras, comunidades e manifestações culturais exige cuidado com '
                                    'informações, fontes e contextos: por isso, ética e responsabilidade fazem parte '
                                    'da formação.'
                                ),
                            ],
                        },
                        {
                            'kind': 'list',
                            'eyebrow': 'Público',
                            'title': 'Para quem é o curso?',
                            'lead': (
                                'O Jornalismo Cultural é voltado para profissionais da área de Comunicação que '
                                'desejam aprofundar sua capacidade de produzir conteúdos relacionados à cultura. '
                                'Pode ser especialmente interessante para:'
                            ),
                            'items': [
                                'Jornalistas',
                                'Comunicadores',
                                'Produtores culturais',
                                'Profissionais da cultura',
                                'Artistas e agentes culturais',
                                'Criadores de conteúdo',
                                'Assessores de comunicação',
                                'Profissionais que trabalham com divulgação cultural',
                                'Pessoas da área de Comunicação interessadas em cobertura cultural',
                            ],
                        },
                    ],
                    'final_cta': {
                        'title': 'Do acontecimento à história.',
                        'text': (
                            'Todos os dias, artistas, produtores, grupos e comunidades criam projetos que '
                            'movimentam a cultura. O jornalismo cultural ajuda essas histórias a encontrarem '
                            'público, contexto e registro. Na Komuniki, a proposta é desenvolver ferramentas para '
                            'que o aluno aprenda a observar a cultura como pauta e transformar pesquisa, entrevistas '
                            'e acontecimentos em informação.'
                        ),
                        'highlight': (
                            'Cultura também é notícia. Aprenda a pesquisar, entrevistar, produzir e contar as '
                            'histórias que acontecem dentro e fora dos palcos.'
                        ),
                        'primary_label': 'Quero conhecer o Jornalismo Cultural',
                        'secondary_label': 'Consultar próximas turmas',
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
                    'hero_cta_label': 'Tenho interesse neste curso',
                    'meta_description': (
                        'Curso livre de 50 horas em apresentação de palco e eventos: presença, voz, condução e '
                        'adaptação para mestres de cerimônia na Escola Komuniki.'
                    ),
                    'intro': [
                        (
                            'Estar no palco significa assumir a responsabilidade de conduzir a atenção do público. '
                            'Uma boa apresentação precisa orientar, informar, conectar diferentes momentos de um '
                            'evento e transmitir segurança para quem está acompanhando.'
                        ),
                        (
                            'O Curso de Apresentação de Palco e Eventos da Komuniki é voltado para quem deseja '
                            'desenvolver técnicas de apresentação e melhorar sua atuação diante de uma plateia.'
                        ),
                    ],
                    'sections': [
                        {
                            'kind': 'cards',
                            'eyebrow': 'Competências',
                            'title': 'Muito além de simplesmente falar no palco',
                            'lead': (
                                'Apresentar envolve voz, postura, atenção e capacidade de adaptação. O apresentador '
                                'precisa compreender o momento, comunicar informações com clareza e manter uma '
                                'relação constante com o público. A formação busca desenvolver essas competências de '
                                'maneira aplicada à condução de eventos.'
                            ),
                            'items': [
                                {
                                    'title': 'Presença',
                                    'body': (
                                        'O modo como o apresentador ocupa o espaço influencia diretamente a '
                                        'percepção do público. Postura, expressão e segurança fazem parte da '
                                        'construção dessa presença.'
                                    ),
                                },
                                {
                                    'title': 'Voz e clareza',
                                    'body': (
                                        'Uma mensagem precisa ser compreendida. Desenvolver articulação, ritmo e '
                                        'intenção ajuda a tornar a comunicação mais clara e agradável.'
                                    ),
                                },
                                {
                                    'title': 'Condução',
                                    'body': (
                                        'Eventos possuem etapas, transições e diferentes participantes. O '
                                        'apresentador atua como um elo entre esses momentos, ajudando o público a '
                                        'acompanhar o que está acontecendo.'
                                    ),
                                },
                                {
                                    'title': 'Adaptação',
                                    'body': (
                                        'Nem toda apresentação acontece exatamente como planejado. Ter domínio da '
                                        'comunicação ajuda a responder com mais segurança às situações que podem '
                                        'surgir durante um evento.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'list',
                            'eyebrow': 'Público',
                            'title': 'Para quem é?',
                            'lead': 'O curso pode ser interessante para quem deseja:',
                            'items': [
                                'Apresentar eventos',
                                'Atuar como mestre de cerimônias',
                                'Desenvolver segurança no palco',
                                'Melhorar postura e expressão',
                                'Falar diante de públicos',
                                'Conduzir apresentações profissionais',
                                'Ampliar habilidades de comunicação presencial',
                            ],
                            'note': (
                                'Também pode ajudar profissionais que já precisam participar de apresentações e '
                                'desejam se sentir mais preparados nesses momentos.'
                            ),
                        },
                    ],
                    'final_cta': {
                        'title': 'O palco começa antes do microfone.',
                        'text': (
                            'Segurança não significa simplesmente perder o nervosismo. Significa desenvolver '
                            'recursos para saber como agir, comunicar e conduzir uma apresentação mesmo diante da '
                            'pressão.'
                        ),
                        'primary_label': 'Quero desenvolver minha apresentação',
                        'secondary_label': 'Consultar próximas turmas',
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
                    'hero_cta_label': 'Tenho interesse neste curso',
                    'meta_description': (
                        'Curso livre de espanhol com foco em conversação e escrita, para desenvolver comunicação '
                        'oral e escrita na Escola Komuniki.'
                    ),
                    'intro': [
                        'Aprender um idioma significa desenvolver novas possibilidades de comunicação.',
                        (
                            'O curso de Espanhol – Conversação e Escrita da Komuniki trabalha o desenvolvimento da '
                            'expressão oral e escrita para quem deseja ampliar sua capacidade de se comunicar em '
                            'espanhol.'
                        ),
                    ],
                    'sections': [
                        {
                            'kind': 'cards',
                            'eyebrow': 'Como o curso é organizado',
                            'title': 'Falar, compreender e se expressar',
                            'lead': (
                                'Conhecer palavras e regras é importante, mas utilizar um idioma exige transformar '
                                'esse conhecimento em comunicação. A proposta do curso é trabalhar espanhol a partir '
                                'de duas dimensões complementares: conversação e escrita.'
                            ),
                            'items': [
                                {
                                    'title': 'Conversação',
                                    'body': (
                                        'A prática oral ajuda o aluno a desenvolver mais naturalidade ao formular '
                                        'frases, participar de conversas e expressar ideias em espanhol.'
                                    ),
                                },
                                {
                                    'title': 'Escrita',
                                    'body': (
                                        'A comunicação escrita permite organizar melhor o pensamento e desenvolver '
                                        'maior familiaridade com estruturas e vocabulário do idioma.'
                                    ),
                                },
                                {
                                    'title': 'Vocabulário',
                                    'body': (
                                        'Ampliar o repertório de palavras e expressões oferece mais recursos para '
                                        'lidar com diferentes situações de comunicação.'
                                    ),
                                },
                                {
                                    'title': 'Segurança para se comunicar',
                                    'body': (
                                        'Aprender um idioma também envolve aceitar o processo de tentativa, prática '
                                        'e desenvolvimento: a experiência ajuda a utilizar o que se aprende com '
                                        'progressivamente mais segurança.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'list',
                            'eyebrow': 'Público',
                            'title': 'Para quem é?',
                            'lead': 'O curso pode atender pessoas que desejam:',
                            'items': [
                                'Desenvolver conversação em espanhol',
                                'Aprimorar a comunicação escrita',
                                'Ampliar vocabulário',
                                'Praticar o idioma',
                                'Utilizar espanhol em situações pessoais, acadêmicas ou profissionais',
                                'Desenvolver mais confiança para se expressar',
                            ],
                        },
                    ],
                    'final_cta': {
                        'title': 'Um novo idioma amplia suas possibilidades de comunicação.',
                        'text': (
                            'Aprender espanhol não significa apenas conhecer uma nova língua. Também significa '
                            'poder acessar novas pessoas, conteúdos, culturas e experiências.'
                        ),
                        'primary_label': 'Quero saber mais sobre o curso de Espanhol',
                        'secondary_label': 'Consultar próximas turmas',
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
                    'hero_cta_label': 'Quero destravar minha comunicação',
                    'meta_description': (
                        'Método premiado de comunicação e oratória: 20 horas em curso coletivo ou mentoria '
                        'individual para falar com clareza e segurança na Escola Komuniki.'
                    ),
                    'intro': [
                        (
                            'Ter uma boa ideia é importante. Conseguir transmiti-la com clareza, presença e '
                            'segurança pode fazer toda a diferença.'
                        ),
                        (
                            'O Comunicação Destravada é um método desenvolvido para pessoas que desejam se expressar '
                            'melhor em situações profissionais, acadêmicas e pessoais — seja em uma apresentação, '
                            'reunião, entrevista, vídeo, evento ou simplesmente em uma conversa importante.'
                        ),
                        (
                            'Mais do que ensinar técnicas para "falar bem", a proposta é desenvolver uma comunicação '
                            'mais consciente, natural e autêntica, trabalhando expressão, voz, presença e confiança.'
                        ),
                    ],
                    'sections': [
                        {
                            'kind': 'prose',
                            'eyebrow': 'Sobre o método',
                            'title': 'Comunicação também se desenvolve',
                            'body': [
                                (
                                    'Nem toda dificuldade para se comunicar acontece porque faltam ideias. Às vezes '
                                    'sabemos exatamente o que queremos dizer, mas temos dificuldade para organizar o '
                                    'pensamento, encontramos bloqueios na hora de falar, sentimos insegurança diante '
                                    'de outras pessoas ou simplesmente não conseguimos transmitir a mensagem da '
                                    'maneira que imaginamos.'
                                ),
                                (
                                    'A comunicação pode ser observada, praticada e desenvolvida. O Comunicação '
                                    'Destravada trabalha justamente esse processo: ajudar cada participante a '
                                    'compreender melhor a própria forma de se expressar e desenvolver recursos para '
                                    'comunicar suas ideias com maior clareza e segurança.'
                                ),
                            ],
                        },
                        {
                            'kind': 'cards',
                            'eyebrow': 'O método',
                            'title': 'O que você desenvolve durante o curso?',
                            'items': [
                                {
                                    'title': 'Fala e expressão',
                                    'body': (
                                        'Construção da fala, articulação, clareza e naturalidade para apresentar um '
                                        'pensamento de forma compreensível, sem depender de falas decoradas ou de um '
                                        'estilo artificial de comunicação.'
                                    ),
                                },
                                {
                                    'title': 'Voz e comunicação',
                                    'body': (
                                        'Ritmo, pausas, entonação, volume e articulação podem modificar completamente '
                                        'a maneira como uma mensagem é percebida: recursos para usar a própria voz de '
                                        'forma mais consciente.'
                                    ),
                                },
                                {
                                    'title': 'Segurança para falar',
                                    'body': (
                                        'O objetivo não é eliminar a insegurança, mas desenvolver recursos para que '
                                        'ela deixe de impedir a comunicação, compreendendo melhor as próprias '
                                        'reações diante de câmera, público ou apresentações.'
                                    ),
                                },
                                {
                                    'title': 'Comunicação não verbal',
                                    'body': (
                                        'Postura, gestos, expressão facial, olhar e maneira de ocupar um espaço '
                                        'também participam da mensagem: uma presença mais consciente e coerente com '
                                        'aquilo que se deseja transmitir.'
                                    ),
                                },
                                {
                                    'title': 'Comunicação para vídeos e redes sociais',
                                    'body': (
                                        'Recursos para se posicionar, organizar uma mensagem e comunicar de maneira '
                                        'mais natural em vídeos e conteúdos digitais, cada vez mais relevante para '
                                        'criadores, profissionais e empreendedores.'
                                    ),
                                },
                                {
                                    'title': 'Falar em público',
                                    'body': (
                                        'Organizar a mensagem, compreender o público, trabalhar presença e conduzir '
                                        'a comunicação em apresentações, palestras, reuniões e eventos de forma mais '
                                        'estruturada e segura.'
                                    ),
                                },
                            ],
                        },
                        {
                            'kind': 'callout_award',
                            'eyebrow': 'Reconhecimento',
                            'title': 'Método premiado',
                            'badge_title': 'Prêmio Paulo Freire de Educação — CLDF 2024',
                            'badge_intro': (
                                'A metodologia Comunicação Destravada recebeu o Prêmio Paulo Freire de Educação, '
                                'concedido pela Câmara Legislativa do Distrito Federal em 2024.'
                            ),
                            'body': [
                                (
                                    'O reconhecimento representa um marco na trajetória do método e em sua proposta '
                                    'de utilizar a comunicação como instrumento de desenvolvimento.'
                                ),
                                (
                                    'Essa experiência faz parte do trabalho desenvolvido pela Komuniki para '
                                    'aproximar técnica, expressão, educação e desenvolvimento pessoal.'
                                ),
                            ],
                        },
                        {
                            'kind': 'prose',
                            'eyebrow': 'Formatos',
                            'title': 'Curso coletivo ou mentoria individual',
                            'body': [
                                (
                                    'Pessoas diferentes possuem desafios diferentes ao se comunicar. Por isso, o '
                                    'Comunicação Destravada pode acontecer tanto em formato coletivo quanto por meio '
                                    'de mentoria individual.'
                                ),
                                (
                                    'No curso coletivo, a experiência permite desenvolver a comunicação também por '
                                    'meio da interação, observação e prática com outras pessoas. Na mentoria '
                                    'individual, o acompanhamento pode ser direcionado às necessidades específicas '
                                    'de comunicação do participante.'
                                ),
                            ],
                        },
                        {
                            'kind': 'list',
                            'eyebrow': 'Público',
                            'title': 'Para quem é o Comunicação Destravada?',
                            'lead': 'O método pode ser interessante para:',
                            'items': [
                                'Pessoas que sentem medo ou vergonha de falar em público',
                                'Profissionais que desejam melhorar sua comunicação',
                                'Empreendedores que precisam apresentar ideias e negócios',
                                'Professores, palestrantes e líderes',
                                'Criadores de conteúdo',
                                'Pessoas que produzem vídeos ou conteúdos para redes sociais',
                                'Quem sente dificuldade durante apresentações, entrevistas ou reuniões',
                                'Quem tem boas ideias, mas encontra dificuldade para organizá-las ao falar',
                                'Pessoas que desejam desenvolver mais segurança e presença ao se expressar',
                            ],
                            'note': (
                                'Você não precisa trabalhar profissionalmente com comunicação para desenvolver sua '
                                'forma de comunicar. A comunicação está presente em praticamente todos os ambientes '
                                'em que precisamos apresentar uma ideia, defender um ponto de vista, explicar algo, '
                                'ensinar, liderar ou simplesmente ser compreendidos.'
                            ),
                        },
                        {
                            'kind': 'quote',
                            'title': 'Não existe apenas uma maneira correta de comunicar',
                            'lead': (
                                'Desenvolver comunicação não significa criar um personagem, copiar o estilo de outra '
                                'pessoa ou abandonar sua personalidade. Cada pessoa possui voz, repertório, ritmo e '
                                'maneira própria de se expressar. O objetivo é compreender melhor esses recursos e '
                                'utilizá-los de maneira consciente.'
                            ),
                            'lines': [
                                'Você não precisa nascer comunicador.',
                                'Comunicação também se aprende, se pratica e se desenvolve.',
                            ],
                        },
                    ],
                    'final_cta': {
                        'title': 'Encontre mais liberdade para expressar suas ideias.',
                        'text': (
                            'Uma comunicação mais clara pode transformar a maneira como você apresenta seu '
                            'trabalho, participa de uma reunião, grava um vídeo ou simplesmente conversa com outras '
                            'pessoas. O primeiro passo é aprender a reconhecer e desenvolver os recursos que você '
                            'já possui.'
                        ),
                        'primary_label': 'Quero destravar minha comunicação',
                        'secondary_label': 'Falar com a Komuniki',
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
