"""Camada única de envio de e-mail do projeto, com observabilidade e sem vazamento.

Fase 2 migra password_reset e newsletter para cá; por ora isto atende quem
precisar de e-mail transacional novo. Centralizar existe para garantir sempre
as mesmas três coisas, num lugar só:

1. NUNCA logar segredo. Senha, código de verificação, token (de reset ou de
   confirmação de conta) e client secret jamais entram numa chamada de logger
   deste módulo — só o endereço mascarado (`mask_email`) e metadados (motivo
   do erro, propósito do envio).
2. Falha de envio NUNCA vira exceção não tratada. Quem chama decide o que
   mostrar ao usuário (mensagem genérica, nova tentativa etc.); esta função só
   informa sucesso ou falha.
3. Backend fake (console/dummy/locmem) fora de DEBUG é logado como erro, mas
   NÃO interrompe a tentativa de envio — quem bloqueia o deploy nesse caso é o
   system check (apps/accounts/checks.py), não esta camada.
"""

import logging
import smtplib
import socket

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils import timezone

from apps.common.context_processors import NEWS_PORTAL_NAME
from apps.common.models import SiteExtension

logger = logging.getLogger('apps.email')

# Backends que devolvem sucesso sem tocar uma rede de verdade — corretos em
# dev/test, mas indistinguíveis de um SMTP quebrado quando aparecem sem querer
# em produção. Público de propósito: apps/accounts/checks.py importa desta
# lista para que o system check e o runtime concordem sobre o que é "fake".
FAKE_EMAIL_BACKENDS = {
    'django.core.mail.backends.console.EmailBackend',
    'django.core.mail.backends.dummy.EmailBackend',
    'django.core.mail.backends.locmem.EmailBackend',
}


def mask_email(value):
    """Reduz um e-mail a `j***@e***.com` para log — nunca o endereço completo.

    String vazia e valor sem '@' são entrada não confiável (formulário, outro
    sistema, campo opcional); devolver um marcador neutro em vez de estourar
    IndexError evita que logar um erro de e-mail derrube o próprio log.
    """
    if not value:
        return '(vazio)'
    if '@' not in value:
        return '***'
    local, _, domain = value.partition('@')
    local_mask = f'{local[0]}***' if local else '***'
    domain_name, dot, tld = domain.partition('.')
    domain_mask = f'{domain_name[0]}***' if domain_name else '***'
    return f'{local_mask}@{domain_mask}{dot}{tld}'


def _classify_send_exception(exc):
    """Reduz a exceção do smtplib/socket a um rótulo estável para log e métricas.

    A ordem dos isinstance() importa: SMTPException, socket.gaierror e
    TimeoutError são todos OSError por baixo, então as subclasses específicas
    do smtplib precisam ser checadas ANTES do fallback genérico de rede —
    senão tudo cairia em 'connection' e o log perderia a causa real.
    """
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return 'smtp_auth'
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return 'sender_refused'
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return 'recipients_refused'
    if isinstance(exc, (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected)):
        return 'smtp_connect'
    if isinstance(exc, TimeoutError):  # socket.timeout é alias de TimeoutError desde o Python 3.10
        return 'timeout'
    if isinstance(exc, socket.gaierror):
        return 'dns'
    if isinstance(exc, smtplib.SMTPException):
        return 'smtp'
    if isinstance(exc, (ConnectionError, OSError)):
        return 'connection'
    return 'unknown'


def get_email_backend_health():
    """Retrato do backend ativo, pronto para o comando de diagnóstico.

    Nunca inclui EMAIL_HOST_PASSWORD: este dict pode acabar num stdout ou numa
    tela de admin, e a senha do SMTP não é dado de diagnóstico.
    """
    backend = settings.EMAIL_BACKEND
    return {
        'backend': backend,
        'is_real_smtp': backend not in FAKE_EMAIL_BACKENDS,
        'host': settings.EMAIL_HOST,
        'port': settings.EMAIL_PORT,
        'use_tls': settings.EMAIL_USE_TLS,
        'use_ssl': settings.EMAIL_USE_SSL,
        'from_email': settings.DEFAULT_FROM_EMAIL,
    }


