"""Peças do editor de notícias no Wagtail que aplicam a regra editorial.

Tudo aqui usa pontos de extensão oficiais do Wagtail 7.4 — classes de view e de
formulário do ``SnippetViewSet`` e painéis — sem tocar no código do Wagtail. A
regra em si mora em apps/news/permissions.py.

* Campos sensíveis (destaque na home, portal, autor e agendamento) só existem
  no formulário de quem publica: ``FieldPanel(permission=...)`` remove o campo
  do formulário NO SERVIDOR, não só da tela.
* Nova notícia já nasce assinada por quem a cria e no portal atual; quem
  publica pode trocar o autor, mas só por alguém da equipe editorial.
* Na listagem, o link e o botão "Editar" só aparecem para a notícia que a
  pessoa pode alterar; as outras abrem a ficha somente leitura.
* "Copiar" nunca grava sobre a notícia de origem.
"""

from django.contrib.sites.shortcuts import get_current_site
from django.db.models import BooleanField, Case, Value, When
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import format_html
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.admin.panels import PublishingPanel
from wagtail.admin.utils import get_latest_str
from wagtail.snippets.views.snippets import (
    CopyView,
    CreateView,
    DeleteView,
    EditView,
    IndexView,
    PreviewOnCreateView,
)

from apps.news import editorial
from apps.news.permissions import editorial_team


