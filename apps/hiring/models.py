import uuid
from pathlib import Path

from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import SEOModel, TimeStampedModel


def resume_upload_path(instance, filename):
    """Gera nome de arquivo UUID para currículos.

    Evita URLs adivinháveis (nomes derivados do candidato) que permitiriam
    baixar currículos diretamente de /media/ sem autenticação.
    """
    return f'hiring/resumes/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'


class Department(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='departments', verbose_name='Site')
    name = models.CharField('Nome', max_length=200)
    slug = models.SlugField('URL amigável', max_length=200)

    objects = models.Manager()
    on_site = CurrentSiteManager()

    class Meta:
        ordering = ['name']
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'
        constraints = [
            models.UniqueConstraint(fields=['site', 'slug'], name='unique_department_slug_per_site'),
        ]

    def __str__(self):
        return self.name


class JobPosting(TimeStampedModel, SEOModel):
    class EmploymentType(models.TextChoices):
        FULL_TIME = 'full_time', 'Tempo Integral'
        PART_TIME = 'part_time', 'Meio Período'
        CONTRACT = 'contract', 'Contrato'
        INTERNSHIP = 'internship', 'Estágio'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Rascunho'
        OPEN = 'open', 'Aberta'
        CLOSED = 'closed', 'Fechada'

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='job_postings', verbose_name='Site')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='jobs', verbose_name='Departamento')
    title = models.CharField('Título', max_length=200)
    slug = models.SlugField('URL amigável', max_length=200)
    description = models.TextField('Descrição')
    requirements = models.TextField('Requisitos')
    employment_type = models.CharField('Tipo de contratação', max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME)
    location = models.CharField('Local', max_length=200, blank=True)
    salary_range = models.CharField('Faixa salarial', max_length=200, blank=True)
    status = models.CharField('Status', max_length=20, choices=Status.choices, default=Status.DRAFT, help_text='Rascunho: não visível. Aberta: visível no site. Fechada: removida do site.')
    published_at = models.DateTimeField('Publicado em', null=True, blank=True)
    deadline = models.DateTimeField('Prazo final', null=True, blank=True, help_text='Data limite para receber candidaturas.')

    objects = models.Manager()
    on_site = CurrentSiteManager()

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'Vaga'
        verbose_name_plural = 'Vagas'
        constraints = [
            models.UniqueConstraint(fields=['site', 'slug'], name='unique_job_posting_slug_per_site'),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.department_id and self.site_id and self.department.site_id != self.site_id:
            raise ValidationError({'department': 'O departamento deve pertencer ao mesmo site da vaga.'})


class Application(TimeStampedModel):
    class Status(models.TextChoices):
        RECEIVED = 'received', 'Recebida'
        REVIEWING = 'reviewing', 'Em Análise'
        SHORTLISTED = 'shortlisted', 'Pré-selecionada'
        INTERVIEW = 'interview', 'Entrevista'
        REJECTED = 'rejected', 'Rejeitada'
        ACCEPTED = 'accepted', 'Aceita'

    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications', verbose_name='Vaga')
    first_name = models.CharField('Nome', max_length=100)
    last_name = models.CharField('Sobrenome', max_length=100)
    email = models.EmailField('E-mail')
    phone = models.CharField('Telefone', max_length=30)
    cover_letter = models.TextField('Carta de apresentação', blank=True)
    resume = models.FileField('Currículo', upload_to=resume_upload_path)
    status = models.CharField('Status', max_length=20, choices=Status.choices, default=Status.RECEIVED, help_text='Acompanhe o progresso desta candidatura.')
    notes = models.TextField('Notas internas', blank=True, help_text='Notas internas sobre o candidato. Não visíveis ao candidato.')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Candidatura'
        verbose_name_plural = 'Candidaturas'

    def __str__(self):
        return f'{self.first_name} {self.last_name} - {self.job.title}'
