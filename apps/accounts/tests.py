import os
from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.common.validators import MAX_UPLOAD_BYTES, validate_uploaded_image


def make_image_upload(name='foto.png', size=(800, 600), fmt='PNG'):
    """Gera um upload de imagem real (Pillow) para os testes."""
    buf = BytesIO()
    Image.new('RGB', size, (20, 110, 200)).save(buf, format=fmt)
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type=f'image/{fmt.lower()}')


# ── Validador reutilizável ───────────────────────────────────────────────────

def test_validator_accepts_valid_image():
    validate_uploaded_image(make_image_upload('ok.png'))  # não levanta


def test_validator_rejects_bad_extension():
    with pytest.raises(ValidationError):
        validate_uploaded_image(SimpleUploadedFile('doc.txt', b'qualquer', content_type='text/plain'))


def test_validator_rejects_spoofed_content():
    # Extensão diz imagem, conteúdo não é — deve cair na checagem do Pillow.
    with pytest.raises(ValidationError):
        validate_uploaded_image(SimpleUploadedFile('fake.jpg', b'isto nao e imagem', content_type='image/jpeg'))


def test_validator_rejects_oversize():
    big = SimpleUploadedFile('big.jpg', b'\0' * (MAX_UPLOAD_BYTES + 1), content_type='image/jpeg')
    with pytest.raises(ValidationError):
        validate_uploaded_image(big)


# ── View pública update_profile ──────────────────────────────────────────────

@pytest.fixture
def reader(db, tmp_path, settings, django_user_model, client):
    settings.MEDIA_ROOT = str(tmp_path)
    user = django_user_model.objects.create_user(
        username='leitora', password='x', email='leitora@example.com',
    )
    client.force_login(user)
    return user


@pytest.mark.django_db
def test_update_profile_stores_optimized_square_jpeg(client, reader):
    response = client.post(reverse('accounts:update_profile'), {'avatar': make_image_upload('foto.png', size=(800, 600))})

    assert response.status_code == 302
    assert '/news/account/' in response.url
    reader.refresh_from_db()
    assert reader.avatar
    assert reader.avatar.name.endswith('.jpg')
    with Image.open(reader.avatar.path) as img:
        assert img.format == 'JPEG'
        assert img.size == (256, 256)
    assert reader.avatar.size < 200_000  # otimizado


@pytest.mark.django_db
def test_update_profile_deletes_previous_file_on_replace(client, reader):
    client.post(reverse('accounts:update_profile'), {'avatar': make_image_upload('a.png')})
    reader.refresh_from_db()
    first_path = reader.avatar.path
    assert os.path.exists(first_path)

    client.post(reverse('accounts:update_profile'), {'avatar': make_image_upload('b.png')})
    reader.refresh_from_db()

    assert reader.avatar.path != first_path
    assert not os.path.exists(first_path)  # sem órfão no disco


@pytest.mark.django_db
def test_update_profile_remove_clears_avatar_and_file(client, reader):
    client.post(reverse('accounts:update_profile'), {'avatar': make_image_upload('a.png')})
    reader.refresh_from_db()
    path = reader.avatar.path

    response = client.post(reverse('accounts:update_profile'), {'action': 'remove'})

    assert response.status_code == 302
    reader.refresh_from_db()
    assert not reader.avatar
    assert not os.path.exists(path)


@pytest.mark.django_db
def test_update_profile_rejects_non_image(client, reader):
    bad = SimpleUploadedFile('fake.jpg', b'isto nao e imagem', content_type='image/jpeg')

    response = client.post(reverse('accounts:update_profile'), {'avatar': bad})

    assert response.status_code == 302
    reader.refresh_from_db()
    assert not reader.avatar


@pytest.mark.django_db
def test_update_profile_requires_login(client):
    response = client.post(reverse('accounts:update_profile'), {'avatar': make_image_upload()})

    assert response.status_code == 302
    assert '/accounts/login' in response.url


@pytest.mark.django_db
def test_dashboard_settings_tab_renders_photo_card(client, reader):
    # Garante que o card novo (Alpine + partial de avatar) compila e renderiza.
    response = client.get(reverse('news:user_dashboard'), {'tab': 'settings'})

    assert response.status_code == 200
    content = response.content.decode()
    assert 'Foto de Perfil' in content
    assert 'enctype="multipart/form-data"' in content
