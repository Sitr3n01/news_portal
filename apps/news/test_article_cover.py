"""Capa da notícia: upload otimizado, ponte para a imagem do Wagtail e URLs de capa e de card."""

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from PIL import Image

from apps.common.validators import ARTICLE_IMAGE_MAX_WIDTH
from apps.news.models import Article
from apps.news.testing import make_article, make_image_upload, make_site

# ── Capa de artigo: mesma higiene do avatar (ProcessedImageField) ────────────

@pytest.mark.django_db
def test_article_featured_image_stored_as_optimized_jpeg(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site()

    article = Article.objects.create(
        title='Artigo com capa',
        slug='com-capa',
        content='Conteúdo.',
        site=site,
        featured_image=make_image_upload('capa.png', size=(2400, 1200)),
    )

    assert article.featured_image.name.endswith('.jpg')
    with Image.open(article.featured_image.path) as img:
        assert img.format == 'JPEG'
        # 2400×1200 (2:1) cabe em 1600×1600 → 1600×800, sem distorcer nem cortar.
        assert img.width == ARTICLE_IMAGE_MAX_WIDTH
        assert img.height == 800


@pytest.mark.django_db
def test_article_featured_image_rejects_non_image(settings, tmp_path):
    from django.core.exceptions import ValidationError

    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site()
    article = Article(
        title='Artigo ruim',
        slug='artigo-ruim',
        content='Conteúdo.',
        site=site,
        featured_image=SimpleUploadedFile('fake.jpg', b'isto nao e imagem', content_type='image/jpeg'),
    )

    # O validador centralizado está plugado no campo: full_clean deve rejeitar.
    with pytest.raises(ValidationError):
        article.full_clean()


# ── Fase 9: featured_image_wagtail (ponte de capa) ────────────────────────────


@pytest.mark.django_db
def test_featured_image_wagtail_field_exists():
    """O campo featured_image_wagtail existe no model Article e é nullable."""
    site = make_site()
    article = make_article(site, slug='wagtail-field-test')
    # Campo deve existir como atributo e ser None por padrão
    assert hasattr(article, 'featured_image_wagtail')
    assert article.featured_image_wagtail is None
    assert article.featured_image_wagtail_id is None


@pytest.mark.django_db
def test_featured_image_wagtail_fk_to_image_model(settings, tmp_path):
    """O campo aceita FK para o modelo Image do Wagtail."""
    settings.MEDIA_ROOT = str(tmp_path)
    from wagtail.images import get_image_model
    image_model = get_image_model()

    site = make_site()
    article = make_article(site, slug='fk-test')

    from io import BytesIO

    from django.core.files.base import ContentFile
    from PIL import Image as PILImage

    buf = BytesIO()
    PILImage.new('RGB', (100, 100), (255, 0, 0)).save(buf, format='PNG')
    buf.seek(0)
    content = buf.read()

    wagtail_image = image_model.objects.create(
        title='Test Image',
        file=ContentFile(content, name='test.png'),
        width=100,
        height=100,
        file_size=len(content),
    )

    article.featured_image_wagtail = wagtail_image
    article.save(update_fields=['featured_image_wagtail'])

    article.refresh_from_db()
    assert article.featured_image_wagtail_id == wagtail_image.pk
    assert article.featured_image_wagtail == wagtail_image


@pytest.mark.django_db
def test_featured_image_wagtail_no_reverse_accessor_clash():
    """related_name='+' evita choque de reverse accessor."""
    field = Article._meta.get_field('featured_image_wagtail')
    assert field.remote_field.related_name == '+'


# ── Bridge command tests ──────────────────────────────────────────────────────


@pytest.mark.django_db
def test_migrate_featured_images_dry_run_no_changes(settings, tmp_path):
    """Dry-run não persiste nada no banco."""
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site()

    article = Article.objects.create(
        title='Artigo com capa para dry-run',
        slug='dry-run-cap',
        content='Conteúdo.',
        site=site,
        featured_image=make_image_upload('capa.png', size=(800, 600)),
    )

    from wagtail.images import get_image_model
    image_model = get_image_model()
    image_count_before = image_model.objects.count()

    assert article.featured_image_wagtail_id is None

    from io import StringIO
    out = StringIO()
    call_command(
        'migrate_featured_images',
        '--article-id', str(article.pk),
        stdout=out, stderr=StringIO(),
    )

    # Após dry-run, nada deve ter sido gravado
    article.refresh_from_db()
    assert article.featured_image_wagtail_id is None
    assert image_model.objects.count() == image_count_before

    output = out.getvalue()
    assert 'Snap' in output or 'snaps' in output.lower() or 'PULADO' in output or 'Image' in output


@pytest.mark.django_db
def test_migrate_featured_images_apply_creates_image(settings, tmp_path):
    """--apply cria Image e popula featured_image_wagtail."""
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site()

    article = Article.objects.create(
        title='Artigo com capa',
        slug='capa-apply',
        content='Conteúdo.',
        site=site,
        featured_image=make_image_upload('capa.png', size=(800, 600)),
    )

    from wagtail.images import get_image_model
    image_model = get_image_model()
    image_count_before = image_model.objects.count()

    from io import StringIO
    out = StringIO()
    call_command(
        'migrate_featured_images',
        '--apply',
        '--article-id', str(article.pk),
        stdout=out, stderr=StringIO(),
    )

    article.refresh_from_db()
    assert article.featured_image_wagtail_id is not None
    assert image_model.objects.count() == image_count_before + 1

    wagtail_image = article.featured_image_wagtail
    assert wagtail_image.title == 'Artigo com capa'
    assert wagtail_image.width <= 800  # imagekit pode ter redimensionado
    assert wagtail_image.height <= 600
    # O arquivo da Image do Wagtail herda o nome do original (já convertido a JPEG pelo imagekit)
    assert wagtail_image.file.name.endswith(('.png', '.jpg', '.jpeg'))

    output = out.getvalue()
    assert 'RESUMO FINAL' in output or '1' in output


@pytest.mark.django_db
def test_migrate_featured_images_idempotent(settings, tmp_path):
    """Rodar o comando duas vezes com --apply não duplica imagens."""
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site()

    article = Article.objects.create(
        title='Artigo idempotent',
        slug='idempotent',
        content='Conteúdo.',
        site=site,
        featured_image=make_image_upload('capa.png', size=(200, 200)),
    )

    from wagtail.images import get_image_model
    image_model = get_image_model()

    from io import StringIO

    # Primeira execução
    call_command(
        'migrate_featured_images',
        '--apply',
        '--article-id', str(article.pk),
        stdout=StringIO(), stderr=StringIO(),
    )

    image_count_after_first = image_model.objects.count()
    article.refresh_from_db()
    first_image_pk = article.featured_image_wagtail_id

    # Segunda execução — deve pular
    out2 = StringIO()
    call_command(
        'migrate_featured_images',
        '--apply',
        '--article-id', str(article.pk),
        stdout=out2, stderr=StringIO(),
    )

    article.refresh_from_db()
    assert image_model.objects.count() == image_count_after_first
    assert article.featured_image_wagtail_id == first_image_pk

    output2 = out2.getvalue()
    assert 'PULADO' in output2 or 'skipp' in output2.lower() or 'ja preenchido' in output2.lower()


@pytest.mark.django_db
def test_migrate_featured_images_skips_without_featured_image(settings, tmp_path):
    """Artigos sem featured_image são ignorados."""
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site()

    article = make_article(site, slug='sem-capa')
    article.featured_image_wagtail_id = None  # explícito
    article.save()

    from wagtail.images import get_image_model
    image_model = get_image_model()
    image_count_before = image_model.objects.count()

    from io import StringIO
    out = StringIO()
    call_command(
        'migrate_featured_images',
        '--apply',
        stdout=out, stderr=StringIO(),
    )

    article.refresh_from_db()
    assert article.featured_image_wagtail_id is None
    assert image_model.objects.count() == image_count_before


@pytest.mark.django_db
def test_migrate_featured_images_does_not_touch_old_field(settings, tmp_path):
    """O campo featured_image original permanece intacto após a migração."""
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site()

    article = Article.objects.create(
        title='Campo antigo preservado',
        slug='old-field',
        content='Conteúdo.',
        site=site,
        featured_image=make_image_upload('capa.png', size=(400, 300)),
    )

    old_image_name = article.featured_image.name

    from io import StringIO
    call_command(
        'migrate_featured_images',
        '--apply',
        '--article-id', str(article.pk),
        stdout=StringIO(), stderr=StringIO(),
    )

    article.refresh_from_db()
    # featured_image original deve continuar igual
    assert article.featured_image.name == old_image_name
    assert article.featured_image  # não vazio
    # E featured_image_wagtail deve ter sido populado
    assert article.featured_image_wagtail_id is not None


# ── Bug C: cover_image_url / has_cover_image ────────────────────────────────


@pytest.mark.django_db
def test_cover_image_url_empty_when_no_image():
    """cover_image_url retorna '' quando nenhum campo de imagem está preenchido."""
    site = make_site()
    article = make_article(site, slug='no-image')
    article.featured_image_wagtail = None
    article.featured_image = None
    article.save()

    assert article.cover_image_url == ''
    assert article.has_cover_image is False


@pytest.mark.django_db
def test_cover_image_url_legacy_only(settings, tmp_path):
    """cover_image_url retorna URL legada quando só featured_image está definido."""
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site()
    article = Article.objects.create(
        title='Legacy Only',
        slug='legacy-only',
        content='.',
        site=site,
        featured_image=make_image_upload('legacy.png', size=(800, 600)),
    )

    url = article.cover_image_url
    assert url == article.featured_image.url
    assert article.has_cover_image is True


@pytest.mark.django_db
def test_cover_image_url_wagtail_only(settings, tmp_path):
    """cover_image_url retorna rendition URL quando só featured_image_wagtail está definido."""
    settings.MEDIA_ROOT = str(tmp_path)
    from io import BytesIO

    from django.core.files.base import ContentFile
    from PIL import Image as PILImage
    from wagtail.images import get_image_model

    site = make_site()
    article = make_article(site, slug='wagtail-only')

    image_model = get_image_model()
    buf = BytesIO()
    PILImage.new('RGB', (100, 100), (30, 90, 180)).save(buf, format='PNG')
    buf.seek(0)
    img = image_model.objects.create(
        title='Wagtail Image',
        file=ContentFile(buf.read(), name='wagtail.png'),
        width=100,
        height=100,
        file_size=buf.tell(),
    )

    article.featured_image_wagtail = img
    article.save(update_fields=['featured_image_wagtail'])

    url = article.cover_image_url
    assert url != ''
    assert article.has_cover_image is True


@pytest.mark.django_db
def test_cover_image_url_wagtail_wins_when_both(settings, tmp_path):
    """Wagtail field tem prioridade quando ambos os campos estão definidos."""
    settings.MEDIA_ROOT = str(tmp_path)
    from io import BytesIO

    from django.core.files.base import ContentFile
    from wagtail.images import get_image_model

    site = make_site()
    article = Article.objects.create(
        title='Both Fields',
        slug='both-fields',
        content='.',
        site=site,
        featured_image=make_image_upload('legacy.png', size=(400, 300)),
    )

    image_model = get_image_model()
    from PIL import Image as PILImage
    buf = BytesIO()
    PILImage.new('RGB', (100, 100), (255, 0, 0)).save(buf, format='PNG')
    buf.seek(0)
    img = image_model.objects.create(
        title='Wagtail Override',
        file=ContentFile(buf.read(), name='wagtail.png'),
        width=100,
        height=100,
        file_size=buf.tell(),
    )

    article.featured_image_wagtail = img
    article.save(update_fields=['featured_image_wagtail'])

    url = article.cover_image_url
    legacy_url = article.featured_image.url
    assert url != legacy_url, f'Wagtail URL {url} não deve ser igual à legacy URL {legacy_url}'
    assert article.has_cover_image is True


# ── card_image_url: rendition de listagem separada da de herói ──────────────


@pytest.mark.django_db
def test_card_image_url_usa_rendition_menor_que_a_capa(settings, tmp_path):
    """Card e herói geram renditions diferentes a partir da mesma imagem.

    `cover_image_url` continua em `max-1600x1600` — certo para o herói e para as
    metatags OG/Twitter. Os cards passam a `fill-600x400`: numa grade de 12, a
    rendition de 1600 px fazia o Pillow decodificar dentro do worker do Gunicorn e
    o navegador baixar muito mais bytes do que renderiza.
    """
    settings.MEDIA_ROOT = str(tmp_path)
    from io import BytesIO

    from django.core.files.base import ContentFile
    from PIL import Image as PILImage
    from wagtail.images import get_image_model

    site = make_site()
    article = make_article(site, slug='card-rendition')

    image_model = get_image_model()
    buf = BytesIO()
    PILImage.new('RGB', (1600, 1200), (30, 90, 180)).save(buf, format='PNG')
    buf.seek(0)
    img = image_model.objects.create(
        title='Capa grande',
        file=ContentFile(buf.read(), name='capa-grande.png'),
        width=1600,
        height=1200,
        file_size=buf.tell(),
    )
    article.featured_image_wagtail = img
    article.save(update_fields=['featured_image_wagtail'])

    assert article.has_card_image is True
    assert article.card_image_url != ''
    assert article.card_image_url != article.cover_image_url

    specs = set(img.renditions.values_list('filter_spec', flat=True))
    assert 'fill-600x400' in specs
    assert 'max-1600x1600' in specs


@pytest.mark.django_db
def test_card_image_url_cai_para_o_campo_legado(settings, tmp_path):
    """Sem imagem Wagtail, o card usa o featured_image legado — igual à capa."""
    settings.MEDIA_ROOT = str(tmp_path)

    site = make_site()
    article = make_article(site, slug='card-legado')
    buf = BytesIO()
    Image.new('RGB', (60, 60), (10, 10, 10)).save(buf, format='PNG')
    buf.seek(0)
    article.featured_image.save('legado.png', SimpleUploadedFile('legado.png', buf.getvalue(), 'image/png'), save=True)

    assert article.has_card_image is True
    assert article.card_image_url == article.featured_image.url


@pytest.mark.django_db
def test_card_image_url_vazio_sem_imagem():
    """Sem nenhuma imagem, card_image_url é '' e has_card_image é False."""
    site = make_site()
    article = make_article(site, slug='card-sem-imagem')

    assert article.card_image_url == ''
    assert article.has_card_image is False
