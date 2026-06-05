from django.db import migrations


KOMUNIKI_ADDRESS = 'QI 11 Bloco A Comércio Local salas 102/104 Guará 1\nBrasília DF, 70274-530, BR'


HOME_CONTENT = {
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
    'meta_title': 'Komuniki - Comunicação que gera resultados',
    'meta_description': 'Cursos e mentorias em comunicação, artes e liderança com Kelly Farias.',
    'meta_keywords': 'komuniki, kelly farias, comunicação, artes, liderança, cursos, mentorias',
    'is_active': True,
}


FEATURES = [
    ('trust', 'Mentorias com Kelly Farias', 'Acompanhamento para desenvolver presença, estilo de comunicação e clareza na expressão.', 'emerald', 1),
    ('trust', 'Cursos online, híbridos e presenciais', 'Formações flexíveis para comunicação, artes, liderança e produção.', 'slate', 2),
    ('trust', 'Atuação corporativa', 'Mentorias, palestras e comunicação interna para equipes e projetos.', 'emerald', 3),
    ('trust', 'Projeto Jovem Comunicador', 'Iniciativa social voltada a jovens em situação de vulnerabilidade social.', 'slate', 4),
    ('proposal', 'Comunicador Profissionalizante', 'Formação de 350 horas em 18 meses, com encaminhamento para registro profissional de Comunicador.', 'emerald', 1),
    ('proposal', 'Produção Cultural', 'Formação de 250 horas em 12 meses, com encaminhamento para registro profissional Diretor de produção.', 'slate', 2),
    ('proposal', 'Jornalismo Cultural', 'Curso livre de 30 horas para jornalistas, influenciadores e produtores de conteúdo.', 'emerald', 3),
    ('proposal', 'Apresentação de Palco e Eventos', 'Curso livre de 50 horas com técnicas de apresentação e condução de eventos.', 'slate', 4),
    ('proposal', 'Espanhol – Conversação e Escrita', 'Curso livre para desenvolvimento da comunicação oral e escrita.', 'emerald', 5),
    ('proposal', 'Comunicação Destravada', '20 horas em curso coletivo ou mentoria individual para oratória, comunicação e autoconfiança.', 'slate', 6),
    ('life', 'Comunicador Profissionalizante', 'Formação de 350 horas, com encaminhamento para registro profissional de Comunicador.', 'emerald', 1),
    ('life', 'Arte e empreendedorismo', 'Formações como Artista Empreendedor, Estilo de Comunicação e Conexão.', 'white', 2),
    ('life', 'Eventos e palestras', 'Encontros, fórum de protagonismo juvenil e experiências formativas ao vivo.', 'white', 3),
    ('life', 'Certificação e registro profissional', 'Cursos com certificação e consulta de disponibilidade para autorização via sindicatos.', 'slate', 4),
]


COURSES_CONTENT = """
<p>A Komuniki oferece formações profissionalizantes, cursos livres e experiências de desenvolvimento pessoal para comunicação, cultura, palco, escrita e presença profissional.</p>

<h2>Formação profissionalizante</h2>
<ul>
    <li><strong>Comunicador Profissionalizante:</strong> 350 horas, duração de 18 meses, requisito de Ensino Médio completo e encaminhamento para registro profissional de Comunicador.</li>
    <li><strong>Produção Cultural:</strong> 250 horas, duração de 12 meses, requisito de Ensino Médio completo e encaminhamento para registro profissional Diretor de produção.</li>
</ul>

<h2>Cursos livres</h2>
<ul>
    <li><strong>Jornalismo Cultural:</strong> 30 horas, para jornalistas, influenciadores e produtores de conteúdo. Requisito: Graduação na área de Comunicação.</li>
    <li><strong>Apresentação de Palco e Eventos:</strong> 50 horas, com técnicas de apresentação e condução de eventos. Requisito: Ensino Médio completo.</li>
    <li><strong>Espanhol – Conversação e Escrita:</strong> curso livre para desenvolvimento da comunicação oral e escrita. Requisito: Ensino Fundamental completo.</li>
</ul>

<h2>Desenvolvimento pessoal e comunicação</h2>
<ul>
    <li><strong>Comunicação Destravada:</strong> 20 horas, em curso coletivo ou mentoria individual, para desenvolvimento da oratória, comunicação e autoconfiança.</li>
</ul>

<p><strong>Reconhecimento:</strong> Vencedor do Prêmio Paulo Freire de Educação 2024.</p>

<p>Para consultar próximas turmas, formatos disponíveis e detalhes de certificação, entre em contato com a Komuniki.</p>
""".strip()


def apply_komuniki_content(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    SiteExtension = apps.get_model('common', 'SiteExtension')
    SchoolHomeConfig = apps.get_model('school', 'SchoolHomeConfig')
    SchoolFeature = apps.get_model('school', 'SchoolFeature')
    TeamMember = apps.get_model('school', 'TeamMember')
    Page = apps.get_model('school', 'Page')

    site, _ = Site.objects.update_or_create(
        id=1,
        defaults={'domain': 'www.komuniki.com.br', 'name': 'Komuniki'},
    )

    SiteExtension.objects.update_or_create(
        site=site,
        defaults={
            'tagline': 'Comunicação que gera resultados',
            'primary_email': 'komunikicomunicacao@gmail.com',
            'phone_number': '(61) 92003-8428',
            'address': KOMUNIKI_ADDRESS,
            'facebook_url': 'https://www.facebook.com/Komunikicomunicacao/',
            'instagram_url': 'https://www.instagram.com/komunikiagencia/',
            'youtube_url': 'https://www.youtube.com/channel/UCidKmbl0ENPRl5vy70-GwfA',
            'newsletter_from_email': 'komunikicomunicacao@gmail.com',
            'newsletter_from_name': 'Komuniki',
        },
    )

    SchoolHomeConfig.objects.update_or_create(site=site, defaults=HOME_CONTENT)

    for placement, title, description, tone, order in FEATURES:
        SchoolFeature.objects.update_or_create(
            site=site,
            placement=placement,
            title=title,
            defaults={
                'description': description,
                'tone': tone,
                'order': order,
                'is_active': True,
            },
        )

    kelly = TeamMember.objects.filter(site=site, name='Kelly Farias').first()
    kelly_defaults = {
        'title': 'CEO da Komuniki',
        'bio': 'Atriz e jornalista de formação. Também é radialista, diretora de produção executiva, editora-chefe, mentora e professora de comunicação.',
        'email': 'komunikicomunicacao@gmail.com',
        'is_active': True,
        'order': 1,
    }
    if kelly:
        for field, value in kelly_defaults.items():
            setattr(kelly, field, value)
        kelly.save()
    else:
        TeamMember.objects.create(site=site, name='Kelly Farias', **kelly_defaults)

    Page.objects.update_or_create(
        site=site,
        slug='cursos',
        defaults={
            'title': 'Cursos',
            'content': COURSES_CONTENT,
            'is_published': True,
            'order': 10,
            'meta_title': 'Cursos Komuniki',
            'meta_description': 'Cursos de comunicação, teatro, produção, locução, apresentação e jornalismo cultural da Komuniki.',
            'meta_keywords': 'cursos komuniki, comunicação, teatro, produção cultural, locução, jornalismo cultural',
        },
    )


def reverse_komuniki_content(apps, schema_editor):
    # Conteúdo institucional pode ter sido editado depois da migração; não removemos no rollback.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0004_siteextension_newsletter_from_email_and_more'),
        ('school', '0006_pt_br_admin_field_labels'),
    ]

    operations = [
        migrations.RunPython(apply_komuniki_content, reverse_komuniki_content),
    ]
