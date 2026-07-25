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
        # READER é o default e NÃO tem grupo em admin_roles.ROLE_TO_GROUP:
        # quem se cadastra sozinho no portal não pode nascer com cargo de
        # redação. Antes o default era NEWS_EDITOR, cujo grupo carrega
        # `wagtailadmin.access_admin` — inerte só porque a sincronização de
        # grupo não roda no cadastro público, mas pronto para virar escalada de
        # privilégio no dia em que alguém a automatizasse.
        READER = 'reader', 'Leitor'
        SUPER_ADMIN = 'super_admin', 'Super Administrador'
        SCHOOL_ADMIN = 'school_admin', 'Administrador Komuniki'
        NEWS_EDITOR = 'news_editor', 'Editor de Notícias'
        REPORTER = 'reporter', 'Repórter'
        HIRING_MANAGER = 'hiring_manager', 'Contratações (guardado)'

    email = models.EmailField(
        'E-mail', unique=True, blank=True,
        help_text='Endereço de e-mail único. Usado para recuperação de senha.',
    )
    role = models.CharField(
        'Cargo', max_length=20,
        choices=Role.choices, default=Role.READER,
        help_text='Define as permissões e acesso do usuário no sistema. '
                  '"Leitor" é apenas o portal público, sem acesso administrativo.',
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

