"""Camada de envio (apps.accounts.mailer) e o system check que a protege em produção.

Templates via locmem.Loader (dict em memória): mais simples e mais robusto do
que criar arquivos reais em templates/ só para o teste — cada caso controla o
conteúdo exato (inclusive um assunto malicioso com quebra de linha) sem tocar
disco, e o loader some sozinho ao fim do teste junto com `settings.TEMPLATES`.
"""

import logging
import smtplib

import pytest
from django.core import mail

from apps.accounts.checks import check_email_backend
from apps.accounts.mailer import mask_email, send_branded_email


def _locmem_templates(templates):
    return [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'OPTIONS': {
                'loaders': [
                    ('django.template.loaders.locmem.Loader', templates),
                ],
            },
        },
    ]


# ── mask_email ──────────────────────────────────────────────────────────────

def test_mask_email_normal():
    assert mask_email('joao.silva@exemplo.com') == 'j***@e***.com'


def test_mask_email_empty_string_does_not_raise():
    assert mask_email('') == '(vazio)'


def test_mask_email_without_at_sign_does_not_raise():
    assert mask_email('nao-e-um-email') == '***'


def test_mask_email_single_letter_local_part():
    assert mask_email('a@exemplo.com') == 'a***@e***.com'


# ── send_branded_email: caminho feliz ───────────────────────────────────────

@pytest.mark.django_db
def test_send_branded_email_success(settings):
    settings.TEMPLATES = _locmem_templates({
        'emails/test_subject.txt': 'Assunto de teste',
        'emails/test_body.txt': 'Corpo em texto puro.',
        'emails/test_body.html': '<p>Corpo em HTML.</p>',
    })

    ok = send_branded_email(
        to='destinatario@example.com',
        subject_template='emails/test_subject.txt',
        text_template='emails/test_body.txt',
        html_template='emails/test_body.html',
        context={},
        purpose='test_success',
    )

    assert ok is True
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.subject == 'Assunto de teste'
    assert message.to == ['destinatario@example.com']
    assert ('<p>Corpo em HTML.</p>', 'text/html') in message.alternatives
    assert '\n' not in message.subject


@pytest.mark.django_db
def test_send_branded_email_subject_with_linebreak_becomes_single_line(settings):
    """Header injection: um '\\n' no template do assunto não pode sobreviver ao envio."""
    settings.TEMPLATES = _locmem_templates({
        'emails/injection_subject.txt': 'Primeira linha\nSegunda linha injetada',
        'emails/body.txt': 'corpo',
        'emails/body.html': '<p>corpo</p>',
    })

    ok = send_branded_email(
        to='vitima@example.com',
        subject_template='emails/injection_subject.txt',
        text_template='emails/body.txt',
        html_template='emails/body.html',
        context={},
        purpose='test_injection',
    )

    assert ok is True
    assert len(mail.outbox) == 1
    assert '\n' not in mail.outbox[0].subject
    assert mail.outbox[0].subject == 'Primeira linhaSegunda linha injetada'


# ── Erros de template ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_send_branded_email_missing_template_returns_false_and_logs(settings, caplog):
    settings.TEMPLATES = _locmem_templates({
        'emails/body.txt': 'corpo',
        'emails/body.html': '<p>corpo</p>',
        # 'emails/nao_existe.txt' não existe de propósito.
    })

    with caplog.at_level(logging.ERROR, logger='apps.email'):
        ok = send_branded_email(
            to='alguem@example.com',
            subject_template='emails/nao_existe.txt',
            text_template='emails/body.txt',
            html_template='emails/body.html',
            context={},
            purpose='test_missing_template',
        )

    assert ok is False
    assert len(mail.outbox) == 0
    assert 'EMAIL_TEMPLATE_ERROR' in caplog.text
    assert 'emails/nao_existe.txt' in caplog.text


# ── Falha de envio SMTP ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_send_branded_email_smtp_auth_failure_returns_false_and_logs_reason(settings, monkeypatch, caplog):
    settings.TEMPLATES = _locmem_templates({
        'emails/subject.txt': 'Assunto',
        'emails/body.txt': 'corpo',
        'emails/body.html': '<p>corpo</p>',
    })

    def _raise_auth_error(self, *args, **kwargs):
        raise smtplib.SMTPAuthenticationError(535, b'Authentication failed')

    from apps.accounts import mailer

    monkeypatch.setattr(mailer.EmailMultiAlternatives, 'send', _raise_auth_error)

    with caplog.at_level(logging.ERROR, logger='apps.email'):
        ok = send_branded_email(
            to='destino@example.com',
            subject_template='emails/subject.txt',
            text_template='emails/body.txt',
            html_template='emails/body.html',
            context={},
            purpose='test_smtp_failure',
        )

    assert ok is False
    assert len(mail.outbox) == 0
    assert 'EMAIL_SEND_FAILED' in caplog.text
    assert 'reason=smtp_auth' in caplog.text


# ── Vazamento de dado sensível ───────────────────────────────────────────────

@pytest.mark.django_db
def test_send_branded_email_never_logs_full_recipient_address(settings, caplog):
    settings.TEMPLATES = _locmem_templates({
        'emails/subject.txt': 'Assunto',
        'emails/body.txt': 'corpo',
        'emails/body.html': '<p>corpo</p>',
    })
    endereco = 'joao.silva@exemplo.com'

    with caplog.at_level(logging.INFO, logger='apps.email'):
        ok = send_branded_email(
            to=endereco,
            subject_template='emails/subject.txt',
            text_template='emails/body.txt',
            html_template='emails/body.html',
            context={},
            purpose='test_leak',
        )

    assert ok is True
    assert len(caplog.records) > 0
    for record in caplog.records:
        assert endereco not in record.getMessage()


# ── System check: accounts.E001/W001/W002 ───────────────────────────────────

def test_check_email_backend_flags_console_backend_outside_debug(settings):
    settings.EMAIL_CHECK_SKIP = False
    settings.DEBUG = False
    settings.EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

    issues = check_email_backend(None)

    assert any(issue.id == 'accounts.E001' for issue in issues)


def test_check_email_backend_passes_with_smtp_fully_configured(settings):
    settings.EMAIL_CHECK_SKIP = False
    settings.DEBUG = False
    settings.EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    settings.EMAIL_HOST_USER = 'contato@example.com'
    settings.EMAIL_HOST_PASSWORD = 'uma-senha-qualquer'
    settings.DEFAULT_FROM_EMAIL = 'contato@example.com'

    issues = check_email_backend(None)

    assert issues == []


def test_check_email_backend_skips_when_flag_is_set(settings):
    """Espelha config/settings/test.py: sem o skip, todo `pytest` acusaria accounts.E001."""
    settings.EMAIL_CHECK_SKIP = True
    settings.DEBUG = False
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

    assert check_email_backend(None) == []
