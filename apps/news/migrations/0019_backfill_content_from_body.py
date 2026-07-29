# Migration 0019 — backfill Article.content a partir de body (StreamField)
#
# Contexto (Fase 10): antes de removermos `ArticleBlock`, garantimos que
# todo artigo com `body` populado tenha seu `content` atualizado diretamente
# do StreamField. A lógica de extração é uma duplicata inline de
# Article._extract_content_from_body(), importada aqui dentro de `apps.get_model`
# para seguir as boas práticas de migração (não importar métodos de modelo vivo).
#
# Idempotente: reexecutar esta migração é seguro — apenas reescreve o mesmo
# valor.

from django.db import migrations
from django.utils.html import escape


def _extract_content_from_body_blocks(body):
    """Walk StreamField blocks, same logic as Article._extract_content_from_body()."""
    if not body:
        return ''
    parts = []
    for block in body:
        if block.block_type == 'texto':
            html = str(block.value) if block.value else ''
            if html:
                parts.append(html)
        elif isinstance(block.value, dict) and block.value.get('legenda', '').strip():
            parts.append(f'<p>{escape(block.value["legenda"].strip())}</p>')
    return '\n'.join(parts)


def backfill_content(apps, schema_editor):
    Article = apps.get_model('news', 'Article')
    from apps.common.sanitization import sanitize_content

    updated = 0
    for article in Article.objects.iterator():
        raw = _extract_content_from_body_blocks(article.body)
        if not raw:
            # NUNCA sobrescrever `content` com vazio. Esta guarda foi acrescentada
            # depois de a versão original desta migration apagar o `content` de
            # todos os artigos legados em produção.
            #
            # O filtro que existia aqui era
            # `.exclude(body__exact='').exclude(body__isnull=True)`, na suposição
            # de que artigo sem body ficaria de fora. Não fica: quando a `0015`
            # adicionou a coluna `body` (JSON, null=True, sem default), o Django
            # gravou `json.dumps(None)` nas linhas existentes — ou seja, o valor
            # JSON `null`, que NÃO é SQL NULL. `body IS NULL` dá falso, o artigo
            # entra no laço, a extração devolve '' e o `content` era zerado.
            #
            # Armadilha geral, não específica desta migration: ao adicionar coluna
            # JSON/StreamField anulável, as linhas antigas recebem JSON `null` e
            # `__isnull=True` não as encontra. Teste a veracidade do valor
            # (`if not campo`), não `__isnull`.
            continue

        content = sanitize_content(raw)
        if content != article.content:
            Article.objects.filter(pk=article.pk).update(content=content)
            updated += 1

    # This is informational only; Django doesn't show stdout in migrations.
    # We leave it so that squashing or manual inspection can confirm the run.
    if updated:
        pass  # placeholder — log via print if needed during manual runs


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0018_article_featured_image_wagtail'),
    ]

    operations = [
        migrations.RunPython(backfill_content, reverse_code=noop),
    ]
