from io import BytesIO
from pathlib import Path

from django import forms
from django.contrib import admin
from django.core.files.base import ContentFile
from django.urls import reverse_lazy
from django.utils.html import format_html
from PIL import Image, ImageOps
from unfold.admin import ModelAdmin

from apps.common.admin_mixins import AdminUXMixin
from apps.common.validators import (
    ALLOWED_IMAGE_EXTENSIONS,
    ARTICLE_IMAGE_JPEG_QUALITY,
    ARTICLE_IMAGE_MAX_HEIGHT,
    ARTICLE_IMAGE_MAX_WIDTH,
    validate_uploaded_image,
)

from .models import MediaFile, MediaFolder

# Extensões reconhecidas por tipo — a auto-detecção evita o usuário escolher na mão.
_DOCUMENT_EXTS = {'.pdf', '.doc', '.docx', '.odt', '.txt', '.rtf', '.xls', '.xlsx', '.csv', '.ppt', '.pptx'}
_VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.webm', '.mkv'}
_AUDIO_EXTS = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'}
_OTHER_IMAGE_EXTS = {'.gif', '.bmp', '.svg'}  # imagens exibíveis, mas fora do pipeline de otimização

_TYPE_ICONS = {
    MediaFile.FileType.IMAGE: 'image',
    MediaFile.FileType.DOCUMENT: 'description',
    MediaFile.FileType.VIDEO: 'movie',
    MediaFile.FileType.AUDIO: 'music_note',
    MediaFile.FileType.OTHER: 'draft',
}


def _detect_file_type(name):
    ext = Path(name or '').suffix.lower()
    if ext in ALLOWED_IMAGE_EXTENSIONS or ext in _OTHER_IMAGE_EXTS:
        return MediaFile.FileType.IMAGE
    if ext in _DOCUMENT_EXTS:
        return MediaFile.FileType.DOCUMENT
    if ext in _VIDEO_EXTS:
        return MediaFile.FileType.VIDEO
    if ext in _AUDIO_EXTS:
        return MediaFile.FileType.AUDIO
    return MediaFile.FileType.OTHER


def _optimize_image_field(file_field):
    """Transpõe (EXIF), redimensiona ao limite e reescreve a imagem otimizada.

    Mesma higiene do avatar/artigo, mas imperativa porque ``MediaFile.file`` é um
    FileField genérico. Preserva o formato (mantém transparência de PNG/WebP),
    nunca amplia a imagem e nunca aumenta o arquivo. Retorna um ``ContentFile``
    quando vale a pena trocar, ou ``None`` para deixar o original intacto.
    """
    ext = Path(file_field.name or '').suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return None  # não é imagem do pipeline (doc, vídeo, gif, svg…) → não mexe

    file_field.seek(0)
    original = file_field.read()
    file_field.seek(0)  # restaura o ponteiro caso a gente decida não trocar

    with Image.open(BytesIO(original)) as src:
        fmt = src.format
        needs_resize = src.width > ARTICLE_IMAGE_MAX_WIDTH or src.height > ARTICLE_IMAGE_MAX_HEIGHT
        if not needs_resize and fmt != 'JPEG':
            return None  # PNG/WebP pequeno: recomprimir só arriscaria inchar

        img = ImageOps.exif_transpose(src)
        img.thumbnail((ARTICLE_IMAGE_MAX_WIDTH, ARTICLE_IMAGE_MAX_HEIGHT))

        buf = BytesIO()
        if fmt == 'JPEG':
            img.convert('RGB').save(buf, 'JPEG', quality=ARTICLE_IMAGE_JPEG_QUALITY, optimize=True, progressive=True)
        elif fmt == 'PNG':
            img.save(buf, 'PNG', optimize=True)
        elif fmt == 'WEBP':
            img.save(buf, 'WEBP', quality=ARTICLE_IMAGE_JPEG_QUALITY, method=6)
        else:
            return None

    processed = buf.getvalue()
    if len(processed) >= len(original) and not needs_resize:
        return None  # não ficou menor e não precisava redimensionar → mantém original
    return ContentFile(processed)


