from django.shortcuts import get_object_or_404, render

from .models import Page, SchoolFeature, SchoolHomeConfig, TeamMember, Testimonial

HOME_FALLBACK = {
    'hero_badge': 'Educação com propósito',
    'hero_title': 'Educação que prepara para o futuro',
    'hero_subtitle': 'Um ambiente de aprendizagem que une cuidado, conhecimento e desenvolvimento humano para acompanhar cada estudante de perto.',
    'visual_eyebrow': 'Comunidade escolar',
    'visual_title': 'Aprender com presença, escuta e projeto.',
    'visual_footer_title': 'Famílias, estudantes e educadores no mesmo projeto',
    'visual_footer_text': 'Comunicação clara para que a comunidade acompanhe a vida escolar com confiança.',
    'proposal_eyebrow': 'Proposta pedagógica',
    'proposal_title': 'Por que escolher nossa escola?',
    'proposal_description': 'Uma experiência escolar consistente nasce do equilíbrio entre método, vínculo humano, segurança e projetos que ampliam repertórios.',
    'life_eyebrow': 'Vida escolar',
    'life_title': 'Uma escola com presença, projetos e comunidade',
    'life_description': 'O cotidiano escolar ganha força quando aprendizagem, cultura, movimento e convivência se encontram em experiências reais.',
    'team_eyebrow': 'Nossa equipe',
    'team_title': 'Pessoas que constroem a experiência escolar',
    'team_description': 'Educadores e profissionais que acompanham a rotina da escola com cuidado, organização e compromisso formativo.',
    'testimonials_eyebrow': 'Depoimentos',
    'testimonials_title': 'Vozes da comunidade',
    'testimonials_description': 'Relatos ajudam a mostrar a relação de confiança construída no cotidiano escolar.',
    'hiring_title': 'Faça parte da nossa equipe',
    'hiring_description': 'Profissionais da educação encontram aqui um espaço para conhecer oportunidades e participar de uma comunidade comprometida com formação humana.',
    'contact_title': 'Vamos conversar?',
    'contact_description': 'Pais, responsáveis e comunidade podem entrar em contato para tirar dúvidas, enviar mensagens ou iniciar uma conversa com a escola.',
}

TRUST_FEATURES_FALLBACK = [
    {'title': 'Acompanhamento próximo', 'description': 'Olhar atento para ritmos, histórias e objetivos.', 'tone': 'emerald'},
    {'title': 'Equipe qualificada', 'description': 'Educadores comprometidos com aprendizagem e cuidado.', 'tone': 'slate'},
    {'title': 'Projetos formativos', 'description': 'Cultura, investigação e convivência no cotidiano.', 'tone': 'amber'},
    {'title': 'Comunicação com famílias', 'description': 'Relação transparente entre escola e responsáveis.', 'tone': 'emerald'},
]

PROPOSAL_FEATURES_FALLBACK = [
    {'title': 'Formação integral', 'description': 'Projetos, convivência e aprendizagem caminham juntos na formação da nossa comunidade.', 'tone': 'emerald'},
    {'title': 'Metodologia ativa', 'description': 'Os estudantes participam, investigam e constroem sentidos em experiências bem orientadas.', 'tone': 'amber'},
    {'title': 'Acompanhamento individual', 'description': 'Acompanhamos cada estudante de perto, respeitando ritmos, histórias e objetivos.', 'tone': 'slate'},
    {'title': 'Ambiente seguro', 'description': 'Cuidado, organização e escuta sustentam uma rotina escolar acolhedora e confiável.', 'tone': 'emerald'},
    {'title': 'Projetos e cultura', 'description': 'A escola é construída todos os dias por estudantes, famílias e educadores.', 'tone': 'amber'},
    {'title': 'Tecnologia com propósito', 'description': 'A tecnologia aparece como ferramenta de aprendizagem, não como fim em si mesma.', 'tone': 'slate'},
]

LIFE_FEATURES_FALLBACK = [
    {'title': 'Projetos pedagógicos', 'description': 'Percursos de investigação que conectam conhecimento, autoria e colaboração.', 'tone': 'emerald'},
    {'title': 'Cultura e arte', 'description': 'Expressão, repertório e sensibilidade fazem parte da formação cotidiana.', 'tone': 'white'},
    {'title': 'Esportes e movimento', 'description': 'Corpo, cooperação e saúde aparecem como dimensões importantes do aprender.', 'tone': 'white'},
    {'title': 'Eventos e comunidade', 'description': 'Encontros que aproximam famílias, estudantes e educadores.', 'tone': 'amber'},
]


def _features_for_site(site, placement, fallback):
    features = list(
        SchoolFeature.on_site
        .filter(site=site, placement=placement, is_active=True)
        .order_by('order', 'title')
    )
    return features or fallback


def home(request):
    site = request.site
    home_config = (
        SchoolHomeConfig.on_site
        .filter(site=site, is_active=True)
        .first()
        or HOME_FALLBACK
    )
    trust_features = _features_for_site(site, SchoolFeature.Placement.TRUST, TRUST_FEATURES_FALLBACK)
    proposal_features = _features_for_site(site, SchoolFeature.Placement.PROPOSAL, PROPOSAL_FEATURES_FALLBACK)
    life_features = _features_for_site(site, SchoolFeature.Placement.LIFE, LIFE_FEATURES_FALLBACK)
    testimonials = Testimonial.on_site.filter(site=site, is_featured=True)[:3]
    team_members = TeamMember.on_site.filter(site=site, is_active=True).order_by('order', 'name')[:4]
    return render(request, 'school/home.html', {
        'home_config': home_config,
        'trust_features': trust_features,
        'hero_features': trust_features[:2],
        'proposal_features': proposal_features,
        'life_features': life_features,
        'testimonials': testimonials,
        'team_members': team_members,
    })


def page_detail(request, slug):
    page = get_object_or_404(Page.on_site, site=request.site, slug=slug, is_published=True)
    return render(request, 'school/page_detail.html', {'page': page})


def team_list(request):
    members = TeamMember.on_site.filter(site=request.site, is_active=True)
    return render(request, 'school/team_list.html', {'members': members})


def privacy(request):
    return render(request, 'school/privacy.html')


def about(request):
    return render(request, 'school/about.html')
