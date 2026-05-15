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
        help_text='Nome exibido como remetente. Ex: Equipe News Portal',
    )
    google_analytics_id = models.CharField(max_length=30, blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)

    class Meta:
        verbose_name = 'Configuração do Site'
        verbose_name_plural = 'Configurações dos Sites'

    def __str__(self):
        return f'Configurações de {self.site.name}'
