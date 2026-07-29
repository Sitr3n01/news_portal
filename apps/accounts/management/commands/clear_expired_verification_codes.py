"""Faxina de códigos de verificação (VerificationCode) velhos demais para importar.

Complementa, não substitui, a limpeza oportunista que apps.accounts.
verification.issue_code já faz a cada emissão (apaga o que tiver mais de 24h
naquele momento): aquela só roda quando alguém pede um código novo, então uma
instalação com pouco tráfego de cadastro/reset acumularia linhas por meses.
Este comando existe para rodar agendado (cron/systemd timer), independente de
tráfego — mesmo raciocínio de send_test_email.py sobre ter uma ferramenta de
manutenção fora do ciclo normal de request/response.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import VerificationCode


class Command(BaseCommand):
    help = 'Remove códigos de verificação (VerificationCode) criados há mais de --days dias.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=1,
            help='Idade mínima, em dias, para um código ser removido. Default: 1.',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Só reporta quantos códigos seriam removidos, sem apagar nada.',
        )

    def handle(self, *args, **options):
        days = options['days']
        threshold = timezone.now() - timedelta(days=days)
        queryset = VerificationCode.objects.filter(created_at__lt=threshold)

        if options['dry_run']:
            total = queryset.count()
            self.stdout.write(f'{total} código(s) seriam removidos (criados antes de {threshold:%d/%m/%Y %H:%M}).')
            return

        # queryset.delete() conta e apaga na mesma operação: pedir um .count()
        # antes correria o risco de reportar um número que já não bate mais
        # com o que de fato foi apagado, se uma linha nova nascer velha o
        # bastante bem entre as duas chamadas.
        deleted, _ = queryset.delete()
        self.stdout.write(self.style.SUCCESS(
            f'{deleted} código(s) removido(s) (criados antes de {threshold:%d/%m/%Y %H:%M}).'
        ))
