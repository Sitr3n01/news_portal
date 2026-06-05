from django.contrib.auth.models import AbstractUser
from django.db import models


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
    avatar = models.ImageField('Foto de perfil', upload_to='avatars/', blank=True)
    bio = models.TextField('Biografia', blank=True, help_text='Breve descrição sobre o usuário.')

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        app_label = 'accounts'

    def __str__(self):
        return self.get_full_name() or self.username

