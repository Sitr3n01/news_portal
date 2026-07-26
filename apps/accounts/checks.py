"""System check que impede o backend de e-mail fake de vazar para produção sem aviso.

`manage.py check` roda sozinho antes de `runserver`/`migrate` e no entrypoint
do container — é o ponto mais cedo possível para gritar "seus e-mails vão
para lugar nenhum" antes que alguém descubra isso pela reclamação de um leitor
que nunca recebeu o link de recuperação de senha (ver o bug que originou esta
Fase 0: EMAIL_BACKEND sem SMTP em produção cai em console.EmailBackend, sem
exceção nenhuma).
"""

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register

# Uma lista só, definida no mailer: se as duas divergirem, o check aprova um
# backend que o mailer considera fake (ou vice-versa) e o alarme fica mentindo.
from apps.accounts.mailer import FAKE_EMAIL_BACKENDS

_DEV_DEFAULT_FROM_EMAIL = 'noreply@localhost'


@register(Tags.security)
def check_email_backend(app_configs, **kwargs):
    """Recusa (Error) backend fake fora de DEBUG; avisa (Warning) SMTP incompleto.

    config/settings/test.py roda com DEBUG=False e locmem de propósito (rápido,
    isolado, sem rede) — sem uma saída explícita, a suíte inteira reportaria
    accounts.E001 e o CI nunca ficaria verde. Em vez de adivinhar "isto é
    teste?" por heurística (sys.argv, sufixo do nome do settings module —
    frágil sob outros test runners, sob gunicorn, sob `manage.py shell`), o
    próprio settings de teste declara a intenção com EMAIL_CHECK_SKIP = True:
    mais honesto do que inferir.
    """
    if getattr(settings, 'EMAIL_CHECK_SKIP', False):
        return []

    issues = []
    backend = settings.EMAIL_BACKEND
    is_fake_backend = backend in FAKE_EMAIL_BACKENDS

    if not settings.DEBUG and is_fake_backend:
        issues.append(
            Error(
                'EMAIL_BACKEND não é SMTP fora de DEBUG: e-mails de recuperação de senha e '
                'confirmação serão descartados silenciosamente.',
                hint=(
                    'Defina EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend no .env.prod '
                    '(veja o bloco de e-mail em .env.prod.example).'
                ),
                id='accounts.E001',
            )
        )

    # `not DEBUG` também aqui: em desenvolvimento o SMTP apontado é o Mailpit do
    # compose, que por definição não pede credencial. Sem esta condição, todo
    # `runserver`/`migrate` local cospe um W001 falso — e alarme que sempre toca
    # é alarme que ninguém lê no dia em que o de produção tocar.
    if not settings.DEBUG and not is_fake_backend and (not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD):
        issues.append(
            Warning(
                'EMAIL_HOST_USER ou EMAIL_HOST_PASSWORD está vazio com um backend SMTP configurado.',
                hint='Preencha as duas variáveis no .env correspondente — a maioria dos provedores SMTP recusa conexão anônima.',
                id='accounts.W001',
            )
        )

    if not settings.DEBUG and settings.DEFAULT_FROM_EMAIL == _DEV_DEFAULT_FROM_EMAIL:
        issues.append(
            Warning(
                'DEFAULT_FROM_EMAIL continua no valor padrão de desenvolvimento (noreply@localhost).',
                hint='Defina DEFAULT_FROM_EMAIL com um remetente real do domínio em produção.',
                id='accounts.W002',
            )
        )

    return issues
