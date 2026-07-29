"""Alinha o estado de publicação do Wagtail (`live`) com o campo `status`.

A `0015` adicionou `live` com `default=True`, o que marcou como "ao vivo" TODA
linha existente — inclusive artigos com `status='draft'` ou `'archived'`. O
resultado é uma tela contraditória: no `/cms/` a matéria aparece publicada,
enquanto no site público ela está escondida (as views filtram por `status`, não
por `live` — ver `apps/news/views.py`).

Pior, o desalinhamento também trava a correção pela interface: o receiver
`sync_article_status_on_wagtail_unpublish` só age quando `status == PUBLISHED`,
então "Retirar do ar" num rascunho marcado como live apagava o `live` e deixava o
`status` como estava, sem sincronizar nada.

`status` é a fonte de verdade porque é ele que decide a visibilidade pública.

Idempotente: reexecutar reescreve o mesmo valor.
"""

from django.db import migrations


def align_draft_state(apps, schema_editor):
    Article = apps.get_model('news', 'Article')
    db_alias = schema_editor.connection.alias
    base = Article.objects.using(db_alias)

    # Publicado: live, e com as datas do Wagtail preenchidas a partir de
    # published_at para o painel não mostrar "nunca publicado".
    for article in base.filter(status='published').iterator():
        updates = {}
        if not article.live:
            updates['live'] = True
        if article.first_published_at is None and article.published_at is not None:
            updates['first_published_at'] = article.published_at
        if article.last_published_at is None and article.published_at is not None:
            updates['last_published_at'] = article.published_at
        if updates:
            base.filter(pk=article.pk).update(**updates)

    # Rascunho e arquivado não estão no ar: live=False. `has_unpublished_changes`
    # fica False porque não existe revisão publicada da qual eles divirjam — a
    # 0015 nunca criou revisão nenhuma para o acervo legado.
    base.filter(status__in=('draft', 'archived'), live=True).update(
        live=False,
        has_unpublished_changes=False,
    )


def noop(apps, schema_editor):
    """Sem volta: o estado anterior (tudo live=True) era justamente o defeito."""


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0024_rebuild_content_from_body'),
    ]

    operations = [
        migrations.RunPython(align_draft_state, noop),
    ]