class ArticleAdminForm(WagtailAdminModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        author = self.fields.get('author')
        if author is not None:
            author.queryset = editorial_team(current_author_id=self.instance.author_id)


class RestrictedPublishingPanel(PublishingPanel):
    """Agendamento (entrada e saída do ar) só para quem tem a permissão.

    A permissão de um grupo de painéis só esconde o grupo da tela; os campos
    ``go_live_at``/``expire_at`` continuariam no formulário. Repassar a
    permissão aos campos filhos faz o formulário ignorá-los no servidor.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for child in self.children:
            child.permission = self.permission


def _stamp_new_article(instance, request):
    instance.author = request.user
    instance.site = get_current_site(request)
    return instance


def _editorial_annotations(queryset):
    """Marca, na mesma consulta da listagem, quem está em revisão e quem tem
    revisão agendada: o selo de cada linha sai daqui, sem consulta por linha."""
    return queryset.annotate(
        nr_in_review=Case(
            When(pk__in=editorial.in_review_article_pks(), then=Value(True)),
            default=Value(False), output_field=BooleanField(),
        ),
        nr_scheduled=Case(
            When(pk__in=editorial.scheduled_article_pks(), then=Value(True)),
            default=Value(False), output_field=BooleanField(),
        ),
    )


def editorial_badge(article):
    """Selo de estado da linha (a mesma leitura da visão geral e da barra do editor)."""
    pk = str(article.pk)
    state = editorial.editorial_state(
        article,
        {pk} if getattr(article, 'nr_in_review', False) else set(),
        {pk} if getattr(article, 'nr_scheduled', False) else set(),
    )
    return format_html('<span class="nr-status nr-status--{}">{}</span>', state, editorial.STATE_LABELS[state])


class ArticleIndexView(IndexView):
    """Listagem de notícias no desenho do painel (newsroom/wagtail/list_header.html):
    cabeçalho com contagem e "Nova notícia", abas por estado editorial com
    contagem (as mesmas da visão geral) e a busca e os filtros do Wagtail."""

    STATE_PARAM = 'estado'

    @cached_property
    def editorial_filter(self):
        value = self.request.GET.get(self.STATE_PARAM, editorial.FILTER_ALL)
        return value if value in editorial.FILTER_KEYS else editorial.FILTER_ALL

    def get_base_queryset(self):
        queryset = _editorial_annotations(super().get_base_queryset())
        return editorial.filter_articles(queryset, self.editorial_filter)

    def get_edit_url(self, instance):
        if not self.permission_policy.user_has_permission_for_instance(self.request.user, 'change', instance):
            return None
        return super().get_edit_url(instance)

    EMPTY_BY_STATE = {
        editorial.STATE_PUBLISHED: 'Nenhuma notícia publicada.',
        editorial.STATE_DRAFT: 'Nenhuma notícia em rascunho.',
        editorial.STATE_REVIEW: 'Nenhuma notícia em revisão no momento.',
        editorial.STATE_SCHEDULED: 'Nenhuma notícia agendada.',
        editorial.STATE_ARCHIVED: 'Nenhuma notícia arquivada.',
    }

    @cached_property
    def no_results_message(self):
        # O do Wagtail diria "Não há Notícias para exibir. Por que não adicionar um?".
        if self.is_searching or self.is_filtering:
            return 'Nenhuma notícia encontrada com essa busca ou esses filtros.'
        if self.editorial_filter in self.EMPTY_BY_STATE:
            return self.EMPTY_BY_STATE[self.editorial_filter]
        if self.add_url:
            return format_html('Nenhuma notícia ainda. <a href="{}">Escreva a primeira</a>.', self.add_url)
        return 'Nenhuma notícia ainda.'

    def _tabs(self, base):
        params = self.request.GET.copy()
        params.pop(self.page_kwarg, None)
        tabs = []
        for key, label in editorial.FILTERS:
            query = params.copy()
            query.pop(self.STATE_PARAM, None)
            if key != editorial.FILTER_ALL:
                query[self.STATE_PARAM] = key
            tabs.append({
                'label': label,
                'count': editorial.filter_articles(base, key).count(),
                'url': f'{self.request.path}?{query.urlencode()}' if query else self.request.path,
                'active': key == self.editorial_filter,
            })
        return tabs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.results_only:
            return context
        base = _editorial_annotations(super().get_base_queryset())
        context['nr_list'] = {
            'title': 'Notícias',
            'description': 'Tudo o que a redação produz: rascunhos, revisões, agendadas e publicadas.',
            'total': base.count(),
            'primary': {'label': 'Nova notícia', 'url': self.add_url} if self.add_url else None,
            'tabs': self._tabs(base),
            'state': '' if self.editorial_filter == editorial.FILTER_ALL else self.editorial_filter,
            'state_param': self.STATE_PARAM,
        }
        return context


class FeminineMessagesMixin:
    """Mensagens de sucesso concordando com "notícia". As do Wagtail montam
    "%(model_name)s '%(object)s' atualizado" e sairiam "Notícia 'X' atualizado".
    Mesma lógica de wagtail.admin.views.generic.mixins (Wagtail 7.4)."""

    def get_success_message(self, instance=None):
        obj = instance or self.object
        created = self.view_name == 'create'
        message = "Notícia '%(object)s' criada." if created else "Notícia '%(object)s' atualizada."
        if self.action == 'publish':
            if obj.go_live_at and obj.go_live_at > timezone.now():
                if created:
                    message = "Notícia '%(object)s' criada e agendada para publicação."
                elif obj.live:
                    message = "Notícia '%(object)s' está no ar, e esta versão foi agendada para publicação."
                else:
                    message = "Notícia '%(object)s' agendada para publicação."
            else:
                message = "Notícia '%(object)s' criada e publicada." if created else "Notícia '%(object)s' atualizada e publicada."
        if self.action == 'submit':
            message = "Notícia '%(object)s' criada e enviada para revisão." if created else "Notícia '%(object)s' enviada para revisão."
        if self.action == 'restart-workflow':
            message = "Revisão da notícia '%(object)s' reiniciada."
        if self.action == 'cancel-workflow':
            message = "Revisão da notícia '%(object)s' cancelada."
        return message % {'object': get_latest_str(obj)}


class ArticleEditView(FeminineMessagesMixin, EditView):
    pass


class ArticleDeleteView(DeleteView):
    success_message = "Notícia '%(object)s' excluída."

    def get_success_message(self):
        return self.success_message % {'object': self.object}


class ArticleCreateView(FeminineMessagesMixin, CreateView):
    def get_initial_form_instance(self):
        instance = super().get_initial_form_instance() or self.model()
        return _stamp_new_article(instance, self.request)


class ArticlePreviewOnCreateView(PreviewOnCreateView):
    def get_object(self):
        return _stamp_new_article(super().get_object(), self.request)


class ArticleCopyView(CopyView):
    """A cópia só MOSTRA o formulário pré-preenchido; quem cria é a view de adição.

    O formulário da cópia é enviado para o endereço de adição (``action_url``),
    que cria uma notícia nova, em rascunho e assinada por quem copia. Já um POST
    no próprio endereço de cópia — que o Wagtail 7.4 aceitaria — salvaria o
    formulário sobre a notícia ORIGINAL (a instância vai com a chave primária)
    e bastaria permissão de "ver" para isso. Como a tela nunca faz esse POST,
    ele é recusado (405).
    """

    http_method_names = ['get', 'head', 'options']
