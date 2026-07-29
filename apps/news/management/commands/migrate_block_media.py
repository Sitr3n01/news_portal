"""Cria ``cms_media.Image`` a partir das ``MediaFile`` usadas nos blocos de imagem.

É o passo que faltava da ponte de mídia: ``cms_media.Image.legacy_media_file_id``
existe no modelo desde o começo e nunca foi escrito por ninguém, então a conversão
de ``ArticleBlock`` para o StreamField (migration ``news.0021``) não tinha como
descobrir qual Image corresponde a qual MediaFile — e toda imagem inline dos
artigos existentes se perderia no deploy.

**Rode ANTES do ``migrate``.** Depois dele a tabela ``news_articleblock`` já não
existe e não há mais o que converter. A ordem completa está em
``docs/technical/DEPLOY.md``.

Dry-run por padrão: nada é gravado no banco NEM no disco. Com ``--apply``,
persiste.

Idempotente: ``MediaFile`` que já tem ``Image`` com o mesmo
``legacy_media_file_id`` é ignorada, então rodar duas vezes não duplica imagem.
"""

from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections, transaction

from apps.cms_media.bridge import create_wagtail_image, image_dimensions, read_source_bytes
from apps.news.legacy_blocks import article_block_table_exists, referenced_media_ids


class Command(BaseCommand):
    help = (
        'Cria cms_media.Image para cada MediaFile usada em bloco de imagem de artigo '
        '(dry-run por padrão). Rode antes do migrate.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Persiste as alterações (sem --apply, nada é gravado no banco nem no disco).',
        )

    def handle(self, *args, **options):
        from wagtail.images import get_image_model

        from apps.media_library.models import MediaFile

        apply_mode = options['apply']
        prefix = '' if apply_mode else '[dry-run] '
        connection = connections[DEFAULT_DB_ALIAS]
        image_model = get_image_model()

        if not article_block_table_exists(connection):
            raise CommandError(
                'A tabela news_articleblock não existe neste banco — a migration news.0021 '
                'já rodou. Este comando precisa rodar ANTES do migrate; depois dele não há '
                'mais blocos legados para converter.'
            )

        media_ids = referenced_media_ids(connection)
        self.stdout.write(
            f'{prefix}{len(media_ids)} MediaFile referenciada(s) por blocos de imagem. '
            f'{image_model.objects.count()} imagens Wagtail no banco.'
        )
        if not media_ids:
            self.stdout.write(self.style.SUCCESS(
                'Nenhum bloco de imagem para converter — o migrate pode seguir.'
            ))
            return

        already = dict(
            image_model.objects
            .filter(legacy_media_file_id__in=media_ids)
            .values_list('legacy_media_file_id', 'pk')
        )
        media_by_id = MediaFile.objects.in_bulk(media_ids)

        stats = Counter()
        with transaction.atomic():
            for media_id in media_ids:
                if media_id in already:
                    stats['ja_convertida'] += 1
                    self.stdout.write(
                        f'  {prefix}PULADO MediaFile #{media_id} -- já existe Image '
                        f'pk={already[media_id]}.'
                    )
                    continue

                media = media_by_id.get(media_id)
                if media is None:
                    # FK órfã: o bloco aponta para uma MediaFile apagada. A migration
                    # 0021 vai cair no fallback de legenda para esse bloco.
                    stats['mediafile_ausente'] += 1
                    self.stdout.write(self.style.WARNING(
                        f'  {prefix}AUSENTE MediaFile #{media_id} -- referenciada por bloco '
                        f'mas não existe mais; o bloco vai virar parágrafo de legenda.'
                    ))
                    continue

                content, filename, error = read_source_bytes(media.file)
                if error:
                    stats['erro_leitura'] += 1
                    self.stdout.write(self.style.ERROR(
                        f'  {prefix}ERRO MediaFile #{media_id} "{media.title}" -- {error}'
                    ))
                    continue

                if not apply_mode:
                    # Em dry-run NÃO criamos a Image: ContentFile gravaria o arquivo no
                    # MEDIA_ROOT e rollback de transação não desfaz escrita em disco.
                    width, height = image_dimensions(content)
                    stats['a_converter'] += 1
                    self.stdout.write(
                        f'  o MediaFile #{media_id} "{media.title}" -> criaria Image '
                        f'({width}×{height}, {len(content)} bytes)'
                    )
                    continue

                try:
                    image = create_wagtail_image(
                        content=content,
                        filename=filename,
                        title=media.title,
                        description=media.alt_text,
                        legacy_media_file_id=media.pk,
                    )
                except Exception as exc:
                    stats['erro_criacao'] += 1
                    self.stdout.write(self.style.ERROR(
                        f'  ERRO MediaFile #{media_id} "{media.title}" -- '
                        f'falha ao criar Image: {exc}'
                    ))
                    continue

                stats['convertida'] += 1
                self.stdout.write(
                    f'  > MediaFile #{media_id} "{media.title}" -> Image pk={image.pk} '
                    f'({image.width}×{image.height})'
                )

        self._report(prefix, stats, len(media_ids), apply_mode)

    def _report(self, prefix, stats, total, apply_mode):
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'{prefix}RESUMO'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'  MediaFile referenciadas por blocos:  {total}')
        if apply_mode:
            self.stdout.write(f'  Convertidas (Image criada):          {stats["convertida"]}')
        else:
            self.stdout.write(f'  Seriam convertidas:                  {stats["a_converter"]}')
        self.stdout.write(f'  Já convertidas antes (ignoradas):    {stats["ja_convertida"]}')
        self.stdout.write(f'  MediaFile ausente (FK órfã):         {stats["mediafile_ausente"]}')
        self.stdout.write(f'  Erros de leitura de arquivo:         {stats["erro_leitura"]}')
        if apply_mode:
            self.stdout.write(f'  Erros ao criar Image:                {stats["erro_criacao"]}')

        pendentes = stats['mediafile_ausente'] + stats['erro_leitura'] + stats['erro_criacao']
        self.stdout.write('')
        if pendentes:
            self.stdout.write(self.style.WARNING(
                f'  !! {pendentes} imagem(ns) NÃO terão destino no StreamField. Rode '
                f'audit_article_blocks para ver quais artigos são afetados antes do migrate.'
            ))
        elif apply_mode:
            self.stdout.write(self.style.SUCCESS(
                '  Todas as imagens de bloco têm destino. Rode audit_article_blocks '
                'para conferir e siga com o migrate.'
            ))
        else:
            self.stdout.write(
                '  Nada foi gravado. Repita com --apply para persistir.'
            )
