from django import forms

from apps.common import turnstile
from apps.school.courses import find_course

from .models import ContactInquiry


class ContactInquiryForm(forms.ModelForm):
    PUBLIC_SUBJECT_CHOICES = [
        ('general', 'Geral'),
        ('admissions', 'Cursos e inscrições'),
        ('support', 'Mentorias e projetos'),
        ('other', 'Outro'),
    ]
    PUBLIC_SUBJECT_LABELS_EN = {
        'general': 'General',
        'admissions': 'Courses and enrollment',
        'support': 'Mentoring and projects',
        'other': 'Other',
    }

    class Meta:
        model = ContactInquiry
        fields = ['name', 'email', 'phone', 'subject', 'course_interest', 'message']
        widgets = {'course_interest': forms.HiddenInput}

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['subject'].choices = self.PUBLIC_SUBJECT_CHOICES

    @property
    def subject_options(self):
        """(valor, rótulo, rótulo em inglês) de cada assunto, para o select trocar de idioma."""
        return [(value, label, self.PUBLIC_SUBJECT_LABELS_EN[value]) for value, label in self.PUBLIC_SUBJECT_CHOICES]

    def clean_course_interest(self):
        # O campo oculto traz o slug do card de Cursos; a mensagem guarda o título, e um slug fora do catálogo é ignorado.
        course = find_course(self.cleaned_data.get('course_interest', ''))
        return course['title'] if course else ''

    def clean(self):
        cleaned_data = super().clean()
        if self.request is None:
            return cleaned_data

        token = self.data.get(turnstile.TURNSTILE_RESPONSE_FIELD)
        remote_ip = turnstile.get_client_ip(self.request)
        if not turnstile.verify_turnstile(token, remote_ip):
            self.add_error(None, 'Confirme a verificação anti-bot para enviar.')
        return cleaned_data
