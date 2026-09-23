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
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.admin.panels import PublishingPanel
from wagtail.snippets.views.snippets import CopyView, CreateView, IndexView, PreviewOnCreateView

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


class ArticleIndexView(IndexView):
    def get_edit_url(self, instance):
        if not self.permission_policy.user_has_permission_for_instance(self.request.user, 'change', instance):
            return None
        return super().get_edit_url(instance)


class ArticleCreateView(CreateView):
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