def send_branded_email(*, to, subject_template, text_template, html_template, context, purpose, from_email=None):
    """Renderiza os três templates e envia; nunca levanta, sempre devolve bool.

    `purpose` identifica o fluxo no log (ex.: 'password_reset', 'newsletter')
    sem carregar dado nenhum do usuário — é o que permite localizar
    EMAIL_SEND_FAILED por tipo de envio sem precisar abrir o corpo da mensagem.
    """
    recipients = [to] if isinstance(to, str) else list(to)
    masked_to = ','.join(mask_email(address) for address in recipients)

    health = get_email_backend_health()
    if not settings.DEBUG and not health['is_real_smtp']:
        # Aviso, não abort: um ambiente mal configurado ainda deve tentar
        # enviar (e falhar de um jeito visível nos logs) em vez de fingir que
        # o e-mail saiu.
        logger.error('EMAIL_BACKEND_NOT_CONFIGURED purpose=%s backend=%s', purpose, health['backend'])

    # Um loop, e não três chamadas soltas, para o log de erro apontar
    # exatamente qual dos três templates falhou.
    templates = {'subject': subject_template, 'text': text_template, 'html': html_template}
    rendered = {}
    for field, template_name in templates.items():
        try:
            rendered[field] = render_to_string(template_name, context)
        except (TemplateDoesNotExist, TemplateSyntaxError) as exc:
            logger.error('EMAIL_TEMPLATE_ERROR purpose=%s template=%s detail=%s', purpose, template_name, exc)
            return False

    # Quebra de linha no Subject é vetor clássico de header injection (forjaria
    # Bcc/Cc/X-Mailer extras) — vira uma linha só antes de qualquer coisa
    # tocar o e-mail de verdade.
    subject = ''.join(rendered['subject'].splitlines()).strip()

    message = EmailMultiAlternatives(
        subject=subject,
        body=rendered['text'],
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    message.attach_alternative(rendered['html'], 'text/html')

    try:
        message.send(fail_silently=False)
    except Exception as exc:
        reason = _classify_send_exception(exc)
        logger.error('EMAIL_SEND_FAILED purpose=%s to=%s reason=%s detail=%s', purpose, masked_to, reason, exc)
        return False

    logger.info('EMAIL_SENT purpose=%s to=%s', purpose, masked_to)
    return True


def build_email_context(extra=None):
    """Contexto mínimo que TODO e-mail da marca precisa, montado à mão.

    send_branded_email chama render_to_string, que renderiza com um Context
    solto — SEM passar por request nenhuma. Os context processors (incluindo
    apps.common.context_processors.site_context, de onde template comum tira
    `news_portal_name` e `site_settings`) só rodam quando o Django monta o
    contexto de uma view a partir de uma request; fora desse caminho eles
    simplesmente não executam. Um e-mail que contasse com `{{ news_portal_name }}`
    vindo do processor sairia da caixa de entrada com a marca em branco — e
    seria um bug invisível em `runserver`/teste (que raramente renderizam
    e-mail fora de uma view) e só apareceria na mensagem real. Por isso esta
    função monta manualmente, aqui, as mesmas chaves que o processor
    injetaria numa página comum, para qualquer chamador de send_branded_email
    poder confiar nelas sem depender de request.
    """
    site_settings = None
    # 'https://' é o padrão em produção; só cai para 'http://' quando DEBUG=True
    # (dev local, sem TLS configurado) — mesmo critério que outros lugares do
    # projeto usam para decidir se a URL absoluta deve ser http ou https.
    scheme = 'http' if settings.DEBUG else 'https'
    base_url = ''  # fallback inerte: só fica vazio se nem houver Site configurado (ver except abaixo)

    try:
        site = Site.objects.get_current()
    except Site.DoesNotExist:
        # SITE_ID aponta para uma linha que não existe — instalação mal
        # configurada, não motivo para o envio de e-mail inteiro estourar.
        # base_url some (fica '') e site_settings continua None; o template
        # só usa os dois para montar a URL do logo, que já tem fallback de
        # wordmark em texto.
        site = None

    if site is not None:
        base_url = f'{scheme}://{site.domain}'
        try:
            site_settings = site.extension
        except SiteExtension.DoesNotExist:
            # SiteExtension é OneToOne opcional: site recém-criado (ou de
            # teste) legitimamente pode não ter um ainda.
            site_settings = None

    context = {
        'news_portal_name': NEWS_PORTAL_NAME,
        'current_year': timezone.now().year,
        'site_settings': site_settings,
        'base_url': base_url,
    }
    if extra:
        context.update(extra)
    return context
