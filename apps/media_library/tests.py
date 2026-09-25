from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.accounts.models import CustomUser
from apps.media_library.admin import _detect_file_type, _optimize_image_field
from apps.media_library.models import MediaFile


def _image_upload(name='foto.jpg', size=(3000, 2000), fmt='JPEG'):
    buf = BytesIO()
    Image.new('RGB', size, (120, 60, 30)).save(buf, format=fmt)
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type=f'image/{fmt.lower()}')


# ── Auto-detecção de tipo (substitui a escolha manual no admin) ───────────────

def test_detect_file_type_by_extension():
    assert _detect_file_type('capa.jpg') == MediaFile.FileType.IMAGE
    assert _detect_file_type('LOGO.PNG') == MediaFile.FileType.IMAGE
    assert _detect_file_type('edital.pdf') == MediaFile.FileType.DOCUMENT
    assert _detect_file_type('aula.mp4') == MediaFile.FileType.VIDEO
    assert _detect_file_type('jingle.mp3') == MediaFile.FileType.AUDIO
    assert _detect_file_type('pacote.zip') == MediaFile.FileType.OTHER
    assert _detect_file_type('') == MediaFile.FileType.OTHER


# ── Otimização de imagem (mesma higiene do avatar/artigo) ─────────────────────

def test_optimize_downsizes_large_jpeg():
    out = _optimize_image_field(_image_upload('grande.jpg', size=(3000, 2000)))

    assert out is not None  # imagem grande deve ser reescrita
    with Image.open(BytesIO(out.read())) as img:
        assert img.format == 'JPEG'
        assert img.width <= 1600 and img.height <= 1600


def test_optimize_preserves_png_format():
    out = _optimize_image_field(_image_upload('grande.png', size=(2400, 2400), fmt='PNG'))

    assert out is not None
    with Image.open(BytesIO(out.read())) as img:
        assert img.format == 'PNG'  # transparência preservada (não vira JPEG)
        assert img.width <= 1600 and img.height <= 1600


def test_optimize_skips_non_image_files():
    doc = SimpleUploadedFile('edital.pdf', b'%PDF-1.4 conteudo', content_type='application/pdf')
    assert _optimize_image_field(doc) is None


def test_optimize_skips_small_png_to_avoid_bloat():
    # PNG já pequeno: recomprimir só arriscaria inchar, então deixa intacto.
    assert _optimize_image_field(_image_upload('icone.png', size=(64, 64), fmt='PNG')) is None


# ── Lista branca de extensões (auditoria de segurança, XSS-01) ───────────────
# /media/ é servida na mesma origem dos painéis: HTML/SVG enviados ali rodavam
# script com a sessão de quem abrisse o link.

ACTIVE_CONTENT = [
    ('pagina.html', b'<script>alert(document.domain)</script>'),
    ('pagina.htm', b'<script>alert(1)</script>'),
    ('desenho.svg', b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'),
    ('dados.xml', b'<?xml version="1.0"?><x/>'),
    ('codigo.js', b'alert(1)'),
    ('pacote.zip', b'PK\x03\x04'),
]


@pytest.mark.django_db
@pytest.mark.parametrize('name,payload', ACTIVE_CONTENT)
def test_media_library_admin_refuses_active_content(client, make_panel_user, current_site, settings, tmp_path, name, payload):
    settings.MEDIA_ROOT = tmp_path
    client.force_login(make_panel_user('escola_up', role=CustomUser.Role.SCHOOL_ADMIN, is_staff=True))

    response = client.post(reverse('admin:media_library_mediafile_add'), {
        'title': 'x', 'file': SimpleUploadedFile(name, payload, content_type='text/html'), '_save': 'Salvar',
    })

    assert response.status_code == 200  # formulário volta com erro
    assert not MediaFile.objects.exists()


@pytest.mark.django_db
def test_media_library_admin_accepts_documents(client, make_panel_user, current_site, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    client.force_login(make_panel_user('escola_pdf', role=CustomUser.Role.SCHOOL_ADMIN, is_staff=True))

    response = client.post(reverse('admin:media_library_mediafile_add'), {
        'title': 'Edital', 'file': SimpleUploadedFile('edital.pdf', b'%PDF-1.4 x', content_type='application/pdf'), '_save': 'Salvar',
    })

    assert response.status_code == 302
    assert MediaFile.objects.get().file_type == MediaFile.FileType.DOCUMENT


@pytest.mark.django_db
@pytest.mark.parametrize('name,payload', ACTIVE_CONTENT)
def test_wagtail_documents_refuse_active_content(settings, tmp_path, name, payload):
    from wagtail.documents import get_document_model

    settings.MEDIA_ROOT = tmp_path
    document = get_document_model()(title='x', file=SimpleUploadedFile(name, payload))

    with pytest.raises(ValidationError):
        document.full_clean(exclude=['collection'])


@pytest.mark.django_db
def test_wagtail_documents_accept_pdf(settings, tmp_path):
    from wagtail.documents import get_document_model

    settings.MEDIA_ROOT = tmp_path
    document = get_document_model()(title='x', file=SimpleUploadedFile('edital.pdf', b'%PDF-1.4 x'))
    document.full_clean(exclude=['collection'])
