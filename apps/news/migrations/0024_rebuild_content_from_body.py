"""Reconstrói Article.content a partir do body com o extrator completo.

Dois motivos para existir:

1. A `0019` rodou com um extrator que só colhia blocos `texto` e legendas —
   título, citação, box de destaque, fonte e tabela ficavam de fora, e portanto
   invisíveis para a busca do portal (`content__icontains` em
   `apps.news.views.article_search`).
2. A `0021` acabou de converter os blocos legados para `body`. O `content` desses
   artigos ainda é o texto consolidado do modelo antigo; reconstruir aqui alinha
   os dois.

REGRA DE SEGURANÇA: só sobrescreve `content` quando a extração render conteúdo.
Se a conversão da 0021 tiver falhado para algum artigo, `body` está vazio, a
extração devolve '' e o `content` legado — que é o que mantém a matéria no ar via
o fallback de `templates/news/article_detail.html` — fica intocado. Sem essa
guarda, uma conversão parcial viraria apagamento de conteúdo publicado.

Idempotente: reexecutar reescreve o mesmo valor.
"""

from django.db import migrations

from apps.common.sanitization import sanitize_content
from apps.news.content_extraction import extract_content_from_body


def rebuild_content(apps, schema_editor):
    Article = apps.get_model('news', 'Article')
    db_alias = schema_editor.connection.alias

    for article in Article.objects.using(db_alias).exclude(body__isnull=True).iterator():
        extracted = extract_content_from_body(article.body)
        if not extracted:
            # Ver REGRA DE SEGURANÇA no docstring: nada extraído, nada apagado.
            continue

        content = sanitize_content(extracted)
        if content != article.content:
            Article.objects.using(db_alias).filter(pk=article.pk).update(content=content)


def noop(apps, schema_editor):
    """Sem volta: o `content` anterior não é recuperável, e o valor novo é um
    superconjunto do antigo — reverter só pioraria a busca."""


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0023_remove_default_wagtail_page'),
    ]

    operations = [
        migrations.RunPython(rebuild_content, noop),
    ]
