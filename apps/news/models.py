import re

from django.conf import settings
from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.sites.models import Site
from django.db import models
from django.urls import reverse
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit, Transpose
from pilkit.processors import MakeOpaque

from apps.common.models import SEOModel, TimeStampedModel
from apps.common.validators import (
    ARTICLE_IMAGE_JPEG_QUALITY,
    ARTICLE_IMAGE_MAX_HEIGHT,
    ARTICLE_IMAGE_MAX_WIDTH,
    validate_uploaded_image,
)


class Category(TimeStampedModel):
    name = models.CharField('Nome', max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField('Descrição', blank=True)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='children', verbose_name='Categoria pai',
        help_text='Deixe vazio para criar uma categoria principal.',
    )
    order = models.PositiveIntegerField('Ordem', default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField('Nome', max_length=200)
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'

    def __str__(self):
        return self.name


class Article(TimeStampedModel, SEOModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Rascunho'
        PUBLISHED = 'published', 'Publicado'
        ARCHIVED = 'archived', 'Arquivado'

    title = models.CharField('Título', max_length=200)
    slug = models.SlugField('URL amigável', max_length=200, unique=True, help_text='Gerado automaticamente a partir do título.')
    excerpt = models.TextField('Resumo', blank=True, help_text='Resumo curto do artigo. Aparece nas listagens e compartilhamentos.')
    content = models.TextField(
        'Conteúdo',
        blank=True,
        editable=False,
        help_text='Texto consolidado dos blocos de conteúdo (gerado automaticamente).',
    )
    featured_image = ProcessedImageField(
        verbose_name='Imagem de capa',
        upload_to='news/articles/',
        blank=True,
        processors=[
            Transpose(),
            ResizeToFit(ARTICLE_IMAGE_MAX_WIDTH, ARTICLE_IMAGE_MAX_HEIGHT, upscale=False),
            MakeOpaque(),
        ],
        format='JPEG',
        options={'quality': ARTICLE_IMAGE_JPEG_QUALITY, 'optimize': True, 'progressive': True},
        validators=[validate_uploaded_image],
        help_text='Imagem principal que aparece no topo do artigo. É convertida e otimizada automaticamente.',
    )
    featured_image_caption = models.CharField('Legenda da imagem', max_length=255, blank=True, help_text='Texto descritivo exibido abaixo da imagem de capa.')
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True,
        related_name='articles', verbose_name='Categoria',
        help_text='Escolha a categoria principal do artigo.',
    )
    tags = models.ManyToManyField(
        Tag, blank=True, related_name='articles', verbose_name='Tags',
        help_text='Digite para buscar tags existentes.',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='articles', verbose_name='Autor',
    )
    site = models.ForeignKey(
        Site, on_delete=models.CASCADE, related_name='articles',
        verbose_name='Site', help_text='Em qual portal este artigo será publicado.',
    )
    status = models.CharField(
        'Status', max_length=20, choices=Status.choices, default=Status.DRAFT,
        help_text='Rascunho: não publicado. Publicado: visível no site. Arquivado: removido do site.',
    )
    published_at = models.DateTimeField('Publicado em', null=True, blank=True, help_text='Data e hora da publicação. Preenchido automaticamente ao publicar.')
    is_featured = models.BooleanField('Destaque', default=False, help_text='Artigos destacados aparecem em posição de destaque na página principal.')
    view_count = models.PositiveIntegerField('Visualizações', default=0)
    meta_title = models.CharField('Título SEO', max_length=70, blank=True, help_text='Título para buscadores (Google). Se vazio, usa o título do artigo.')
    meta_description = models.CharField('Descrição SEO', max_length=160, blank=True, help_text='Descrição para buscadores (Google). Se vazio, usa o resumo.')

    newsletter_sent_at = models.DateTimeField(
        'Newsletter enviada em', null=True, blank=True, editable=False,
        help_text='Preenchido automaticamente quando a newsletter é enviada via sinal ou ação do admin.',
    )

    objects = models.Manager()
    on_site = CurrentSiteManager()

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'Artigo'
        verbose_name_plural = 'Artigos'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('news:article_detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        from django.utils import timezone

        from apps.common.sanitization import sanitize_content

        if self.content:
            self.content = sanitize_content(self.content)

        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def rebuild_content_cache(self):
        """Reconstrói `content` a partir dos blocos (texto + legendas).

        `content` deixou de ser editável: vira a concatenação do texto dos blocos
        e das legendas, alimentando busca, tempo de leitura e teaser da newsletter.
        Usa update() para não disparar save()/sinais novamente (evita recursão).
        """
        from django.utils.html import escape

        parts = []
        for block in self.blocks.all():
            if block.block_type == ArticleBlock.BlockType.RICH_TEXT and block.rich_text:
                parts.append(block.rich_text)
            if block.caption:
                parts.append(f'<p>{escape(block.caption)}</p>')
        new_content = '\n'.join(parts)
        if new_content != self.content:
            type(self).objects.filter(pk=self.pk).update(content=new_content)
            self.content = new_content

    @property
    def reading_time(self):
        """Estimate reading time in minutes (average 200 wpm)."""
        word_count = len(re.findall(r'\w+', self.content))
        return max(1, round(word_count / 200))


class ArticleBlock(TimeStampedModel):
    """Bloco de conteúdo do artigo: texto, imagem ou embed de rede social.

    O corpo do artigo é uma sequência ordenada destes blocos. Embeds guardam só a
    URL/provedor (resolvidos por apps.common.embeds) e são renderizados por
    templates confiáveis — a plataforma nunca vira HTML do usuário.
    """

    class BlockType(models.TextChoices):
        RICH_TEXT = 'rich_text', 'Texto'
        IMAGE = 'image', 'Imagem'
        EMBED = 'embed', 'Vídeo / Post'

    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='blocks', verbose_name='Artigo',
    )
    order = models.PositiveIntegerField('Ordem', default=0, db_index=True)
    block_type = models.CharField(
        'Tipo de bloco', max_length=20,
        choices=BlockType.choices, default=BlockType.RICH_TEXT,
    )
    rich_text = models.TextField(
        'Texto', blank=True,
        help_text='Parágrafos, subtítulos, listas e links do artigo.',
    )
    media = models.ForeignKey(
        'media_library.MediaFile', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='article_blocks',
        verbose_name='Imagem',
        help_text='Selecione na Biblioteca de Mídia ou envie uma nova (otimizada automaticamente).',
    )
    caption = models.CharField(
        'Legenda', max_length=255, blank=True,
        help_text='Texto opcional exibido abaixo da imagem ou do vídeo/post.',
    )
    embed_url = models.URLField(
        'Link do vídeo/post', blank=True,
        help_text='Cole o link do YouTube, Instagram ou TikTok. O embed é gerado automaticamente.',
    )
    embed_provider = models.CharField('Plataforma', max_length=20, blank=True, editable=False)
    embed_id = models.CharField('ID do embed', max_length=255, blank=True, editable=False)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Bloco de conteúdo'
        verbose_name_plural = 'Blocos de conteúdo'
        indexes = [models.Index(fields=['article', 'order'])]

    def __str__(self):
        return f'{self.get_block_type_display()} #{self.order}'

    @property
    def partial_template(self):
        return f'news/partials/blocks/{self.block_type}.html'

    @property
    def embed(self):
        """EmbedData (provider, embed_url, thumbnail, aspect) ou None."""
        if self.block_type != self.BlockType.EMBED or not self.embed_url:
            return None
        from apps.common.embeds import resolve_embed
        return resolve_embed(self.embed_url)

    def save(self, *args, **kwargs):
        from apps.common.embeds import resolve_embed
        from apps.common.sanitization import sanitize_content

        if self.block_type == self.BlockType.RICH_TEXT and self.rich_text:
            self.rich_text = sanitize_content(self.rich_text)

        if self.block_type == self.BlockType.EMBED and self.embed_url:
            data = resolve_embed(self.embed_url)
            self.embed_provider = data.provider if data else ''
            self.embed_id = data.embed_id if data else ''
        else:
            self.embed_provider = ''
            self.embed_id = ''

        super().save(*args, **kwargs)


class NewsletterSubscription(TimeStampedModel):
    email = models.EmailField('E-mail')
    is_active = models.BooleanField(
        'Ativo', default=True,
        help_text='Desmarque para cancelar a inscrição deste email.',
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='newsletter_subscriptions',
        verbose_name='Site',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Assinatura de Newsletter'
        verbose_name_plural = 'Assinaturas de Newsletter'
        unique_together = [['email', 'site']]

    def __str__(self):
        return self.email


class NewsletterDelivery(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        SENT = 'sent', 'Enviado'
        FAILED = 'failed', 'Falhou'
        SKIPPED = 'skipped', 'Ignorado'

    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='newsletter_deliveries', verbose_name='Artigo',
    )
    subscription = models.ForeignKey(
        NewsletterSubscription, on_delete=models.CASCADE,
        related_name='deliveries', verbose_name='Assinatura',
    )
    email = models.EmailField('E-mail')
    status = models.CharField(
        'Status', max_length=20, choices=Status.choices, default=Status.PENDING,
    )
    attempts = models.PositiveSmallIntegerField('Tentativas', default=0)
    last_error = models.TextField('Último erro', blank=True)
    sent_at = models.DateTimeField('Enviado em', null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Entrega de Newsletter'
        verbose_name_plural = 'Entregas de Newsletter'
        unique_together = [['article', 'subscription']]
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['article', 'status']),
        ]

    def __str__(self):
        return f'{self.email} — {self.article.title}'


class ArticleLike(TimeStampedModel):
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='likes', verbose_name='Artigo',
    )
    ip_address = models.GenericIPAddressField('Endereço IP', null=True, blank=True)
    session_key = models.CharField('Chave de sessão', max_length=40, null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='article_likes', verbose_name='Usuário',
    )

    class Meta:
        verbose_name = 'Curtida'
        verbose_name_plural = 'Curtidas'
        unique_together = [['article', 'ip_address', 'session_key', 'user']]

    def __str__(self):
        return f'Curtida em {self.article.title}'


class Comment(TimeStampedModel):
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='comments', verbose_name='Artigo',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='comments', verbose_name='Usuário',
    )
    content = models.TextField('Comentário')
    is_active = models.BooleanField(
        'Visível', default=True,
        help_text='Desmarque para ocultar este comentário do portal.',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Comentário'
        verbose_name_plural = 'Comentários'

    def __str__(self):
        return f'{self.user} em {self.article.title}'


class ArticleBookmark(TimeStampedModel):
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='bookmarks', verbose_name='Artigo',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='bookmarked_articles', verbose_name='Usuário',
    )

    class Meta:
        verbose_name = 'Favorito'
        verbose_name_plural = 'Favoritos'
        unique_together = [['article', 'user']]

    def __str__(self):
        return f'{self.user} favoritou {self.article.title}'
