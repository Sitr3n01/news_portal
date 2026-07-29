"""Ferramenta de diagnóstico para validar SMTP no ambiente atual, fora do shell.

Não usa apps.accounts.mailer.send_branded_email: a Fase 0 ainda não tem
templates de e-mail (isso é Fase 2), então o corpo é montado direto aqui, sem
depender de nada em templates/emails/.
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.mailer import get_email_backend_health, mask_email


class Command(BaseCommand):
    help = 'Envia um e-mail de teste para validar EMAIL_BACKEND/SMTP do ambiente atual.'

    def add_arguments(self, parser):
        parser.add_argument('destinatario', help='Endereço que vai receber o e-mail de teste.')
        parser.add_argument(
            '--fail-loud',
            action='store_true',
            help='Relevanta a exceção original (com traceback) em vez de só reportar o erro.',
        )

    def handle(self, *args, **options):
        destinatario = options['destinatario']
        health = get_email_backend_health()

        # Diagnóstico ANTES do envio: se o problema for de configuração (host
        # errado, TLS/SSL invertidos), o operador já vê a causa sem precisar
        # decifrar o traceback do smtplib.
        self.stdout.write('── Configuração de e-mail ──')
        self.stdout.write(f'EMAIL_BACKEND: {health["backend"]}')
        self.stdout.write(f'EMAIL_HOST: {settings.EMAIL_HOST}')
        self.stdout.write(f'EMAIL_PORT: {settings.EMAIL_PORT}')
        self.stdout.write(f'EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}')
        self.stdout.write(f'EMAIL_TIMEOUT: {settings.EMAIL_TIMEOUT}')
        self.stdout.write(f'DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}')
        # Nunca o valor da senha — só se a variável foi preenchida.
        senha_status = '(definida)' if settings.EMAIL_HOST_PASSWORD else '(vazia)'
        self.stdout.write(f'EMAIL_HOST_PASSWORD: {senha_status}')
        self.stdout.write('')

        text_body = (
            'Este é um e-mail de teste do News Portal.\n\n'
            'Se você recebeu esta mensagem, a configuração de SMTP está funcionando.'
        )
        html_body = (
            '<p>Este é um e-mail de teste do <strong>News Portal</strong>.</p>'
            '<p>Se você recebeu esta mensagem, a configuração de SMTP está funcionando.</p>'
        )

        message = EmailMultiAlternatives(
            subject='Teste de configuração de e-mail — News Portal',
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        message.attach_alternative(html_body, 'text/html')

        try:
            message.send(fail_silently=False)
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'{type(exc).__name__}: {exc}'))
            if options['fail_loud']:
                raise
            raise CommandError(f'Falha ao enviar e-mail de teste para {mask_email(destinatario)}.') from exc

        self.stdout.write(self.style.SUCCESS(f'E-mail de teste enviado para {destinatario}.'))
        if not health['is_real_smtp']:
            self.stdout.write(self.style.WARNING(
                f'Backend atual é {health["backend"]}: o e-mail foi impresso no terminal e NÃO enviado de verdade.'
            ))
