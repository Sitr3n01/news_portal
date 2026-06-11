import uuid

from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.sites.models import Site
from django.db import models
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit, Transpose
from pilkit.processors import MakeOpaque

from apps.common.models import TimeStampedModel
from apps.common.validators import (
    ARTICLE_IMAGE_JPEG_QUALITY,
    ARTICLE_IMAGE_MAX_HEIGHT,
    ARTICLE_IMAGE_MAX_WIDTH,
    validate_uploaded_image,
)


class Platform(models.TextChoices):
    INSTAGRAM = 'instagram', 'Instagram'
    TIKTOK = 'tiktok', 'TikTok'


class SyncStatus(models.TextChoices):
    NEVER = 'never', 'Nunca sincronizado'
    SUCCESS = 'success', 'Sucesso'
    FAILED = 'failed', 'Falha'
    PARTIAL = 'partial', 'Parcial'


class MediaType(models.TextChoices):
    IMAGE = 'image', 'Imagem'
    VIDEO = 'video', 'Vídeo'
    CAROUSEL = 'carousel', 'Carrossel'
    REEL = 'reel', 'Reel'
    UNKNOWN = 'unknown', 'Desconhecido'


def social_thumbnail_upload_path(instance, filename):
    # Nome opaco + .jpg: o ProcessedImageField sempre grava JPEG otimizado.
    return f'social/thumbnails/{uuid.uuid4().hex}.jpg'


class SocialAccount(TimeStampedModel):
    """Perfil oficial de uma rede social (Instagram/TikTok) de um Site.

    Guarda os links públicos e — opcionalmente — credenciais de API para a
    sincronização automática. Sem credenciais, a conta ainda serve para exibir
    os botões das redes e agrupar posts cadastrados manualmente.
    """

    site = models.ForeignKey(
        Site, on_delete=models.CASCADE,
        related_name='social_accounts', verbose_name='Site',
    )
    platform = models.CharField('Plataforma', max_length=20, choices=Platform.choices)
    display_name = models.CharField(
        'Nome de exibição', max_length=120,
        help_text='Nome amigável usado no admin. Ex: Komuniki no Instagram.',
    )
    username = models.CharField(
        'Usuário (@)', max_length=120, blank=True,
        help_text='Nome de usuário público, sem o @. Ex: komunikiescola.',
    )
    profile_url = models.URLField(
        'Link do perfil', blank=True,
        help_text='Endereço público do perfil. Ex: https://www.instagram.com/komunikiescola/',
    )
    external_user_id = models.CharField(
        'ID da conta na API', max_length=120, blank=True,
        help_text='Preenchido ao conectar a API oficial. Pode ficar em branco no uso manual.',
    )
    access_token = models.TextField(
        'Token de acesso', blank=True,
        help_text='Sensível. Usado apenas para conectar a API oficial. '
                  'Prefira variável de ambiente; nunca compartilhe nem versione.',
    )
    refresh_token = models.TextField(
        'Token de atualização', blank=True,
        help_text='Sensível. Opcional, usado por algumas APIs para renovar o acesso.',
    )
    token_expires_at = models.DateTimeField('Token expira em', null=True, blank=True)
    is_active = models.BooleanField(
        'Ativa', default=True,
        help_text='Apenas contas ativas aparecem no site e são sincronizadas.',
    )
    last_sync_at = models.DateTimeField('Última sincronização', null=True, blank=True)
    last_sync_status = models.CharField(
        'Status da última sincronização', max_length=20,
        choices=SyncStatus.choices, default=SyncStatus.NEVER,
    )
    last_sync_error = models.TextField('Erro da última sincronização', blank=True)

    objects = models.Manager()
    on_site = CurrentSiteManager()

    class Meta:
        ordering = ['platform', 'display_name']
        verbose_name = 'Conta de Rede Social'
        verbose_name_plural = 'Contas de Redes Sociais'
        constraints = [
            models.UniqueConstraint(
                fields=['site', 'platform', 'username'],
                name='unique_social_account_per_site_platform_username',
            ),
        ]

    def __str__(self):
        return f'{self.display_name} ({self.get_platform_display()})'


