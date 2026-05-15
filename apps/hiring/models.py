from django.db import models

from apps.common.models import SEOModel, TimeStampedModel


class Department(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'

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

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    requirements = models.TextField()
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME)
    location = models.CharField(max_length=200, blank=True)
    salary_range = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, help_text='Rascunho: não visível. Aberta: visível no site. Fechada: removida do site.')
    published_at = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True, help_text='Data limite para receber candidaturas.')

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'Vaga'
        verbose_name_plural = 'Vagas'

    def __str__(self):
        return self.title


class Application(TimeStampedModel):
    class Status(models.TextChoices):
        RECEIVED = 'received', 'Recebida'
        REVIEWING = 'reviewing', 'Em Análise'
        SHORTLISTED = 'shortlisted', 'Pré-selecionada'
        INTERVIEW = 'interview', 'Entrevista'
        REJECTED = 'rejected', 'Rejeitada'
        ACCEPTED = 'accepted', 'Aceita'

    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    cover_letter = models.TextField(blank=True)
    resume = models.FileField(upload_to='hiring/resumes/')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED, help_text='Acompanhe o progresso desta candidatura.')
    notes = models.TextField(blank=True, help_text='Notas internas sobre o candidato. Não visíveis ao candidato.')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Candidatura'
        verbose_name_plural = 'Candidaturas'

    def __str__(self):
        return f'{self.first_name} {self.last_name} - {self.job.title}'
