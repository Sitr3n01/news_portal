from django.contrib.sites.models import Site
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SEOModel(models.Model):
    meta_title = models.CharField('Título SEO', max_length=70, blank=True, help_text='Título para buscadores (Google). Recomendado: até 70 caracteres.')
    meta_description = models.CharField('Descrição SEO', max_length=160, blank=True, help_text='Descrição para buscadores (Google). Recomendado: até 160 caracteres.')
    meta_keywords = models.CharField('Palavras-chave SEO', max_length=255, blank=True, help_text='Palavras-chave separadas por vírgula. Ex: educação, escola, notícias.')

    class Meta:
        abstract = True


class SiteExtension(models.Model):
    site = models.OneToOneField(Site, on_delete=models.CASCADE, related_name='extension')
    tagline = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to='site_logos/', blank=True)
    favicon = models.ImageField(upload_to='site_favicons/', blank=True)
    primary_email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    newsletter_from_email = models.EmailField(
        'E-mail remetente da Newsletter', blank=True,
        help_text='E-mail que aparecerá como remetente das newsletters. Ex: noticias@seusite.com',
    )
    newsletter_from_name = models.CharField(
        'Nome remetente da Newsletter', max_length=100, blank=True,
        help_text='Nome exibido como remetente. Ex: Blog da Kelly',
    )
    google_analytics_id = models.CharField(max_length=30, blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    tiktok_url = models.URLField('TikTok', blank=True)
    youtube_url = models.URLField(blank=True)

    # ── Seção "Redes sociais" da home ────────────────────────────────────────
    social_section_enabled = models.BooleanField(
        'Exibir seção de redes na home', default=True,
        help_text='Quando ativo, a home mostra a seção de redes sociais (botões e posts recentes).',
    )
    social_show_instagram = models.BooleanField(
        'Exibir Instagram na seção', default=True,
        help_text='Mostra o botão e os posts do Instagram na seção da home.',
    )
    social_show_tiktok = models.BooleanField(
        'Exibir TikTok na seção', default=True,
        help_text='Mostra os posts do TikTok na seção da home.',
    )
    social_section_title = models.CharField(
        'Título da seção de redes', max_length=120,
        default='Acompanhe a Komuniki nas redes',
    )
    social_section_title_en = models.CharField(
        'Título da seção de redes (EN)', max_length=120, blank=True,
        default='Follow Komuniki on social media',
        help_text='Opcional. Se vazio, usa o título em português.',
    )
    social_section_subtitle = models.CharField(
        'Subtítulo da seção de redes', max_length=255,
        default='Veja bastidores, conteúdos, eventos e novidades publicados no Instagram e TikTok.',
    )
    social_section_subtitle_en = models.CharField(
        'Subtítulo da seção de redes (EN)', max_length=255, blank=True,
        default='See behind the scenes, content, events and news posted on Instagram and TikTok.',
        help_text='Opcional. Se vazio, usa o subtítulo em português.',
    )

    class Meta:
        verbose_name = 'Configuração do Site'
        verbose_name_plural = 'Configurações dos Sites'

    def __str__(self):
        return f'Configurações de {self.site.name}'
