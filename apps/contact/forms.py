from django import forms

from apps.common import turnstile

from .models import ContactInquiry


class ContactInquiryForm(forms.ModelForm):
    PUBLIC_SUBJECT_CHOICES = [
        ('general', 'Geral'),
        ('admissions', 'Cursos e inscrições'),
        ('support', 'Mentorias e projetos'),
        ('other', 'Outro'),
    ]

    class Meta:
        model = ContactInquiry
        fields = ['name', 'email', 'phone', 'subject', 'message']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['subject'].choices = self.PUBLIC_SUBJECT_CHOICES

    def clean(self):
        cleaned_data = super().clean()
        if self.request is None:
            return cleaned_data

        token = self.data.get(turnstile.TURNSTILE_RESPONSE_FIELD)
        remote_ip = turnstile.get_client_ip(self.request)
        if not turnstile.verify_turnstile(token, remote_ip):
            self.add_error(None, 'Confirme a verificação anti-bot para enviar.')
        return cleaned_data
