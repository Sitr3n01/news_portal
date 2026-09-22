"""Comentários e newsletter no Wagtail — migração progressiva do Django admin.

Por que aqui: o cargo "Editor de Notícias" recebe permissão de moderar
comentários e acompanhar a newsletter (apps/accounts/admin_roles.py), mas não é
``is_staff`` — então nunca alcançou essas telas, que só existiam no /admin/. No
Wagtail elas ficam atrás da mesma porta que o editor já usa (``access_admin``)
e das MESMAS permissões de modelo, sem conceder nada novo a ninguém.

Paridade com o Django admin (apps/news/admin.py):

* ninguém cria esses registros à mão — nascem no site público ou no envio da
  newsletter (``has_add_permission = False`` lá; política sem "add" aqui);
* o texto do comentário e os dados da inscrição são somente leitura; só a
  visibilidade/estado ativo muda;
* entregas da newsletter são trilha de auditoria: somente leitura;
* as ações em massa (aprovar/ocultar, reativar/desativar) existem nos dois;
* a exportação de e-mails em CSV continua SÓ no Django admin, restrita a
  superusuário e com neutralização de fórmulas (``_csv_safe``) — a exportação
  nativa do Wagtail não neutraliza fórmulas, então não é habilitada.

As telas do Django admin continuam registradas: nada foi removido.
"""

from django.utils.functional import cached_property
from django.utils.text import Truncator
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.admin.ui.tables import BooleanColumn, Column, DateColumn
from wagtail.permission_policies.base import ModelPermissionPolicy
from wagtail.snippets.bulk_actions.snippet_bulk_action import SnippetBulkAction
from wagtail.snippets.views.snippets import SnippetViewSet

from apps.news.models import Comment, NewsletterDelivery, NewsletterSubscription


class RestrictedPermissionPolicy(ModelPermissionPolicy):
    """Política de modelo sem algumas ações, para todos (inclusive superusuário)."""

    def __init__(self, model, denied_actions):
        super().__init__(model)
        self.denied_actions = frozenset(denied_actions)

    def user_has_permission(self, user, action):
        if action in self.denied_actions:
            return False
        return super().user_has_permission(user, action)

    def user_has_any_permission(self, user, actions):
        return any(self.user_has_permission(user, action) for action in actions)


class _ReadOnlyOriginViewSet(SnippetViewSet):
    add_to_admin_menu = False
    # Comentários e inscrições são gravados pelo site público: indexar
    # referências a cada gravação só custaria tempo na requisição do leitor.
    add_to_reference_index = False
    copy_view_enabled = False
    denied_actions = ('add',)

    @cached_property
    def permission_policy(self):
        return RestrictedPermissionPolicy(self.model, self.denied_actions)


class CommentSnippetViewSet(_ReadOnlyOriginViewSet):
    model = Comment
    icon = 'comment'
    menu_label = 'Comentários'
    menu_name = 'comments'
    list_per_page = 25
    # A primeira coluna precisa ser um nome (não um Column): é dela que o
    # Wagtail faz o título com link de edição e o menu de ações da linha.
    list_display = [
        '__str__',
        Column('content', label='Trecho', accessor=lambda comment: Truncator(comment.content).chars(90)),
        BooleanColumn('is_active', label='Visível'),
        DateColumn('created_at', label='Recebido em'),
    ]
    list_filter = ['is_active']
    search_fields = ['content', 'user__username', 'article__title']
    panels = [
        MultiFieldPanel(
            [
                FieldPanel('user', read_only=True),
                FieldPanel('article', read_only=True),
                FieldPanel('content', read_only=True),
            ],
            heading='Comentário',
            help_text='O texto do comentário não é editado no painel.',
        ),
        FieldPanel(
            'is_active',
            heading='Visível no portal',
            help_text='Desmarque para ocultar o comentário do portal sem apagar o registro.',
        ),
    ]


class NewsletterSubscriptionSnippetViewSet(_ReadOnlyOriginViewSet):
    model = NewsletterSubscription
    icon = 'mail'
    menu_label = 'Assinantes da newsletter'
    menu_name = 'newsletter-subscriptions'
    list_per_page = 25
    list_display = [
        'email',
        Column('site', label='Portal'),
        BooleanColumn('is_active', label='Ativo'),
        DateColumn('created_at', label='Inscrito em'),
    ]
    list_filter = ['is_active', 'site']
    search_fields = ['email']
    panels = [
        FieldPanel('email', read_only=True),
        FieldPanel('site', read_only=True),
        FieldPanel(
            'is_active',
            help_text='Desative apenas quando houver pedido de cancelamento ou sinal claro de spam.',
        ),
    ]


