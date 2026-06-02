import re

from django.conf import settings
from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.sites.models import Site
from django.db import models
from django.urls import reverse

from apps.common.models import SEOModel, TimeStampedModel


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
    content = models.TextField('Conteúdo')
    featured_image = models.ImageField('Imagem de capa', upload_to='news/articles/', blank=True, help_text='Imagem principal que aparece no topo do artigo.')
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

    @property
    def reading_time(self):
        """Estimate reading time in minutes (average 200 wpm)."""
        word_count = len(re.findall(r'\w+', self.content))
        return max(1, round(word_count / 200))


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
