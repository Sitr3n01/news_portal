"""Consultas editoriais de artigos, compartilhadas pelos painéis administrativos.

Fonte única para "quantas publicadas / rascunhos / em revisão / agendadas" e
para o estado editorial de cada artigo. Antes a contagem morava só no dashboard
do Wagtail (apps/news/wagtail_hooks.py); agora a visão geral unificada
(apps/common/newsroom) e a navegação usam as mesmas regras.

Nenhuma função aqui altera artigo. Publicar, despublicar, revisar e agendar
continuam sendo feitos pelos fluxos nativos do Wagtail (DraftStateMixin,
WorkflowMixin), sincronizados com ``status`` por apps/news/signals.py.
"""

from django.contrib.contenttypes.models import ContentType
from django.db.models import BigIntegerField, Q
from django.db.models.functions import Cast
from wagtail.models import Revision, WorkflowState

from apps.news.models import Article

STATE_PUBLISHED = 'published'
STATE_DRAFT = 'draft'
STATE_REVIEW = 'review'
STATE_SCHEDULED = 'scheduled'
STATE_ARCHIVED = 'archived'

STATE_LABELS = {
    STATE_PUBLISHED: 'Publicada',
    STATE_DRAFT: 'Rascunho',
    STATE_REVIEW: 'Em revisão',
    STATE_SCHEDULED: 'Agendada',
    STATE_ARCHIVED: 'Arquivada',
}

# Filtros oferecidos na listagem, na ordem das abas.
FILTER_ALL = 'all'
FILTERS = (
    (FILTER_ALL, 'Todas'),
    (STATE_PUBLISHED, 'Publicadas'),
    (STATE_DRAFT, 'Rascunhos'),
    (STATE_REVIEW, 'Em revisão'),
    (STATE_SCHEDULED, 'Agendadas'),
    (STATE_ARCHIVED, 'Arquivadas'),
)
FILTER_KEYS = {key for key, _label in FILTERS}


def article_content_type():
    return ContentType.objects.get_for_model(Article, for_concrete_model=False)


def _active_workflow_states():
    return WorkflowState.objects.active().filter(base_content_type=article_content_type())


def in_review_article_pks():
    """Subquery de PKs (inteiros) de artigos com fluxo de revisão ativo.

    ``WorkflowState.object_id`` é texto (serve a qualquer modelo); o Cast evita
    comparar bigint com varchar, que o PostgreSQL recusa.
    """
    return _active_workflow_states().annotate(
        article_pk=Cast('object_id', output_field=BigIntegerField()),
    ).values('article_pk')


def in_review_ids(article_pks):
    """Conjunto de PKs (como texto) em revisão entre os artigos informados."""
    if not article_pks:
        return set()
    return set(
        _active_workflow_states()
        .filter(object_id__in=[str(pk) for pk in article_pks])
        .values_list('object_id', flat=True)
    )


def _scheduled_revisions():
    """Revisões aprovadas para entrar no ar numa data: é isso que agenda no
    Wagtail ("Agendar publicação"), e o ``publish_scheduled`` as publica na
    hora marcada. Só preencher a data no formulário (``go_live_at``) e salvar
    o rascunho NÃO agenda nada."""
    return Revision.objects.filter(base_content_type=article_content_type(), approved_go_live_at__isnull=False)


def scheduled_article_pks():
    """Subquery de PKs (inteiros) de artigos com uma revisão agendada."""
    return _scheduled_revisions().annotate(
        article_pk=Cast('object_id', output_field=BigIntegerField()),
    ).values('article_pk')


def scheduled_ids(article_pks):
    """Conjunto de PKs (como texto) com revisão agendada entre os artigos informados."""
    if not article_pks:
        return set()
    return set(
        _scheduled_revisions()
        .filter(object_id__in=[str(pk) for pk in article_pks])
        .values_list('object_id', flat=True)
    )


def scheduled_q():
    """Agendada = ainda não está no ar e tem uma revisão agendada no Wagtail."""
    return Q(live=False, pk__in=scheduled_article_pks())


def in_review_count():
    return _active_workflow_states().count()


def article_status_counts():
    return {
        'published': Article.objects.filter(status=Article.Status.PUBLISHED).count(),
        'draft': Article.objects.filter(status=Article.Status.DRAFT).exclude(scheduled_q()).count(),
        'in_review': in_review_count(),
        'scheduled': Article.objects.filter(scheduled_q()).count(),
    }


def filter_articles(queryset, state):
    """Aplica o filtro de aba. Filtros desconhecidos equivalem a "Todas".

    "Rascunhos" inclui os rascunhos em revisão — continuam sendo rascunhos, e é
    a mesma regra da contagem acima —, mas não os agendados: esses ficam com
    ``status`` de rascunho até entrar no ar (apps/news/signals.py) e têm a aba
    própria. O selo de cada linha mostra o estado mais específico (ver
    ``editorial_state``).
    """
    if state == STATE_PUBLISHED:
        return queryset.filter(status=Article.Status.PUBLISHED)
    if state == STATE_DRAFT:
        return queryset.filter(status=Article.Status.DRAFT).exclude(scheduled_q())
    if state == STATE_ARCHIVED:
        return queryset.filter(status=Article.Status.ARCHIVED)
    if state == STATE_REVIEW:
        return queryset.filter(pk__in=in_review_article_pks())
    if state == STATE_SCHEDULED:
        return queryset.filter(scheduled_q())
    return queryset


def editorial_state(article, review_ids, scheduled=frozenset()):
    """Estado mais específico de um artigo, para o selo da listagem.

    ``review_ids`` e ``scheduled`` vêm de ``in_review_ids`` e ``scheduled_ids``
    (uma consulta para a página inteira, em vez de uma por artigo).
    """
    if str(article.pk) in review_ids:
        return STATE_REVIEW
    if not article.live and str(article.pk) in scheduled:
        return STATE_SCHEDULED
    if article.status == Article.Status.PUBLISHED:
        return STATE_PUBLISHED
    if article.status == Article.Status.ARCHIVED:
        return STATE_ARCHIVED
    return STATE_DRAFT
