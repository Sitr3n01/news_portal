from django.core.management.base import BaseCommand

from apps.news.newsletter import process_pending_newsletters


class Command(BaseCommand):
    help = 'Processa newsletters pendentes do portal de notícias.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Número máximo de entregas processadas nesta execução.',
        )
        parser.add_argument(
            '--site-id',
            type=int,
            help='Processa apenas artigos de um Site específico.',
        )
        parser.add_argument(
            '--article-id',
            type=int,
            help='Processa apenas um artigo específico.',
        )
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            help='Inclui entregas com status de falha na tentativa atual.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra o que seria enfileirado/enviado sem alterar dados nem enviar e-mails.',
        )

    def handle(self, *args, **options):
        result = process_pending_newsletters(
            batch_size=options['batch_size'],
            site_id=options.get('site_id'),
            article_id=options.get('article_id'),
            retry_failed=options['retry_failed'],
            dry_run=options['dry_run'],
        )

        prefix = '[dry-run] ' if options['dry_run'] else ''
        self.stdout.write(
            self.style.SUCCESS(
                f'{prefix}Newsletter: '
                f'{result["deliveries_created"]} criada(s), '
                f'{result["deliveries_existing"]} existente(s), '
                f'{result["would_create"]} criaria, '
                f'{result["sent"]} enviada(s), '
                f'{result["would_send"]} enviaria, '
                f'{result["failed"]} falha(s), '
                f'{result["skipped"]} ignorada(s), '
                f'{result["articles_marked_sent"]} artigo(s) marcado(s) como concluído(s).'
            )
        )
