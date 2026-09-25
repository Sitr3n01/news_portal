from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

from apps.common.models import TimeStampedModel
from apps.common.validators import ALLOWED_IMAGE_EXTENSIONS

# Extensões aceitas, por tipo — fonte única: o admin detecta o tipo daqui.
#
# Lista branca, e não "qualquer arquivo": /media/ é servida pelo nginx na MESMA
# origem do /admin/ e do /cms/. Um .html, .svg, .xml ou .js enviado aqui abria
# como página e rodava script com a sessão de quem clicasse no link. SVG ficou
# de fora por isso (é XML com <script>); GIF e BMP não executam nada.
EXTRA_IMAGE_EXTENSIONS = {'.gif', '.bmp'}
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.odt', '.txt', '.rtf', '.xls', '.xlsx', '.csv', '.ppt', '.pptx'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.webm', '.mkv'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'}
ALLOWED_EXTENSIONS = sorted(
    ext.lstrip('.')
    for ext in ALLOWED_IMAGE_EXTENSIONS | EXTRA_IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS
)


class MediaFolder(models.Model):
    name = models.CharField('Nome', max_length=200)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Pasta superior',
        help_text='Use apenas quando esta pasta deve ficar dentro de outra.',
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Pasta de Mídia'
        verbose_name_plural = 'Pastas de Mídia'

    def __str__(self):
        return self.name


class MediaFile(TimeStampedModel):
    class FileType(models.TextChoices):
        IMAGE = 'image', 'Imagem'
        DOCUMENT = 'document', 'Documento'
        VIDEO = 'video', 'Vídeo'
        AUDIO = 'audio', 'Áudio'
        OTHER = 'other', 'Outro'

    title = models.CharField('Título', max_length=255)
    file = models.FileField(
        'Arquivo', upload_to='media_library/files/',
        validators=[FileExtensionValidator(ALLOWED_EXTENSIONS)],
        help_text='Imagens (JPG, PNG, WebP, GIF, BMP), documentos (PDF, Office, texto), vídeo ou áudio.',
    )
    file_type = models.CharField('Tipo de arquivo', max_length=20, choices=FileType.choices, default=FileType.OTHER)
    alt_text = models.CharField(
        'Texto alternativo',
        max_length=255,
        blank=True,
        help_text='Descreva imagens para acessibilidade. Ex.: alunos em laboratório de ciências.',
    )
    folder = models.ForeignKey(
        MediaFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='files',
        verbose_name='Pasta',
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Enviado por',
    )
    file_size = models.PositiveIntegerField('Tamanho do arquivo', help_text='Tamanho em bytes.', default=0)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Arquivo de Mídia'
        verbose_name_plural = 'Arquivos de Mídia'

    def __str__(self):
        return self.title
