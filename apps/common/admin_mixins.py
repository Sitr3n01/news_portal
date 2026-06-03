class AdminUXMixin:
    list_before_template = 'admin/includes/model_list_help.html'
    change_form_before_template = 'admin/includes/model_form_help.html'
    change_form_after_template = 'admin/includes/model_form_next_steps.html'
    warn_unsaved_form = True

    ux_list_title = ''
    ux_list_description = ''
    ux_list_icon = 'info'
    ux_list_actions = []
    ux_list_filters = []
    ux_empty_message = ''

    ux_form_title = ''
    ux_form_description = ''
    ux_form_icon = 'edit_note'
    ux_form_steps = []
    ux_after_save_title = 'Depois de salvar'
    ux_after_save_description = ''
    ux_after_save_actions = []
