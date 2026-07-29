"""E-mails transacionais de alto nível: confirmação de cadastro e recuperação de senha.

Cada função aqui é a fronteira entre "um código foi emitido"
(apps.accounts.verification.issue_code, que devolve o texto puro) e "o
e-mail com esse código foi enviado" (apps.accounts.mailer.send_branded_email).
Os dois módulos propositalmente não se conhecem — verification.py não sabe
nada de e-mail, mailer.py não sabe nada de código de verificação — e este
arquivo é o único lugar que amarra os dois, para o texto puro do código
percorrer o menor caminho possível entre "gerado" e "enviado".
"""

from django.conf import settings

from apps.accounts.mailer import build_email_context, send_branded_email


def send_verification_code_email(user, code, request=None):
    """Envia o e-mail de confirmação de cadastro com `code` em destaque.

    `code` (texto puro, vindo de verification.issue_code) entra SÓ no
    contexto do template — de onde vai para o corpo renderizado da mensagem
    e para lugar nenhum mais. send_branded_email loga apenas `purpose` e o
    destinatário mascarado (mask_email); nunca recebe nem loga o `context`
    inteiro, então o código não tem como vazar por aqui para um log.

    `request=None` não é usado hoje (build_email_context sempre tira o site
    de Site.objects.get_current(), nunca da request) — o parâmetro existe
    para a assinatura ficar simétrica a issue_code/check_code em
    verification.py, e para não ser uma mudança incompatível no dia em que
    este envio precisar de algo derivado da request (IP para telemetria, por
    exemplo).
    """
    context = build_email_context({
        'code': code,
        'expires_in_minutes': settings.VERIFICATION_CODE_TTL // 60,
    })
    return send_branded_email(
        to=user.email,
        subject_template='emails/verification_code_subject.txt',
        text_template='emails/verification_code.txt',
        html_template='emails/verification_code.html',
        context=context,
        purpose='email_verification',
    )


def send_password_reset_code_email(user, code, request=None):
    """Envia o e-mail de recuperação de senha com `code` em destaque.

    Mesmo contrato de send_verification_code_email — ver a docstring lá para
    o porquê do código nunca sair do contexto do template e do `request` não
    ser usado hoje.
    """
    context = build_email_context({
        'code': code,
        'expires_in_minutes': settings.VERIFICATION_CODE_TTL // 60,
    })
    return send_branded_email(
        to=user.email,
        subject_template='emails/password_reset_code_subject.txt',
        text_template='emails/password_reset_code.txt',
        html_template='emails/password_reset_code.html',
        context=context,
        purpose='password_reset',
    )
