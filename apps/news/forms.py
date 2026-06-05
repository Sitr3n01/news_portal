from django import forms

from apps.common import turnstile

from .models import NewsletterSubscription


class NewsletterSubscriptionForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscription
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'placeholder': 'Seu melhor e-mail',
                'class': (
                    'flex-grow rounded-full border-gray-300 shadow-sm '
                    'focus:border-primary-500 focus:ring-primary-500 px-6 py-4'
                ),
            })
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if self.request is None:
            return cleaned_data

        token = self.data.get(turnstile.TURNSTILE_RESPONSE_FIELD)
        remote_ip = turnstile.get_client_ip(self.request)
        if not turnstile.verify_turnstile(token, remote_ip):
            self.add_error(None, 'Confirme a verificação anti-bot para assinar.')
        return cleaned_data
