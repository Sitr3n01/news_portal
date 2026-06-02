from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import Application, Department, JobPosting


@admin.register(Department)
class DepartmentAdmin(ModelAdmin):
    list_display = ['name', 'site', 'slug']
    list_filter = ['site']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = [
        ('Departamento', {
            'fields': ('site', 'name', 'slug'),
        }),
    ]


@admin.register(JobPosting)
class JobPostingAdmin(ModelAdmin):
    list_display = ['title', 'site', 'department', 'employment_type', 'status', 'published_at', 'deadline']
    list_filter = ['site', 'status', 'employment_type', 'department']
    search_fields = ['title', 'description', 'requirements', 'location']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'published_at'
    fieldsets = [
        ('Site e detalhes da vaga', {
            'fields': ('site', 'title', 'slug', 'department', 'employment_type', 'location', 'salary_range'),
        }),
        ('Descrição', {
            'fields': ('description', 'requirements'),
        }),
        ('Publicação', {
            'fields': ('status', 'published_at', 'deadline'),
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',),
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    ]
    actions = ['open_postings', 'close_postings']

    @admin.action(description='Abrir vagas selecionadas')
    def open_postings(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status=JobPosting.Status.OPEN, published_at=timezone.now())
        self.message_user(request, f'{updated} vaga(s) aberta(s).')

    @admin.action(description='Fechar vagas selecionadas')
    def close_postings(self, request, queryset):
        updated = queryset.update(status=JobPosting.Status.CLOSED)
        self.message_user(request, f'{updated} vaga(s) fechada(s).')


@admin.register(Application)
class ApplicationAdmin(ModelAdmin):
    list_display = ['first_name', 'last_name', 'job', 'job_site', 'status', 'created_at']
    list_filter = ['status', 'job__site', 'job', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'job__title']
    readonly_fields = ['first_name', 'last_name', 'email', 'phone', 'cover_letter', 'resume_link', 'created_at', 'updated_at']
    fieldsets = [
        ('Candidato', {
            'fields': ('first_name', 'last_name', 'email', 'phone'),
        }),
        ('Candidatura', {
            'fields': ('job', 'cover_letter', 'resume_link'),
        }),
        ('Avaliação', {
            'fields': ('status', 'notes'),
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    ]
    actions = ['mark_reviewing', 'mark_accepted', 'mark_rejected']

    @admin.display(description='Site')
    def job_site(self, obj):
        return obj.job.site

    @admin.display(description='Currículo')
    def resume_link(self, obj):
        if obj is None or not obj.resume:
            return '—'
        url = reverse('hiring:download_resume', args=[obj.pk])
        return format_html('<a href="{}" target="_blank" rel="noopener">Baixar currículo</a>', url)

    @admin.action(description='Marcar como Em Análise')
    def mark_reviewing(self, request, queryset):
        updated = queryset.update(status=Application.Status.REVIEWING)
        self.message_user(request, f'{updated} candidatura(s) marcada(s) como em análise.')

    @admin.action(description='Marcar como Aceito')
    def mark_accepted(self, request, queryset):
        updated = queryset.update(status=Application.Status.ACCEPTED)
        self.message_user(request, f'{updated} candidatura(s) aceita(s).')

    @admin.action(description='Marcar como Rejeitado')
    def mark_rejected(self, request, queryset):
        updated = queryset.update(status=Application.Status.REJECTED)
        self.message_user(request, f'{updated} candidatura(s) rejeitada(s).')
