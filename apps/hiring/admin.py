from django.contrib import admin
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html
from django.utils.text import format_lazy
from unfold.admin import ModelAdmin

from apps.common.admin_mixins import AdminUXMixin

from .models import Application, Department, JobPosting


@admin.register(Department)
class DepartmentAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['name', 'site', 'slug']
    list_filter = ['site']
    list_filter_submit = True
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ux_list_title = 'Departamentos de contratação'
    ux_list_description = 'Organize vagas por área para facilitar filtros no portal e análise interna das candidaturas.'
    ux_list_icon = 'business'
    ux_list_actions = [
        {'label': 'Guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Novo departamento', 'icon': 'add_business', 'url': reverse_lazy('admin:hiring_department_add'), 'kind': 'primary'},
    ]
    ux_empty_message = 'Nenhum departamento criado. Cadastre áreas antes de publicar vagas.'
    ux_form_title = 'Departamento'
    ux_form_description = 'Use nomes simples, reconhecíveis por candidatos e equipe administrativa.'
    ux_form_icon = 'business'
    ux_form_steps = [
        'Escolha o site correto.',
        'Use um nome claro para a área.',
        'Confira o slug antes de salvar.',
    ]
    ux_after_save_actions = [
        {'label': 'Guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Criar vaga', 'icon': 'add_business', 'url': reverse_lazy('admin:hiring_jobposting_add')},
    ]
    fieldsets = [
        ('Departamento', {
            'fields': ('site', 'name', 'slug'),
        }),
    ]


@admin.register(JobPosting)
class JobPostingAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['title', 'site', 'department', 'employment_type', 'status', 'published_at', 'deadline']
    list_filter = ['site', 'status', 'employment_type', 'department']
    list_filter_submit = True
    search_fields = ['title', 'description', 'requirements', 'location']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at']
    radio_fields = {'status': admin.HORIZONTAL, 'employment_type': admin.HORIZONTAL}
    date_hierarchy = 'published_at'
    ux_list_title = 'Vagas do portal escolar'
    ux_list_description = 'Abra vagas quando houver oportunidade real, mantenha rascunhos privados e feche posições concluídas.'
    ux_list_icon = 'work'
    ux_list_actions = [
        {'label': 'Guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Abrir nova vaga', 'icon': 'add_business', 'url': reverse_lazy('admin:hiring_jobposting_add'), 'kind': 'primary'},
    ]
    ux_list_filters = [
        {'label': 'Abertas', 'icon': 'work', 'url': '?status__exact=open'},
        {'label': 'Rascunhos', 'icon': 'draft', 'url': '?status__exact=draft'},
        {'label': 'Fechadas', 'icon': 'lock', 'url': '?status__exact=closed'},
    ]
    ux_empty_message = 'Nenhuma vaga cadastrada. Crie uma vaga em rascunho e publique quando estiver revisada.'
    ux_form_title = 'Vaga'
    ux_form_description = 'Transforme uma oportunidade em uma página clara para candidatos, com descrição, requisitos e prazo.'
    ux_form_icon = 'work'
    ux_form_steps = [
        'Preencha detalhes da vaga e selecione o departamento correto.',
        'Explique responsabilidades e requisitos em linguagem objetiva.',
        'Use status Aberta apenas quando a vaga puder receber candidaturas.',
    ]
    ux_after_save_description = 'Depois de publicar, acompanhe candidaturas recebidas pelo guia escolar.'
    ux_after_save_actions = [
        {'label': 'Guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Candidaturas', 'icon': 'description', 'url': reverse_lazy('admin:hiring_application_changelist')},
    ]
    fieldsets = [
        ('Site e detalhes da vaga', {
            'fields': ('site', 'title', 'slug', 'department', 'employment_type', 'location', 'salary_range'),
            'classes': ('tab',),
        }),
        ('Descrição', {
            'fields': ('description', 'requirements'),
            'classes': ('tab',),
        }),
        ('Publicação', {
            'fields': ('status', 'published_at', 'deadline'),
            'classes': ('tab',),
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('tab',),
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
class ApplicationAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['first_name', 'last_name', 'job', 'job_site', 'status', 'created_at']
    list_filter = ['status', 'job__site', 'job', 'created_at']
    list_filter_submit = True
    search_fields = ['first_name', 'last_name', 'email', 'job__title']
    readonly_fields = ['first_name', 'last_name', 'email', 'phone', 'cover_letter', 'resume_link', 'created_at', 'updated_at']
    radio_fields = {'status': admin.HORIZONTAL}
    ux_list_title = 'Candidaturas'
    ux_list_description = 'Revise primeiro as candidaturas recebidas, registre notas internas e mova o status conforme a triagem avança.'
    ux_list_icon = 'description'
    ux_list_actions = [
        {'label': 'Guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
    ]
    ux_list_filters = [
        {'label': 'Recebidas', 'icon': 'inbox', 'url': '?status__exact=received'},
        {'label': 'Em análise', 'icon': 'rate_review', 'url': '?status__exact=reviewing'},
        {'label': 'Entrevista', 'icon': 'event', 'url': '?status__exact=interview'},
    ]
    ux_empty_message = 'Nenhuma candidatura encontrada para os filtros atuais.'
    ux_form_title = 'Revisão de candidatura'
    ux_form_description = 'Os dados do candidato são preservados como enviados. Atualize apenas status e notas internas.'
    ux_form_icon = 'rate_review'
    ux_form_steps = [
        'Leia currículo e carta de apresentação.',
        'Use notas internas para registrar contexto da avaliação.',
        'Mude o status para orientar a próxima ação da equipe.',
    ]
    ux_after_save_actions = [
        {'label': 'Guia escolar', 'icon': 'school', 'url': reverse_lazy('admin_school_guide')},
        {'label': 'Recebidas', 'icon': 'inbox', 'url': format_lazy('{}?status__exact=received', reverse_lazy('admin:hiring_application_changelist'))},
        {'label': 'Todas as candidaturas', 'icon': 'list', 'url': reverse_lazy('admin:hiring_application_changelist')},
    ]
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
