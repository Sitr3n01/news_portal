from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class MediaFolder(models.Model):
    name = models.CharField(max_length=200)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    class Meta:
        ordering = ['name']
        verbose_name = 'Media Folder'
        verbose_name_plural = 'Media Folders'

    def __str__(self):
        return self.name


class MediaFile(TimeStampedModel):
    class FileType(models.TextChoices):
        IMAGE = 'image', 'Image'
        DOCUMENT = 'document', 'Document'
        VIDEO = 'video', 'Video'
        AUDIO = 'audio', 'Audio'
        OTHER = 'other', 'Other'

    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='media_library/files/')
    file_type = models.CharField(max_length=20, choices=FileType.choices, default=FileType.OTHER)
    alt_text = models.CharField(max_length=255, blank=True)
    folder = models.ForeignKey(MediaFolder, on_delete=models.SET_NULL, null=True, blank=True, related_name='files')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    file_size = models.PositiveIntegerField(help_text="Size in bytes", default=0)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Media File'
        verbose_name_plural = 'Media Files'

    def __str__(self):
        return self.title
