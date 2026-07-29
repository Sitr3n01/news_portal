from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from apps.common import turnstile

from .models import CustomUser


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
        # Mesmo padrão de NewsletterSubscriptionForm (apps/news/forms.py):
        # request só chega quando a view de fato o passa; um form instanciado
        # sem request (script, teste antigo) simplesmente pula a checagem no
        # clean() abaixo, em vez de estourar.
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        # Normaliza para minúsculas e busca com __iexact — as duas coisas, não
        # uma só. Antes daqui usava-se `filter(email=email)`, comparação
        # sensível a maiúsculas tanto no SQLite quanto no PostgreSQL: com
        # 'Fulano@x.com' já cadastrado, 'FULANO@X.COM' passava e nascia uma
        # SEGUNDA conta para a mesma caixa postal.
        #
        # Pela RFC 5321 a parte local do endereço é tecnicamente sensível a
        # maiúsculas, mas nenhum provedor real trata assim. Considerar
        # 'a@x.com' e 'A@x.com' identidades distintas não é rigor: é entregar
        # duas contas para a mesma pessoa, e inviabiliza casar identidade por
        # e-mail — que é exatamente o que o login com Google precisa fazer
        # para reconhecer uma conta que já existe em vez de duplicá-la.
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            # Mensagem deliberadamente genérica: dizer "este e-mail já tem
            # conta" transformaria o cadastro em oráculo de quem é cliente.
            raise forms.ValidationError(
                'Não foi possível criar a conta. Verifique os dados e tente novamente.'
            )
        return email

    def clean(self):
        cleaned_data = super().clean()
        if self.request is None:
            return cleaned_data

        # O cadastro agora dispara e-mail de confirmação (Fase 3): sem
        # anti-bot aqui, o formulário público vira mailbomb grátis contra
        # endereços de terceiros — quem preenche o formulário nem precisa ser
        # dono do e-mail digitado, e cada envio nosso vai para a caixa de
        # outra pessoa.
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


class PasswordResetRequestForm(forms.Form):
    """Pede o e-mail para iniciar a recuperação de senha por código.

    NÃO valida se a conta existe — de propósito. Quem decide isso é a view, e
    ela responde igual nos dois casos; levantar ValidationError aqui quando o
    e-mail não tem conta transformaria o formulário num oráculo de quem está
    cadastrado no site.
    """

    email = forms.EmailField(label='E-mail', max_length=254)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        # Mesma normalização de CustomUserCreationForm.clean_email: a busca da
        # conta é __iexact, então o valor precisa chegar lá já sem espaços e
        # em minúsculas para o e-mail congelado no VerificationCode bater.
        return (self.cleaned_data.get('email') or '').strip().lower()

    def clean(self):
        cleaned_data = super().clean()
        if self.request is None:
            return cleaned_data

        # Este endpoint dispara e-mail para um endereço que quem preenche não
        # precisa possuir — é o alvo clássico de mailbomb. O rate limit por IP
        # da view é a segunda camada; o anti-bot é a primeira.
        token = self.data.get(turnstile.TURNSTILE_RESPONSE_FIELD)
        remote_ip = turnstile.get_client_ip(self.request)
        if not turnstile.verify_turnstile(token, remote_ip):
            self.add_error(None, 'Confirme a verificação anti-bot para continuar.')
        return cleaned_data


class VerificationCodeForm(forms.Form):
    """Formulário de entrada do código de 6 dígitos (confirmação de e-mail).

    Sem validação de formato além do tamanho: quem decide se o código serve é
    apps.accounts.verification.check_code (via _normalize_code + hash), e
    duplicar a regra de formato aqui criaria uma segunda fonte de verdade que
    um dia divergiria da de lá (ex.: se o comprimento do código mudasse).
    """

    code = forms.CharField(
        label='Código',
        max_length=12,  # cabe a versão formatada '123 456' ou '123-456'
        widget=forms.TextInput(attrs={
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
            'pattern': '[0-9 -]*',
            'autofocus': True,
        }),
    )
