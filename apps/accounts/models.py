import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
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

    # "Não confirmado" é ESTADO DE CADASTRO, não penalidade — por isso não
    # reaproveita `is_active`. `is_active` alimenta can_access_admin (panels.py)
    # e o django-axes (que recusa autenticação de conta inativa mesmo com senha
    # certa), e é o campo que o admin usa para desativar uma conta por abuso.
    # Se "ainda não confirmou o e-mail" desligasse is_active, todo cadastro
    # novo nasceria indistinguível de uma conta banida — e não haveria como,
    # no dia em que alguém reativasse contas em massa, separar quem só não
    # terminou o cadastro de quem foi banido de propósito.
    email_verified = models.BooleanField(
        'E-mail confirmado', default=False,
        help_text='Marcado automaticamente quando o usuário confirma o endereço com o código enviado por e-mail.',
    )
    email_verified_at = models.DateTimeField('Confirmado em', null=True, blank=True)

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


class VerificationCode(models.Model):
    """Código numérico de uso único para confirmar e-mail ou autorizar troca de senha.

    Este modelo é só o registro (estado + propriedades de leitura). Emissão,
    validação, rate limit e hashing vivem em apps.accounts.verification — uma
    camada só, compartilhada pelos dois fluxos, para não duplicar a mesma
    decisão de segurança em dois lugares que um dia divergiriam.
    """

    class Purpose(models.TextChoices):
        EMAIL_VERIFICATION = 'email_verification', 'Confirmação de e-mail'
        PASSWORD_RESET = 'password_reset', 'Recuperação de senha'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='verification_codes',
    )
    # Normalizado em minúsculas e CONGELADO no momento da emissão (apps.accounts.
    # verification.issue_code copia de user.email uma vez só): se a conta trocar
    # de e-mail entre a emissão e a validação, o código antigo não pode valer
    # para o endereço novo — ele foi enviado para uma caixa de entrada que já
    # não é mais a da conta.
    email = models.EmailField()
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    # Nunca o código em texto puro — só o hash. Ver apps.accounts.verification
    # para o porquê de HMAC em vez de um KDF lento aqui.
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Código de verificação'
        verbose_name_plural = 'Códigos de verificação'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'purpose', '-created_at'])]

    def __str__(self):
        # NUNCA hash nem código aqui: este texto pode acabar numa lista do
        # admin ou num repr() de shell. Propósito + e-mail + data já bastam
        # para localizar a linha sem expor nada que sirva pra autenticar.
        return f'{self.get_purpose_display()} para {self.email} em {self.created_at:%d/%m/%Y %H:%M}'

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_usable(self):
        """Não usado, não expirado, e ainda dentro do teto de tentativas.

        Lê settings.VERIFICATION_CODE_MAX_ATTEMPTS direto — e não importa a
        constante MAX_ATTEMPTS de apps.accounts.verification — porque aquele
        módulo importa VerificationCode deste aqui; importar de volta fecharia
        um ciclo. Duplicar a leitura da mesma setting nos dois lugares é mais
        barato do que quebrar o ciclo com import tardio.
        """
        return not self.is_used and not self.is_expired and self.attempts < settings.VERIFICATION_CODE_MAX_ATTEMPTS


class GoogleIdentity(models.Model):
    """Vínculo entre uma conta local e uma identidade Google (login social, Fase 2).

    A chave é sempre `google_sub` — NUNCA o e-mail. Um endereço de Google
    Workspace pode ser desativado pelo administrador do domínio e reatribuído
    a outra pessoa meses depois; se a busca de identidade fosse por e-mail, o
    novo dono do endereço herdaria por acidente a conta local de quem usava
    aquele e-mail antes — um sequestro de conta silencioso, sem senha
    quebrada nem token roubado. `sub` é o identificador imutável que o Google
    nunca recicla para outra pessoa.

    `OneToOneField` (em `user`) + `unique=True` (em `google_sub`) impedem, por
    construção — não por checagem em view, que alguém pode esquecer de
    chamar —, tanto uma segunda identidade Google na mesma conta local quanto
    a mesma identidade Google vinculada a duas contas locais.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='google_identity',
    )
    google_sub = models.CharField(max_length=255, unique=True, db_index=True)
    # E-mail do Google no momento do vínculo: só para auditoria/exibição no
    # admin. Nunca é usado para localizar a identidade (ver docstring acima).
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Identidade Google'
        verbose_name_plural = 'Identidades Google'

    def __str__(self):
        return f'{self.email} (Google)'

