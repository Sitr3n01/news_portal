from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

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
