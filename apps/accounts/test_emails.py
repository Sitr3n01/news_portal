"""E-mails de alto nível (apps.accounts.emails) e o contexto compartilhado
(apps.accounts.mailer.build_email_context) que os alimenta.

O que mais importa garantir aqui não é "o e-mail foi enviado" — isso já é
coberto por test_mailer.py, que testa send_branded_email isoladamente. O que
é específico deste par de funções é o CÓDIGO em texto puro:
  1. chega ao corpo em texto E ao HTML (senão o e-mail não cumpre a função);
  2. nunca aparece no assunto (vazaria em notificação de tela bloqueada e em
     prévia de terceiros, mesmo com o e-mail ainda fechado);
  3. nunca aparece em log nenhum, nem no caminho feliz (EMAIL_SENT já loga
     purpose+destinatário mascarado hoje — isto aqui é para garantir que
     ninguém acrescente `context` ou `code` a esse log no futuro sem que a
     suíte reclame).
"""

import logging

import pytest
from django.contrib.sites.models import Site
from django.core import mail
from django.utils import timezone

from apps.accounts.emails import (
    send_password_reset_code_email,
    send_verification_code_email,
)
from apps.accounts.mailer import build_email_context
from apps.common.models import SiteExtension

# Os dois códigos de exemplo pedidos na verificação manual (render_emails.py),
# reaproveitados aqui para o mesmo par HTML/TXT ficar coberto pelos dois lados.
CODIGO_VERIFICACAO = '482731'
CODIGO_RESET = '719284'


@pytest.fixture
def usuario(db, django_user_model):
    return django_user_model.objects.create_user(
        username='usuaria', email='usuaria@example.com', password='SenhaTeste#2026',
    )


def _unica_alternativa_html(message):
    """Extrai o corpo da única alternativa text/html anexada à mensagem.

    Assumir "exatamente uma" é proposital: send_branded_email chama
    attach_alternative uma única vez (o HTML) — zero ou mais de uma já seria
    uma regressão em send_branded_email, não só um detalhe deste teste.
    """
    html_alternatives = [conteudo for conteudo, mimetype in message.alternatives if mimetype == 'text/html']
    assert len(html_alternatives) == 1
    return html_alternatives[0]


# ── send_verification_code_email ────────────────────────────────────────────

@pytest.mark.django_db
def test_send_verification_code_email_success(usuario):
    ok = send_verification_code_email(usuario, CODIGO_VERIFICACAO)

    assert ok is True
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert CODIGO_VERIFICACAO in message.body
    assert CODIGO_VERIFICACAO not in message.subject
    assert CODIGO_VERIFICACAO in _unica_alternativa_html(message)


@pytest.mark.django_db
def test_send_verification_code_email_does_not_log_code(usuario, caplog):
    with caplog.at_level(logging.INFO, logger='apps.email'):
        send_verification_code_email(usuario, CODIGO_VERIFICACAO)

    assert len(caplog.records) > 0  # o caminho feliz loga EMAIL_SENT; um teste sem nenhum registro não provaria nada
    for record in caplog.records:
        assert CODIGO_VERIFICACAO not in record.getMessage()


# ── send_password_reset_code_email ──────────────────────────────────────────

@pytest.mark.django_db
def test_send_password_reset_code_email_success(usuario):
    ok = send_password_reset_code_email(usuario, CODIGO_RESET)

    assert ok is True
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert CODIGO_RESET in message.body
    assert CODIGO_RESET not in message.subject
    assert CODIGO_RESET in _unica_alternativa_html(message)


@pytest.mark.django_db
def test_send_password_reset_code_email_does_not_log_code(usuario, caplog):
    with caplog.at_level(logging.INFO, logger='apps.email'):
        send_password_reset_code_email(usuario, CODIGO_RESET)

    assert len(caplog.records) > 0
    for record in caplog.records:
        assert CODIGO_RESET not in record.getMessage()


# ── build_email_context ─────────────────────────────────────────────────────

@pytest.mark.django_db
def test_build_email_context_has_brand_name_and_current_year():
    context = build_email_context()

    assert context['news_portal_name'] == 'Blog da Kelly'
    assert isinstance(context['current_year'], int)
    assert context['current_year'] == timezone.now().year


@pytest.mark.django_db
def test_build_email_context_does_not_raise_without_site_extension():
    """SiteExtension é OneToOne opcional — instalação nova, ou site ainda sem
    configuração salva, não pode derrubar o envio de um e-mail transacional.
    """
    site = Site.objects.get_current()
    SiteExtension.objects.filter(site=site).delete()
    # django.contrib.sites cacheia o Site (e o acessor `.extension` fica preso
    # à instância) no nível do processo, não da transação de teste — sem
    # limpar aqui, o resultado dependeria de qual outro teste rodou antes.
    Site.objects.clear_cache()

    context = build_email_context()

    assert context['site_settings'] is None


@pytest.mark.django_db
def test_build_email_context_does_not_raise_without_configured_site(settings):
    """Mesma tolerância do teste acima, um nível abaixo: SITE_ID apontando
    para uma linha inexistente (Site.DoesNotExist) também não pode estourar.
    """
    settings.SITE_ID = 999999
    Site.objects.clear_cache()

    context = build_email_context()

    assert context['site_settings'] is None
    assert context['base_url'] == ''
    assert context['news_portal_name'] == 'Blog da Kelly'