class MediaFileForm(forms.ModelForm):
    class Meta:
        model = MediaFile
        fields = ('title', 'file', 'alt_text', 'folder')

    def clean_file(self):
        uploaded = self.cleaned_data.get('file')
        # Valida como imagem só quando a extensão é de imagem do pipeline; PDFs,
        # vídeos e afins passam livremente — a biblioteca aceita qualquer arquivo.
        if uploaded and Path(uploaded.name).suffix.lower() in ALLOWED_IMAGE_EXTENSIONS:
            validate_uploaded_image(uploaded)
        return uploaded


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
        {'label': 'Biblioteca de mídia', 'icon': 'perm_media', 'url': reverse_lazy('admin:media_library_mediafile_changelist')},
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
    form = MediaFileForm
    list_display = ['thumbnail', 'title', 'folder', 'file_type', 'file_size_label', 'uploaded_by', 'created_at']
    list_display_links = ['thumbnail', 'title']
    list_filter = ['file_type', 'folder']
    list_filter_submit = True
    search_fields = ['title', 'alt_text']
    autocomplete_fields = ['folder']
    readonly_fields = ['thumbnail_large', 'file_type', 'uploaded_by', 'file_size_label', 'created_at', 'updated_at']
    ux_list_title = 'Biblioteca de mídia'
    ux_list_description = 'Imagens e documentos reutilizáveis pelos portais. Imagens são otimizadas no envio; o tipo é detectado automaticamente.'
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
    ux_form_description = 'Envie o arquivo e dê um título legível. Imagens recebem otimização automática (orientação, tamanho e peso).'
    ux_form_icon = 'perm_media'
    ux_form_steps = [
        'Escolha um arquivo e defina um título fácil de buscar.',
        'Selecione uma pasta para facilitar a manutenção futura.',
        'Preencha o texto alternativo quando for imagem usada no site.',
    ]
    ux_after_save_actions = [
        {'label': 'Guia de gerenciamento', 'icon': 'admin_panel_settings', 'url': reverse_lazy('admin_management_guide')},
        {'label': 'Enviar outro arquivo', 'icon': 'upload_file', 'url': reverse_lazy('admin:media_library_mediafile_add')},
        {'label': 'Biblioteca', 'icon': 'perm_media', 'url': reverse_lazy('admin:media_library_mediafile_changelist')},
    ]
    fieldsets = [
        ('Arquivo', {
            'fields': ('title', 'file', 'thumbnail_large', 'alt_text'),
            'description': 'Envie a imagem ou documento e dê um título fácil de buscar. Imagens são otimizadas automaticamente.',
        }),
        ('Organização', {
            'fields': ('folder',),
        }),
        ('Detalhes', {
            'fields': ('file_type', 'uploaded_by', 'file_size_label', 'created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'O tipo é detectado automaticamente pela extensão do arquivo enviado.',
        }),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('folder', 'uploaded_by')

    @admin.display(description='Prévia')
    def thumbnail(self, obj):
        if obj and obj.file and obj.file_type == MediaFile.FileType.IMAGE:
            return format_html(
                '<img src="{}" loading="lazy" '
                'style="height:40px;width:40px;object-fit:cover;border-radius:6px;">',
                obj.file.url,
            )
        icon = _TYPE_ICONS.get(obj.file_type, 'draft') if obj else 'draft'
        return format_html('<span class="material-symbols-outlined" style="opacity:.45;">{}</span>', icon)

    @admin.display(description='Pré-visualização')
    def thumbnail_large(self, obj):
        if obj and obj.pk and obj.file and obj.file_type == MediaFile.FileType.IMAGE:
            return format_html(
                '<img src="{}" loading="lazy" '
                'style="max-height:200px;max-width:100%;border-radius:8px;">',
                obj.file.url,
            )
        return '—'

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
            obj.file_type = _detect_file_type(obj.file.name)
            optimized = _optimize_image_field(obj.file)
            if optimized is not None:
                obj.file.save(obj.file.name, optimized, save=False)
            obj.file_size = obj.file.size
        super().save_model(request, obj, form, change)
