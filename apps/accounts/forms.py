import logging

from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from apps.common import turnstile

from .models import CustomUser

logger = logging.getLogger(__name__)


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label='E-mail')
    subscribe_newsletter = forms.BooleanField(
        required=False,
        initial=False,
        label='Receber newsletter',
        help_text='Receba novos artigos publicados diretamente no seu e-mail.',
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError(
                'Não foi possível criar a conta. Verifique os dados e tente novamente.'
            )
        return email

    def clean(self):
        cleaned_data = super().clean()
        # Só exige o desafio anti-bot quando há request (uso público real) e uma
        # site key configurada. Sem chave configurada (ex.: config.settings.test,
        # onde DEBUG=False e não há segredo de Turnstile) o widget nem aparece no
        # template, então a validação fica desativada de forma explícita — em vez
        # de rejeitar todo cadastro por falta de token que o usuário nunca viu.
        if self.request is None:
            return cleaned_data
        if not turnstile.get_turnstile_site_key():
            # Fail-open documentado, mas ruidoso nos logs: cadastros públicos
            # seguem sem anti-bot enquanto a chave não for configurada.
            logger.warning('Cadastro público sem verificação anti-bot: CLOUDFLARE_TURNSTILE_SITE_KEY não configurada.')
            return cleaned_data

        token = self.data.get(turnstile.TURNSTILE_RESPONSE_FIELD)
        remote_ip = turnstile.get_client_ip(self.request)
        if not turnstile.verify_turnstile(token, remote_ip):
            self.add_error(None, 'Confirme a verificação anti-bot para criar sua conta.')
        return cleaned_data

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = UserChangeForm.Meta.fields


class ProfileForm(forms.ModelForm):
    """Form público de edição do perfil. Hoje só a foto; o validador de imagem
    vem do próprio campo do modelo (apps.common.validators)."""

    class Meta:
        model = CustomUser
        fields = ('avatar',)
