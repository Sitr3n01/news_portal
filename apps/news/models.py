import logging
import re

from django.conf import settings
from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.sites.models import Site
from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit, Transpose
from modelcluster.fields import ParentalManyToManyField
from modelcluster.models import ClusterableModel
from pilkit.processors import MakeOpaque
from wagtail.fields import StreamField
from wagtail.images import get_image_model_string
from wagtail.models import (
    DraftStateMixin,
    LockableMixin,
    PreviewableMixin,
    RevisionMixin,
    WorkflowMixin,
)
from wagtail.snippets.blocks import SnippetChooserBlock

from apps.common.models import SEOModel, TimeStampedModel
from apps.common.validators import (
    ARTICLE_IMAGE_JPEG_QUALITY,
    ARTICLE_IMAGE_MAX_HEIGHT,
    ARTICLE_IMAGE_MAX_WIDTH,
    validate_uploaded_image,
)
from apps.news.blocks import ArticleStreamBlock
from apps.news.content_extraction import extract_content_from_body

logger = logging.getLogger(__name__)


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


class Article(PreviewableMixin, WorkflowMixin, DraftStateMixin, LockableMixin, RevisionMixin, ClusterableModel, TimeStampedModel, SEOModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Rascunho'
        PUBLISHED = 'published', 'Publicado'
        ARCHIVED = 'archived', 'Arquivado'

    title = models.CharField('Título', max_length=200)
    slug = models.SlugField('URL amigável', max_length=200, help_text='Gerado automaticamente a partir do título.')
    excerpt = models.TextField('Resumo', blank=True, help_text='Resumo curto do artigo. Aparece nas listagens e compartilhamentos.')
    content = models.TextField(
        'Conteúdo',
        blank=True,
        editable=False,
        help_text='Texto consolidado gerado automaticamente a partir do corpo (body) do artigo.',
    )
    body = StreamField(
        ArticleStreamBlock(),
        null=True,
        blank=True,
        verbose_name='Conteúdo (blocos)',
        use_json_field=True,
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
    featured_image_wagtail = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name='Imagem de capa (Wagtail)',
        help_text='Nova imagem de capa pelo sistema Wagtail. Use este campo em vez do campo acima para novos artigos — o antigo continua funcionando, mas não aparece mais no painel Wagtail.',
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True,
        related_name='articles', verbose_name='Categoria',
        help_text='Escolha a categoria principal do artigo.',
    )
    tags = ParentalManyToManyField(
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
        constraints = [
            models.UniqueConstraint(fields=['site', 'slug'], name='unique_article_slug_per_site'),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('news:article_detail', kwargs={'slug': self.slug})

    def get_preview_template(self, request, mode_name):
        """Template de preview do Wagtail.

        Reusa o template público existente — a renderização usa `article.body`
        (StreamField) como única fonte de conteúdo.
        """
        return 'news/article_detail.html'

    def get_preview_context(self, request, mode_name):
        """Contexto de preview espelhando `apps.news.views.article_detail`.

        `PreviewableMixin.get_preview_context()` só fornece `object`/`request` —
        como o template de preview é o mesmo da página pública, ele também
        precisa de `article`, `comments`, `related_articles` etc., ou a
        renderização falha com VariableDoesNotExist.
        """
        context = super().get_preview_context(request, mode_name)

        related_articles = Article.objects.none()
        comments = Comment.objects.none()
        comment_count = 0
        like_count = 0

        if self.pk:
            if self.category_id:
                related_articles = (
                    Article.objects.filter(status=Article.Status.PUBLISHED, category_id=self.category_id)
                    .exclude(pk=self.pk)
                    .select_related('category', 'author')
                    .order_by('-published_at')[:3]
                )
            comments = self.comments.filter(is_active=True).select_related('user').order_by('created_at')
            comment_count = comments.count()
            like_count = self.likes.count()

        context.update({
            'article': self,
            'related_articles': related_articles,
            'is_bookmarked': False,
            'is_liked': False,
            'comments': comments,
            'comment_count': comment_count,
            'like_count': like_count,
        })
        return context

    def _extract_content_from_body(self):
        """Extrai texto plano/HTML de `self.body` (StreamField) para `content`.

        A lógica em si vive em `apps/news/content_extraction.py` porque a data
        migration 0024 precisa reconstruir `content` com exatamente as mesmas
        regras, e migration não importa método de modelo vivo.
        """
        return extract_content_from_body(self.body)

    def save(self, *args, **kwargs):
        from django.utils import timezone

        from apps.common.sanitization import sanitize_content

        if self.body:
            self.content = self._extract_content_from_body()

        if self.content:
            self.content = sanitize_content(self.content)

        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def reading_time(self):
        """Estimate reading time in minutes (average 200 wpm)."""
        if self.body:
            from django.utils.html import strip_tags
            text = strip_tags(self._extract_content_from_body())
        else:
            text = self.content
        word_count = len(re.findall(r'\w+', text))
        return max(1, round(word_count / 200))

    @cached_property
    def cover_image_url(self):
        """URL única para a imagem de capa, priorizando o campo Wagtail com fallback
        para o campo legado. Nunca levanta exceção em template.

        `cached_property`, e não `property`: os templates de listagem checam
        `has_cover_image` e em seguida usam `cover_image_url`, e `get_rendition()`
        é uma consulta ao banco (mais o processamento da imagem na primeira vez).
        Como `property` isso rodava duas vezes por artigo em cada grid.
        """
        if self.featured_image_wagtail_id:
            try:
                return self.featured_image_wagtail.get_rendition('max-1600x1600').url
            except Exception:
                logger.warning('Falha ao gerar rendition para article #%s', self.pk, exc_info=True)
        if self.featured_image:
            return self.featured_image.url
        return ''

    @property
    def has_cover_image(self):
        return bool(self.cover_image_url)


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


class NewsHomeConfig(TimeStampedModel, SEOModel):
    site = models.OneToOneField(Site, on_delete=models.CASCADE, related_name='news_home_config')
    is_active = models.BooleanField('Ativo', default=True,
        help_text='Desligado: a home volta ao comportamento automático.')
    hero_override = models.ForeignKey(Article, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='Destaque manual do hero',
        help_text='Substitui o destaque automático. Deixe vazio para manter o comportamento atual.')
    secondary_highlights = StreamField(
        [('artigo', SnippetChooserBlock(Article, label='Artigo'))],
        blank=True, use_json_field=True, max_num=4, verbose_name='Destaques secundários',
        help_text='2 a 4 artigos publicados, na ordem desejada. Vazio: a seção não aparece.')

    objects = models.Manager()
    on_site = CurrentSiteManager()

    class Meta:
        verbose_name = 'Configuração da Home de Notícias'
        verbose_name_plural = 'Configurações da Home de Notícias'

    def __str__(self):
        return f'Home de notícias - {self.site.name}'
