"""Prevê o resultado da conversão ArticleBlock → StreamField, sem escrever nada.

É o portão do deploy: rode contra produção DEPOIS de ``migrate_featured_images``
e ``migrate_block_media``, e ANTES do ``migrate``. Se este relatório mostrar
blocos sem destino, o ``migrate`` vai perder aquele conteúdo — a migration
``news.0021`` apaga a tabela ``news_articleblock`` de forma irreversível.

Somente leitura: nenhuma linha é criada, alterada ou apagada, nenhum arquivo é
tocado. Usa exatamente a mesma função de conversão que a migration
(``apps.news.legacy_blocks.build_stream_data``), então o que ele prevê é o que vai
acontecer.
"""

from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections

from apps.news.legacy_blocks import (
    article_block_table_exists,
    build_stream_data,
    fetch_legacy_blocks,
    group_by_article,
)

# Desfechos que significam conteúdo perdido de verdade — os que travam o deploy.
LOSSY_OUTCOMES = (
    'imagem_sem_destino_perdida',
    'embed_sem_url_perdido',
    'tipo_desconhecido_perdido',
)

# Desfechos que preservam o texto mas rebaixam o bloco (imagem/embed viram
# parágrafo de legenda). Não travam o deploy, mas você precisa saber.
DEGRADED_OUTCOMES = (
    'imagem_sem_destino_com_legenda',
    'embed_sem_url_com_legenda',
    'tipo_desconhecido_legenda',
)

OUTCOME_LABELS = {
    'texto': 'Texto (rich text) convertido',
    'texto_so_legenda': 'Texto vazio, só legenda -> parágrafo',
    'imagem': 'Imagem convertida (com Image do Wagtail)',
    'imagem_sem_destino_com_legenda': 'Imagem SEM Image -> só a legenda sobrevive',
    'imagem_sem_destino_perdida': 'Imagem SEM Image e SEM legenda -> PERDIDA',
    'embed': 'Vídeo/post convertido',
    'embed_sem_url_com_legenda': 'Embed sem URL -> só a legenda sobrevive',
    'embed_sem_url_perdido': 'Embed sem URL e sem legenda -> PERDIDO',
    'tipo_desconhecido_texto': 'Tipo desconhecido, tinha texto -> convertido',
    'tipo_desconhecido_legenda': 'Tipo desconhecido -> só a legenda sobrevive',
    'tipo_desconhecido_perdido': 'Tipo desconhecido, vazio -> PERDIDO',
    'vazio_descartado': 'Bloco totalmente vazio -> descartado (sem perda)',
}


class Command(BaseCommand):
    help = (
        'Relatório somente-leitura do que a migration news.0021 fará com os blocos '
        'legados. Rode antes do migrate.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--detalhado',
            action='store_true',
            help='Lista artigo por artigo, não só o total.',
        )

    def handle(self, *args, **options):
        from wagtail.images import get_image_model

        from apps.news.models import Article

        connection = connections[DEFAULT_DB_ALIAS]

        if not article_block_table_exists(connection):
            raise CommandError(
                'A tabela news_articleblock não existe neste banco — a migration news.0021 '
                'já rodou. Não há mais nada para auditar.'
            )

        blocks = fetch_legacy_blocks(connection)
        if not blocks:
            self.stdout.write(self.style.SUCCESS(
                'Nenhum bloco legado no banco. O migrate pode seguir sem risco de perda.'
            ))
            return

        image_pk_by_media_id = dict(
            get_image_model().objects
            .filter(legacy_media_file_id__isnull=False)
            .values_list('legacy_media_file_id', 'pk')
        )

        def image_pk_for(media_id):
            return image_pk_by_media_id.get(media_id)

        grouped = group_by_article(blocks)
        titles = dict(Article.objects.filter(pk__in=grouped).values_list('pk', 'title'))

        totals = Counter()
        problem_articles = []

        for article_id, article_blocks in sorted(grouped.items()):
            outcomes = Counter()
            stream = build_stream_data(article_blocks, image_pk_for, outcomes=outcomes)
            totals.update(outcomes)

            lossy = sum(outcomes[key] for key in LOSSY_OUTCOMES)
            degraded = sum(outcomes[key] for key in DEGRADED_OUTCOMES)
            title = titles.get(article_id, '(artigo ausente)')

            if lossy or degraded:
                problem_articles.append((article_id, title, lossy, degraded))

            if options['detalhado']:
                marker = self.style.ERROR('X') if lossy else (
                    self.style.WARNING('!') if degraded else ' '
                )
                self.stdout.write(
                    f'  {marker} #{article_id} "{title[:50]}" -- '
                    f'{len(article_blocks)} bloco(s) -> {len(stream)} no StreamField'
                )

        self._report(len(blocks), len(grouped), totals, problem_articles)

    def _report(self, block_count, article_count, totals, problem_articles):
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 68))
        self.stdout.write(self.style.SUCCESS('PREVISÃO DA CONVERSÃO ArticleBlock -> Article.body'))
        self.stdout.write(self.style.SUCCESS('=' * 68))
        self.stdout.write(f'  {block_count} bloco(s) em {article_count} artigo(s).')
        self.stdout.write('')

        for key, count in sorted(totals.items(), key=lambda item: -item[1]):
            if not count:
                continue
            label = OUTCOME_LABELS.get(key, key)
            line = f'  {count:>5}  {label}'
            if key in LOSSY_OUTCOMES:
                self.stdout.write(self.style.ERROR(line))
            elif key in DEGRADED_OUTCOMES:
                self.stdout.write(self.style.WARNING(line))
            else:
                self.stdout.write(line)

        lossy_total = sum(totals[key] for key in LOSSY_OUTCOMES)
        degraded_total = sum(totals[key] for key in DEGRADED_OUTCOMES)

        self.stdout.write('')
        if problem_articles:
            self.stdout.write('  Artigos afetados:')
            for article_id, title, lossy, degraded in problem_articles[:30]:
                detail = []
                if lossy:
                    detail.append(f'{lossy} perdido(s)')
                if degraded:
                    detail.append(f'{degraded} rebaixado(s)')
                self.stdout.write(f'    #{article_id} "{title[:45]}" -- {", ".join(detail)}')
            if len(problem_articles) > 30:
                self.stdout.write(f'    ... e mais {len(problem_articles) - 30} artigo(s).')
            self.stdout.write('')

        if lossy_total:
            self.stdout.write(self.style.ERROR(
                f'  NÃO RODE O MIGRATE: {lossy_total} bloco(s) seriam perdidos sem volta.\n'
                f'  Rode "migrate_block_media --apply" e confira os erros dele primeiro.'
            ))
        elif degraded_total:
            self.stdout.write(self.style.WARNING(
                f'  {degraded_total} bloco(s) serão rebaixados a parágrafo de legenda '
                f'(nenhum texto se perde). Se isso é aceitável, siga com o migrate.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                '  Cobertura de 100%: nenhum bloco perdido nem rebaixado. '
                'Pode rodar o migrate.'
            ))
