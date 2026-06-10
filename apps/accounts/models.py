import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill, Transpose
from pilkit.processors import MakeOpaque

from apps.common.validators import (
    AVATAR_JPEG_QUALITY,
    AVATAR_SIZE,
    validate_uploaded_image,
)


def avatar_upload_path(instance, filename):
    """Caminho único por upload (cache-bust natural no nginx), namespeado por usuário."""
    return f'avatars/{instance.pk or "tmp"}/{uuid.uuid4().hex}.jpg'


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Administrador'
        SCHOOL_ADMIN = 'school_admin', 'Administrador Komuniki'
        NEWS_EDITOR = 'news_editor', 'Editor de Notícias'
        HIRING_MANAGER = 'hiring_manager', 'Contratações (guardado)'

    email = models.EmailField(
        'E-mail', unique=True, blank=True,
        help_text='Endereço de e-mail único. Usado para recuperação de senha.',
    )
    role = models.CharField(
        'Cargo', max_length=20,
        choices=Role.choices, default=Role.NEWS_EDITOR,
        help_text='Define as permissões e acesso do usuário no sistema.',
    )
    avatar = ProcessedImageField(
        verbose_name='Foto de perfil',
        upload_to=avatar_upload_path,
        blank=True,
        processors=[Transpose(), ResizeToFill(AVATAR_SIZE, AVATAR_SIZE), MakeOpaque()],
        format='JPEG',
        options={'quality': AVATAR_JPEG_QUALITY, 'optimize': True, 'progressive': True},
        validators=[validate_uploaded_image],
        help_text='Imagem quadrada recomendada. É convertida e otimizada automaticamente.',
    )
    bio = models.TextField('Biografia', blank=True, help_text='Breve descrição sobre o usuário.')

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        app_label = 'accounts'

    def __str__(self):
        return self.get_full_name() or self.username

