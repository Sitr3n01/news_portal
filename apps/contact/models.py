from django.contrib.sites.models import Site
from django.db import models

from apps.common.models import TimeStampedModel


class ContactInquiry(TimeStampedModel):
    class Status(models.TextChoices):
        NEW = 'new', 'Nova'
        READ = 'read', 'Lida'
        REPLIED = 'replied', 'Respondida'
        ARCHIVED = 'archived', 'Arquivada'

    class Subject(models.TextChoices):
        GENERAL = 'general', 'Geral'
        ADMISSIONS = 'admissions', 'Admissões'
        SUPPORT = 'support', 'Suporte'
        OTHER = 'other', 'Outro'

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='inquiries')
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    subject = models.CharField(max_length=50, choices=Subject.choices, default=Subject.GENERAL)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, help_text='Marque como Lida, Respondida ou Arquivada conforme o atendimento.')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Mensagem de Contato'
        verbose_name_plural = 'Mensagens de Contato'

    def __str__(self):
        return f'{self.name} - {self.subject}'
