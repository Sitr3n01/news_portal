"""Fábricas compartilhadas pelos testes do app news: site, notícia e upload de imagem."""

from io import BytesIO

from django.contrib.sites.models import Site
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.news.models import Article, Category

# ── Helpers compartilhados ───────────────────────────────────────────────────

def make_site(pk=1, domain='testserver', name='Test Site'):
    site, _ = Site.objects.update_or_create(
        id=pk,
        defaults={'domain': domain, 'name': name},
    )
    return site


def make_article(site, slug='artigo', status=Article.Status.PUBLISHED):
    return Article.objects.create(
        title=f'Artigo {slug}',
        slug=slug,
        excerpt='Resumo do artigo',
        content='Conteúdo do artigo para newsletter.',
        site=site,
        status=status,
    )


def make_article_full(site, slug='artigo', status=Article.Status.PUBLISHED, category=None, author=None):
    """Cria um artigo com category e author populados (necessário para save_revision/full_clean)."""
    art = make_article(site, slug=slug, status=status)
    if category is None:
        category, _ = Category.objects.get_or_create(
            name='Geral', slug='geral',
        )
    if author is None:
        from django.contrib.auth import get_user_model
        user_cls = get_user_model()
        author = user_cls.objects.create_user(
            username=f'author-{slug}',
            email=f'author-{slug}@test.com',
            password='x',
        )
    art.category = category
    art.author = author
    art.save()
    return art


def make_image_upload(name='capa.png', size=(2400, 1200), fmt='PNG'):
    """Gera um upload de imagem real (Pillow) para os testes de capa."""
    buf = BytesIO()
    Image.new('RGB', size, (30, 90, 180)).save(buf, format=fmt)
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type=f'image/{fmt.lower()}')
