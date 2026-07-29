"""Cria Image (Wagtail) a partir de Article.featured_image (Fase 9 — ponte de capa).

Dry-run por padrão (nenhum flag) — não grava nada, nem no banco nem no disco.
Com --apply, persiste as alterações.

Cuidado ao mexer: em dry-run o comando NÃO pode chamar
`bridge.create_wagtail_image`. `ContentFile` grava o arquivo no MEDIA_ROOT, e o
`savepoint_rollback` no fim de handle() desfaz só o banco — cada dry-run deixava
uma cópia órfã do arquivo para trás.

Idempotente: artigos que já têm `featured_image_wagtail` preenchido são ignorados.
O campo `featured_image` original nunca é modificado — apenas lido como fonte.

Ordem no deploy (ver docs/technical/DEPLOY.md): este comando primeiro, depois
`migrate_block_media`, depois `audit_article_blocks`, e só então o `migrate`.
"""

import logging
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.cms_media.bridge import create_wagtail_image, image_dimensions, read_source_bytes
from apps.news.models import Article

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cria Image (Wagtail) a partir de Article.featured_image (dry-run por padrão).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Persiste as alterações no banco (sem --apply, nada é gravado).',
        )
        parser.add_argument(
            '--article-id',
            type=int,
            help='Processa apenas este artigo (útil para verificação pontual).',
        )

    def handle(self, *args, **options):
        apply_mode = options['apply']
        article_id = options.get('article_id')
        prefix = '' if apply_mode else '[dry-run] '

        # ── snapshot pré-execução ─────────────────────────────────────────
        article_count_before = Article.objects.count()
        from wagtail.images import get_image_model
        image_model = get_image_model()
        image_count_before = image_model.objects.count()
        self.stdout.write(
            f'{prefix}Snapshot inicial: {article_count_before} artigos, '
            f'{image_count_before} imagens Wagtail.'
        )

        # ── executar em transação ─────────────────────────────────────────
        with transaction.atomic():
            sid = transaction.savepoint()
            stats = self._run(apply_mode=apply_mode, article_id=article_id, prefix=prefix)

            if not apply_mode:
                transaction.savepoint_rollback(sid)
            else:
                transaction.savepoint_commit(sid)

        # ── Relatório final ───────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'{prefix}RESUMO FINAL'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'  Artigos encontrados (com featured_image):  {stats["total_found"]}')
        if apply_mode:
            self.stdout.write(f'  Convertidos (Wagtail Image criado):        {stats["total_converted"]}')
        else:
            self.stdout.write(f'  Seriam convertidos:                       {stats["total_would_convert"]}')
        self.stdout.write(f'  Ignorados (já tinham featured_image_wagtail): {stats["total_skipped"]}')
        self.stdout.write(f'  Erros:                                     {stats["total_errors"]}')

        # ── Snapshot pós-execução ─────────────────────────────────────────
        article_count_after = Article.objects.count()
        image_count_after = image_model.objects.count()
        self.stdout.write('')
        self.stdout.write(
            f'  Snapshot final: {article_count_after} artigos, '
            f'{image_count_after} imagens Wagtail.'
        )
        if article_count_before != article_count_after:
            self.stdout.write(self.style.WARNING(
                '  !! A contagem de artigos mudou! (esperado: identica)'
            ))

        if not apply_mode and image_count_before != image_count_after:
            self.stdout.write(self.style.WARNING(
                '  !! A contagem de imagens Wagtail mudou! (esperado: identica em dry-run)'
            ))

    # ── Core logic ────────────────────────────────────────────────────────

    def _run(self, *, apply_mode, article_id, prefix):
        stats = Counter({
            'total_found': 0,
            'total_converted': 0,
            'total_would_convert': 0,
            'total_skipped': 0,
            'total_errors': 0,
        })

        articles_qs = Article.objects.filter(
            featured_image__isnull=False,
        ).exclude(featured_image='').order_by('pk')

        if article_id is not None:
            articles_qs = articles_qs.filter(pk=article_id)

        articles = list(articles_qs)
        for article in articles:
            stats['total_found'] += 1

            # Idempotência: pula se já tem featured_image_wagtail
            if article.featured_image_wagtail_id is not None:
                stats['total_skipped'] += 1
                self.stdout.write(
                    f'  {prefix}PULADO #{article.pk} "{article.slug}" -- '
                    f'featured_image_wagtail já preenchido (Image pk={article.featured_image_wagtail_id}).'
                )
                continue

            # Tenta ler o arquivo existente
            content, original_name, error = read_source_bytes(article.featured_image)
            if error == 'arquivo vazio (0 bytes)':
                stats['total_skipped'] += 1
                self.stdout.write(
                    f'  {prefix}PULADO #{article.pk} "{article.slug}" -- '
                    f'featured_image está vazio (0 bytes).'
                )
                continue
            if error:
                stats['total_errors'] += 1
                self.stdout.write(self.style.ERROR(
                    f'  {prefix}ERRO #{article.pk} "{article.slug}" -- '
                    f'não foi possível ler o arquivo: {error}'
                ))
                continue

            if not apply_mode:
                # NÃO criar a Image em dry-run: ContentFile grava o arquivo no
                # MEDIA_ROOT, e o savepoint_rollback lá em handle() desfaz apenas o
                # banco — o arquivo ficava órfão, e cada dry-run deixava mais uma
                # cópia. Aqui só relatamos o que seria criado.
                width, height = image_dimensions(content)
                stats['total_would_convert'] += 1
                self.stdout.write(
                    f'  o #{article.pk} "{article.slug}" '
                    f'-> criaria Image ({width}×{height}, {len(content)} bytes)'
                )
                continue

            try:
                image = create_wagtail_image(
                    content=content,
                    filename=original_name,
                    title=article.title,
                )
            except Exception as exc:
                stats['total_errors'] += 1
                self.stdout.write(self.style.ERROR(
                    f'  {prefix}ERRO #{article.pk} "{article.slug}" -- '
                    f'falha ao criar Image: {exc}'
                ))
                continue

            article.featured_image_wagtail = image
            article.save(update_fields=['featured_image_wagtail'])
            stats['total_converted'] += 1

            self.stdout.write(
                f'  > #{article.pk} "{article.slug}" '
                f'-> Image pk={image.pk} ({image.width}×{image.height})'
            )

        return stats
