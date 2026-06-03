from django.contrib import admin
from django.urls import reverse_lazy
from unfold.admin import ModelAdmin

from apps.common.admin_mixins import AdminUXMixin

from .models import MediaFile, MediaFolder


@admin.register(MediaFolder)
class MediaFolderAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['name', 'parent']
    search_fields = ['name']
    autocomplete_fields = ['parent']
    ux_list_title = 'Pastas da biblioteca de mídia'
    ux_list_description = 'Organize imagens, documentos e arquivos reutilizáveis por assunto ou área do portal.'
    ux_list_icon = 'folder'
    ux_list_actions = [
        {'label': 'Guia de gerenciamento', 'icon': 'admin_panel_settings', 'url': reverse_lazy('admin_management_guide')},
        {'label': 'Nova pasta', 'icon': 'create_new_folder', 'url': reverse_lazy('admin:media_library_mediafolder_add'), 'kind': 'primary'},
    ]
    ux_empty_message = 'Nenhuma pasta criada. Comece com pastas simples, como Escola, Notícias e Documentos.'
    ux_form_title = 'Pasta de mídia'
    ux_form_description = 'Use pastas para tornar a biblioteca previsível para usuários leigos.'
    ux_form_icon = 'folder'
    ux_form_steps = [
        'Use nome curto e fácil de reconhecer.',
        'Escolha pasta superior apenas quando houver hierarquia necessária.',
        'Evite criar níveis demais para não dificultar a busca.',
    ]
    ux_after_save_actions = [
        {'label': 'Guia de gerenciamento', 'icon': 'admin_panel_settings', 'url': reverse_lazy('admin_management_guide')},
        {'label': 'Enviar arquivo', 'icon': 'upload_file', 'url': reverse_lazy('admin:media_library_mediafile_add')},
        {'label': 'Todas as pastas', 'icon': 'folder', 'url': reverse_lazy('admin:media_library_mediafolder_changelist')},
    ]
    fieldsets = [
        ('Organização', {
            'fields': ('name', 'parent'),
        }),
    ]


@admin.register(MediaFile)
class MediaFileAdmin(AdminUXMixin, ModelAdmin):
    list_display = ['title', 'folder', 'file_type', 'uploaded_by', 'file_size_label', 'created_at']
    list_filter = ['file_type', 'folder']
    list_filter_submit = True
    search_fields = ['title', 'alt_text']
    autocomplete_fields = ['folder']
    readonly_fields = ['uploaded_by', 'file_size_label', 'created_at', 'updated_at']
    radio_fields = {'file_type': admin.HORIZONTAL}
    ux_list_title = 'Biblioteca de mídia'
    ux_list_description = 'Gerencie arquivos compartilhados pelos portais. Prefira títulos claros e texto alternativo em imagens.'
    ux_list_icon = 'perm_media'
    ux_list_actions = [
        {'label': 'Guia de gerenciamento', 'icon': 'admin_panel_settings', 'url': reverse_lazy('admin_management_guide')},
        {'label': 'Enviar arquivo', 'icon': 'upload_file', 'url': reverse_lazy('admin:media_library_mediafile_add'), 'kind': 'primary'},
        {'label': 'Pastas', 'icon': 'folder', 'url': reverse_lazy('admin:media_library_mediafolder_changelist')},
    ]
    ux_list_filters = [
        {'label': 'Imagens', 'icon': 'image', 'url': '?file_type__exact=image'},
        {'label': 'Documentos', 'icon': 'description', 'url': '?file_type__exact=document'},
        {'label': 'Outros', 'icon': 'draft', 'url': '?file_type__exact=other'},
    ]
    ux_empty_message = 'Nenhum arquivo na biblioteca. Envie imagens e documentos usados nos portais.'
    ux_form_title = 'Arquivo de mídia'
    ux_form_description = 'Cadastre arquivos com título legível e texto alternativo quando forem imagens.'
    ux_form_icon = 'perm_media'
    ux_form_steps = [
        'Escolha um arquivo e defina um título fácil de buscar.',
        'Selecione tipo e pasta para facilitar manutenção futura.',
        'Preencha texto alternativo em imagens usadas no site.',
    ]
    ux_after_save_actions = [
        {'label': 'Guia de gerenciamento', 'icon': 'admin_panel_settings', 'url': reverse_lazy('admin_management_guide')},
        {'label': 'Enviar outro arquivo', 'icon': 'upload_file', 'url': reverse_lazy('admin:media_library_mediafile_add')},
        {'label': 'Biblioteca', 'icon': 'perm_media', 'url': reverse_lazy('admin:media_library_mediafile_changelist')},
    ]
    fieldsets = [
        ('Arquivo', {
            'fields': ('title', 'file', 'file_type', 'alt_text'),
        }),
        ('Organização', {
            'fields': ('folder',),
        }),
        ('Auditoria', {
            'fields': ('uploaded_by', 'file_size_label', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('folder', 'uploaded_by')

    @admin.display(description='Tamanho')
    def file_size_label(self, obj):
        if not obj or not obj.file_size:
            return '—'
        if obj.file_size < 1024:
            return f'{obj.file_size} B'
        if obj.file_size < 1024 * 1024:
            return f'{obj.file_size / 1024:.1f} KB'
        return f'{obj.file_size / (1024 * 1024):.1f} MB'

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by_id:
            obj.uploaded_by = request.user
        if obj.file:
            obj.file_size = obj.file.size
        super().save_model(request, obj, form, change)