class NewsletterDeliverySnippetViewSet(_ReadOnlyOriginViewSet):
    model = NewsletterDelivery
    icon = 'mail'
    menu_label = 'Entregas da newsletter'
    menu_name = 'newsletter-deliveries'
    list_per_page = 50
    denied_actions = ('add', 'change')
    inspect_view_enabled = True
    inspect_view_fields = [
        'article', 'subscription', 'email', 'status', 'attempts', 'sent_at', 'last_error', 'created_at', 'updated_at',
    ]
    list_display = [
        'email',
        Column('article', label='Notícia'),
        Column('status', label='Estado', accessor='get_status_display'),
        Column('attempts', label='Tentativas'),
        DateColumn('sent_at', label='Enviado em'),
        DateColumn('updated_at', label='Atualizado em'),
    ]
    list_filter = ['status']
    search_fields = ['email', 'article__title', 'last_error']


# ── Ações em massa ──────────────────────────────────────────────────────────


class _SetFlagBulkAction(SnippetBulkAction):
    """Liga/desliga um booleano em lote — mesmo efeito das actions do Django admin."""

    template_name = 'news/wagtail/bulk_actions/confirm_set_flag.html'
    field_name = ''
    value = None
    confirm_question = ''
    confirm_button = ''
    success_singular = ''
    success_plural = ''

    def check_perm(self, snippet):
        if getattr(self, '_can_change', None) is None:
            self._can_change = self.model.snippet_viewset.permission_policy.user_has_permission(
                self.request.user, 'change',
            )
        return self._can_change

    @classmethod
    def execute_action(cls, objects, **kwargs):
        model = kwargs['self'].model
        updated = model.objects.filter(pk__in=[obj.pk for obj in objects]).update(**{cls.field_name: cls.value})
        return updated, 0

    def get_success_message(self, num_parent_objects, num_child_objects):
        template = self.success_singular if num_parent_objects == 1 else self.success_plural
        return template.format(count=num_parent_objects)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'action_title': self.display_name,
            'confirm_question': self.confirm_question,
            'confirm_button': self.confirm_button,
        })
        return context


class ApproveCommentsBulkAction(_SetFlagBulkAction):
    models = [Comment]
    display_name = 'Aprovar'
    action_type = 'approve_comments'
    aria_label = 'Aprovar os comentários selecionados'
    action_priority = 10
    field_name = 'is_active'
    value = True
    confirm_question = 'Tornar visíveis no portal os comentários abaixo?'
    confirm_button = 'Sim, aprovar'
    success_singular = '1 comentário aprovado.'
    success_plural = '{count} comentários aprovados.'


class HideCommentsBulkAction(_SetFlagBulkAction):
    models = [Comment]
    display_name = 'Ocultar'
    action_type = 'hide_comments'
    aria_label = 'Ocultar os comentários selecionados'
    action_priority = 20
    field_name = 'is_active'
    value = False
    confirm_question = 'Ocultar do portal os comentários abaixo? O registro é mantido.'
    confirm_button = 'Sim, ocultar'
    success_singular = '1 comentário ocultado.'
    success_plural = '{count} comentários ocultados.'


class ActivateSubscriptionsBulkAction(_SetFlagBulkAction):
    models = [NewsletterSubscription]
    display_name = 'Reativar'
    action_type = 'activate_subscriptions'
    aria_label = 'Reativar as inscrições selecionadas'
    action_priority = 10
    field_name = 'is_active'
    value = True
    confirm_question = 'Reativar as inscrições abaixo?'
    confirm_button = 'Sim, reativar'
    success_singular = '1 inscrição reativada.'
    success_plural = '{count} inscrições reativadas.'


class DeactivateSubscriptionsBulkAction(_SetFlagBulkAction):
    models = [NewsletterSubscription]
    display_name = 'Desativar'
    action_type = 'deactivate_subscriptions'
    aria_label = 'Desativar as inscrições selecionadas'
    action_priority = 20
    field_name = 'is_active'
    value = False
    confirm_question = 'Desativar as inscrições abaixo (spam, bots ou pedido de cancelamento)?'
    confirm_button = 'Sim, desativar'
    success_singular = '1 inscrição desativada.'
    success_plural = '{count} inscrições desativadas.'


BULK_ACTIONS = (
    ApproveCommentsBulkAction,
    HideCommentsBulkAction,
    ActivateSubscriptionsBulkAction,
    DeactivateSubscriptionsBulkAction,
)