class SocialPost(TimeStampedModel):
    """Publicação de rede social salva no banco e renderizada como card próprio.

    Pode vir da sincronização da API (is_manual=False) ou ser cadastrada à mão no
    admin (is_manual=True). A home nunca depende de embed externo: usa só estes dados.
    """

    account = models.ForeignKey(
        SocialAccount, on_delete=models.CASCADE,
        related_name='posts', verbose_name='Conta',
    )
    # Desnormalizado da conta para permitir índice/filtro direto por plataforma.
    platform = models.CharField('Plataforma', max_length=20, choices=Platform.choices, db_index=True)
    external_id = models.CharField(
        'ID do post na plataforma', max_length=255, blank=True,
        help_text='ID do post na API. Em posts manuais é gerado automaticamente.',
    )
    permalink = models.URLField(
        'Link público do post', max_length=500,
        help_text='Endereço da publicação original. Ex: https://www.instagram.com/p/XXXX/',
    )
    caption = models.TextField('Legenda', blank=True)
    media_type = models.CharField(
        'Tipo de mídia', max_length=20,
        choices=MediaType.choices, default=MediaType.UNKNOWN,
    )
    thumbnail_url = models.URLField(
        'URL da miniatura', max_length=500, blank=True,
        help_text='Usada pela sincronização automática. Pode ficar em branco e enviar uma imagem abaixo.',
    )
    media_url = models.URLField(
        'URL da mídia', max_length=500, blank=True,
        help_text='Link direto da imagem/vídeo na plataforma (opcional).',
    )
    thumbnail_image = ProcessedImageField(
        verbose_name='Imagem da miniatura (upload)',
        upload_to=social_thumbnail_upload_path,
        blank=True,
        processors=[
            Transpose(),
            ResizeToFit(ARTICLE_IMAGE_MAX_WIDTH, ARTICLE_IMAGE_MAX_HEIGHT, upscale=False),
            MakeOpaque(),
        ],
        format='JPEG',
        options={'quality': ARTICLE_IMAGE_JPEG_QUALITY, 'optimize': True, 'progressive': True},
        validators=[validate_uploaded_image],
        help_text='Opcional. Para posts manuais: envie uma imagem (otimizada automaticamente). '
                  'Tem prioridade sobre a URL da miniatura.',
    )
    published_at = models.DateTimeField('Publicado em', db_index=True)
    is_visible = models.BooleanField('Visível no site', default=True)
    is_manual = models.BooleanField(
        'Cadastrado manualmente', default=True,
        help_text='Desmarcado automaticamente quando o post vem da sincronização da API.',
    )
    sync_payload = models.JSONField(
        'Payload da sincronização', default=dict, blank=True,
        help_text='Resumo técnico do retorno da API. Não contém tokens.',
    )

    objects = models.Manager()

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'Post de Rede Social'
        verbose_name_plural = 'Posts de Redes Sociais'
        constraints = [
            models.UniqueConstraint(
                fields=['platform', 'external_id'],
                name='unique_social_post_platform_external_id',
            ),
        ]
        indexes = [
            models.Index(fields=['platform']),
            models.Index(fields=['published_at']),
            models.Index(fields=['is_visible']),
        ]

    def __str__(self):
        return f'{self.get_platform_display()} · {self.external_id or self.pk}'

    @property
    def thumbnail(self):
        """URL da miniatura a exibir: o upload manual tem prioridade, depois a URL
        da API; vazio quando não há nenhuma (o template cai no placeholder)."""
        if self.thumbnail_image:
            return self.thumbnail_image.url
        return self.thumbnail_url or ''

    @property
    def is_video(self):
        return self.media_type in {MediaType.VIDEO, MediaType.REEL}

    def save(self, *args, **kwargs):
        # A plataforma do post sempre acompanha a da conta — evita divergência e
        # dispensa o admin de reescolher (campo é readonly no admin).
        if self.account_id and not self.platform:
            self.platform = self.account.platform
        # Posts manuais não têm ID de API; geramos um estável para satisfazer a
        # UniqueConstraint (platform, external_id) sem colidir entre si.
        if self.is_manual and not self.external_id:
            self.external_id = f'manual-{uuid.uuid4().hex}'
        super().save(*args, **kwargs)
