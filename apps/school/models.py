from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.sites.models import Site
from django.db import models

from apps.common.models import SEOModel, TimeStampedModel


class Page(TimeStampedModel, SEOModel):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='pages', verbose_name='Site')
    title = models.CharField('Título', max_length=200)
    slug = models.SlugField('URL amigável', max_length=200)
    content = models.TextField('Conteúdo', blank=True)
    featured_image = models.ImageField('Imagem destacada', upload_to='school/pages/', blank=True)
    is_published = models.BooleanField('Publicado', default=False)
    order = models.PositiveIntegerField('Ordem', default=0)

    objects = models.Manager()
    on_site = CurrentSiteManager()

    class Meta:
        ordering = ['order', 'title']
        verbose_name = 'Página'
        verbose_name_plural = 'Páginas'
        constraints = [
            models.UniqueConstraint(fields=['site', 'slug'], name='unique_school_page_slug_per_site'),
        ]

    def __str__(self):
        return f'{self.title} ({self.site.name})'

    def save(self, *args, **kwargs):
        from apps.common.sanitization import sanitize_content
        if self.content:
            self.content = sanitize_content(self.content)
        super().save(*args, **kwargs)


class SchoolHomeConfig(TimeStampedModel, SEOModel):
    site = models.OneToOneField(Site, on_delete=models.CASCADE, related_name='school_home_config')
    hero_badge = models.CharField('Selo do hero', max_length=120, default='Educação com propósito')
    hero_title = models.CharField('Título do hero', max_length=200, default='Educação que prepara para o futuro')
    hero_subtitle = models.TextField(
        'Subtítulo do hero',
        default='Um ambiente de aprendizagem que une cuidado, conhecimento e desenvolvimento humano para acompanhar cada estudante de perto.',
    )
    visual_eyebrow = models.CharField('Chamada visual', max_length=120, default='Comunidade escolar')
    visual_title = models.CharField('Título do bloco visual', max_length=200, default='Aprender com presença, escuta e projeto.')
    visual_footer_title = models.CharField('Título do bloco de comunidade', max_length=200, default='Famílias, estudantes e educadores no mesmo projeto')
    visual_footer_text = models.TextField(
        'Texto do bloco de comunidade',
        default='Comunicação clara para que a comunidade acompanhe a vida escolar com confiança.',
    )
    proposal_eyebrow = models.CharField('Chamada da proposta', max_length=120, default='Proposta pedagógica')
    proposal_title = models.CharField('Título da proposta', max_length=200, default='Por que escolher nossa escola?')
    proposal_description = models.TextField(
        'Descrição da proposta',
        default='Uma experiência escolar consistente nasce do equilíbrio entre método, vínculo humano, segurança e projetos que ampliam repertórios.',
    )
    life_eyebrow = models.CharField('Chamada de vida escolar', max_length=120, default='Vida escolar')
    life_title = models.CharField('Título de vida escolar', max_length=200, default='Uma escola com presença, projetos e comunidade')
    life_description = models.TextField(
        'Descrição de vida escolar',
        default='O cotidiano escolar ganha força quando aprendizagem, cultura, movimento e convivência se encontram em experiências reais.',
    )
    team_eyebrow = models.CharField('Chamada da equipe', max_length=120, default='Nossa equipe')
    team_title = models.CharField('Título da equipe', max_length=200, default='Pessoas que constroem a experiência escolar')
    team_description = models.TextField(
        'Descrição da equipe',
        default='Educadores e profissionais que acompanham a rotina da escola com cuidado, organização e compromisso formativo.',
    )
    testimonials_eyebrow = models.CharField('Chamada de depoimentos', max_length=120, default='Depoimentos')
    testimonials_title = models.CharField('Título de depoimentos', max_length=200, default='Vozes da comunidade')
    testimonials_description = models.TextField(
        'Descrição de depoimentos',
        default='Relatos ajudam a mostrar a relação de confiança construída no cotidiano escolar.',
    )
    hiring_title = models.CharField('Título de trabalhe conosco', max_length=200, default='Faça parte da nossa equipe')
    hiring_description = models.TextField(
        'Descrição de trabalhe conosco',
        default='Profissionais da educação encontram aqui um espaço para conhecer oportunidades e participar de uma comunidade comprometida com formação humana.',
    )
    contact_title = models.CharField('Título de contato', max_length=200, default='Vamos conversar?')
    contact_description = models.TextField(
        'Descrição de contato',
        default='Pais, responsáveis e comunidade podem entrar em contato para tirar dúvidas, enviar mensagens ou iniciar uma conversa com a escola.',
    )
    is_active = models.BooleanField('Ativo', default=True)

    objects = models.Manager()
    on_site = CurrentSiteManager()

    class Meta:
        verbose_name = 'Configuração da Home Escolar'
        verbose_name_plural = 'Configurações da Home Escolar'

    def __str__(self):
        return f'Home escolar - {self.site.name}'


class SchoolFeature(TimeStampedModel):
    class Placement(models.TextChoices):
        TRUST = 'trust', 'Barra de confiança'
        PROPOSAL = 'proposal', 'Proposta pedagógica'
        LIFE = 'life', 'Vida escolar'

    class Tone(models.TextChoices):
        EMERALD = 'emerald', 'Verde institucional'
        AMBER = 'amber', 'Âmbar'
        SLATE = 'slate', 'Slate'
        WHITE = 'white', 'Branco'

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='school_features', verbose_name='Site')
    placement = models.CharField('Local de exibição', max_length=20, choices=Placement.choices)
    title = models.CharField('Título', max_length=160)
    description = models.TextField('Descrição')
    tone = models.CharField('Tom visual', max_length=20, choices=Tone.choices, default=Tone.EMERALD)
    is_active = models.BooleanField('Ativo', default=True)
    order = models.PositiveIntegerField('Ordem', default=0)

    objects = models.Manager()
    on_site = CurrentSiteManager()

    class Meta:
        ordering = ['placement', 'order', 'title']
        verbose_name = 'Diferencial da Escola'
        verbose_name_plural = 'Diferenciais da Escola'
        constraints = [
            models.UniqueConstraint(fields=['site', 'placement', 'title'], name='unique_school_feature_title_per_site_placement'),
        ]

    def __str__(self):
        return f'{self.title} ({self.get_placement_display()})'


class TeamMember(TimeStampedModel):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='team_members', verbose_name='Site')
    name = models.CharField('Nome', max_length=200)
    title = models.CharField('Cargo ou função', max_length=200)
    photo = models.ImageField('Foto', upload_to='school/team/', blank=True)
    bio = models.TextField('Biografia', blank=True)
    email = models.EmailField('E-mail', blank=True)
    is_active = models.BooleanField('Ativo', default=True)
    order = models.PositiveIntegerField('Ordem', default=0)

    objects = models.Manager()
    on_site = CurrentSiteManager()

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Membro da Equipe'
        verbose_name_plural = 'Membros da Equipe'

    def __str__(self):
        return self.name


class Testimonial(TimeStampedModel):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='testimonials', verbose_name='Site')
    name = models.CharField('Nome', max_length=200)
    relationship = models.CharField('Relação com a escola', max_length=200, blank=True)
    quote = models.TextField('Depoimento')
    photo = models.ImageField('Foto', upload_to='school/testimonials/', blank=True)
    is_featured = models.BooleanField('Destacado', default=False)

    objects = models.Manager()
    on_site = CurrentSiteManager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Depoimento'
        verbose_name_plural = 'Depoimentos'

    def __str__(self):
        return self.name
