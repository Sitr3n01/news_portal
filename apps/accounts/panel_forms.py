"""Formulário do login unificado (/entrar/)."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from apps.accounts import panels


class PanelLoginForm(AuthenticationForm):
    """Autenticação padrão do Django mais a escolha de destino.

    O campo ``panel`` é CONSELHO, não autorização: o ChoiceField recusa valores
    fora da lista (falha fechado) e a view ainda re-filtra o valor aceito por
    ``panels.available_panels(user)``. Quem escolher uma área a que não tem
    direito é redirecionado para a que tem — nunca promovido.
    """

    panel = forms.ChoiceField(
        label='Entrar em',
        required=False,
        widget=forms.RadioSelect,
        choices=[
            (panels.PANEL_CMS, panels.PANEL_LABELS[panels.PANEL_CMS]),
            (panels.PANEL_ADMIN, panels.PANEL_LABELS[panels.PANEL_ADMIN]),
        ],
    )

    # O Wagtail deixa a sessão expirar ao fechar o navegador, a não ser que o
    # usuário peça o contrário. Sem reproduzir isso aqui, todo mundo da redação
    # passaria a ganhar em silêncio o cookie de 12h do SESSION_COOKIE_AGE.
    remember = forms.BooleanField(
        label='Continuar conectado neste computador',
        required=False,
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Usuário ou senha incorretos. Verifique os dados e tente novamente.',
        'inactive': 'Esta conta está desativada. Fale com um Administrador Geral.',
    }
