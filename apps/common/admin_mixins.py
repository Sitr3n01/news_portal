from contextvars import ContextVar

from django.contrib import admin
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.admin.utils import quote
from django.template.loader import render_to_string
from django.urls import NoReverseMatch, reverse

# Requisição da lista em andamento, para a coluna do menu ⋯ (as colunas do
# list_display só recebem o objeto). ContextVar: o ModelAdmin é compartilhado
# entre requisições simultâneas, então nada de guardar a requisição nele.
_list_request = ContextVar('nr_list_request', default=None)


class AdminUXMixin:
    list_before_template = 'admin/includes/model_list_help.html'
    warn_unsaved_form = True

    ux_list_title = ''
    ux_list_description = ''
    ux_list_icon = 'info'
    ux_list_actions = []
    ux_list_filters = []
    # Rótulo da primeira aba do cabeçalho da lista ("Todas" para mensagens, vagas…).
    ux_list_all_label = 'Todos'
    ux_empty_message = ''

    # Formulário: o texto do "Guia" da barra (templates/admin/includes/form_bar.html)
    # e os atalhos que aparecem nele. ux_form_new_title troca o título da
    # tela de adicionar ("Adicionar {verbose_name}").
    ux_form_title = ''
    ux_form_description = ''
    ux_form_icon = 'edit_note'
    ux_form_steps = []
    ux_form_new_title = ''
    ux_after_save_title = 'Atalhos'
    ux_after_save_description = ''
    ux_after_save_actions = []

    # Selo de estado na barra do formulário (e na coluna de status das listas
    # que quiserem): o campo do modelo, o tom do nr-status para cada valor
    # (info, success, warning, neutral, archived, danger) e, para campos
    # booleanos, o rótulo de cada valor.
    ux_status_field = ''
    ux_status_tones = {}
    ux_status_labels = {}

    # Menu ⋯ ao fim de cada linha da lista: abrir/editar, as ações em massa
    # aplicadas só àquela linha (preenchidas por newsroom.js a partir da barra
    # de seleção) e remover, cada item só para quem tem a permissão.
    ux_row_menu = True

    def nr_status(self, obj):
        field = self.ux_status_field
        if not field or obj is None:
            return None
        value = getattr(obj, field, None)
        label = self.ux_status_labels.get(value)
        if label is None:
            display = getattr(obj, f'get_{field}_display', None)
            label = display() if callable(display) else str(value)
        return {'label': str(label), 'tone': self.ux_status_tones.get(value, 'neutral')}

    # O Unfold 0.87 não tem tradução pt-BR e põe "Select value" como primeira
    # opção das listas de escolha e de registros relacionados.
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if 'choices' not in kwargs:
            kwargs['choices'] = db_field.get_choices(include_blank=db_field.blank, blank_choice=[('', 'Selecione')])
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if field is not None and 'empty_label' not in kwargs and getattr(field, 'empty_label', None) is not None:
            field.empty_label = 'Selecione'
        return field

    def nr_form_links(self, request, obj):
        """Links extras do menu ⋯ da barra do formulário, antes de Remover:
        [{'label', 'url', 'icon'}]. Cada tela confere a própria permissão."""
        return []

    def get_list_display(self, request):
        list_display = list(super().get_list_display(request))
        _list_request.set(request)
        if self.ux_row_menu and IS_POPUP_VAR not in request.GET and 'nr_row_menu' not in list_display:
            list_display.append('nr_row_menu')
        return list_display

    @admin.display(description='')
    def nr_row_menu(self, obj):
        request = _list_request.get()
        if request is None:
            return ''
        opts = self.model._meta
        name = f'admin:{opts.app_label}_{opts.model_name}'
        can_change = self.has_change_permission(request, obj)
        try:
            change_url = reverse(f'{name}_change', args=[quote(obj.pk)])
        except NoReverseMatch:
            change_url = ''
        delete_url = ''
        if self.has_delete_permission(request, obj):
            try:
                delete_url = reverse(f'{name}_delete', args=[quote(obj.pk)])
            except NoReverseMatch:
                delete_url = ''
        return render_to_string('admin/includes/row_menu.html', {
            'label': str(obj),
            'change_url': change_url if (can_change or self.has_view_permission(request, obj)) else '',
            'change_label': 'Editar' if can_change else 'Abrir',
            'delete_url': delete_url,
        })


class SuperuserOnlyAdminMixin:
    """Guarda recursos fora do front atual sem remover modelos ou dados."""

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
