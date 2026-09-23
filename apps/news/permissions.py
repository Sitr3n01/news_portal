"""Quem pode alterar QUAL notícia — regra editorial única.

As permissões de modelo (``news.change_article`` etc., distribuídas por cargo
em apps/accounts/admin_roles.py) dizem se alguém edita notícias *em geral*. A
edição do Wagtail 7.4 só confere isso. Esta regra acrescenta o recorte por
notícia, decidido com a redação:

* quem PUBLICA (``news.publish_article``: Editor de Notícias, Administrador
  Geral, superusuário) altera qualquer notícia;
* quem não publica (Repórter) altera as PRÓPRIAS notícias (é o autor) em
  qualquer estado, e as dos colegas só enquanto forem RASCUNHO — nunca uma
  publicada ou retirada do ar.

Em revisão, o próprio Wagtail ainda bloqueia a edição para quem não é
aprovador da etapa (WorkflowLock); esta regra não afrouxa isso.

Usada em três lugares, para que nunca divirjam: a política de permissão do
snippet (listagens e botões do Wagtail), o hook ``before_edit_snippet`` (porta
da edição e da restauração de revisão) e a visão geral (/painel/).
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import Q
from wagtail.permission_policies.base import ModelPermissionPolicy

PUBLISH_PERMISSION = 'news.publish_article'
CHANGE_PERMISSION = 'news.change_article'


def can_publish(user):
    return bool(user and user.is_authenticated and user.has_perm(PUBLISH_PERMISSION))


def is_draft(article):
    """Rascunho = ``status`` DRAFT: nunca esteve no ar nem foi retirado dele.

    ``status`` é a fonte de verdade da visibilidade pública (ver
    apps/news/migrations/0025); o ``live`` do Wagtail não entra na conta — ele
    nasce True em linhas criadas fora do editor.
    """
    from apps.news.models import Article

    return article.status == Article.Status.DRAFT


def can_edit_article(user, article):
    if not (user and user.is_authenticated and user.has_perm(CHANGE_PERMISSION)):
        return False
    if can_publish(user):
        return True
    if article.author_id is not None and article.author_id == user.pk:
        return True
    return is_draft(article)


class ArticlePermissionPolicy(ModelPermissionPolicy):
    """Política do snippet Article: modelo + recorte por notícia em "change"."""

    def user_has_permission_for_instance(self, user, action, instance):
        if action == 'change':
            return can_edit_article(user, instance)
        return super().user_has_permission_for_instance(user, action, instance)

    def user_has_any_permission_for_instance(self, user, actions, instance):
        return any(self.user_has_permission_for_instance(user, action, instance) for action in actions)


def editorial_team(current_author_id=None):
    """Quem pode assinar uma notícia: contas ativas que escrevem notícias.

    Antes o campo "Autor" listava TODAS as contas — inclusive leitores do
    portal —, expondo nomes e permitindo atribuir matéria a quem não escreve.
    O autor atual continua na lista mesmo que tenha deixado a equipe, para não
    apagar a autoria de matérias antigas ao salvar.
    """
    writer_permissions = Permission.objects.filter(
        content_type__app_label='news', codename__in=['add_article', 'change_article'],
    )
    team = (
        Q(is_active=True)
        & (Q(is_superuser=True) | Q(groups__permissions__in=writer_permissions) | Q(user_permissions__in=writer_permissions))
    )
    if current_author_id:
        team |= Q(pk=current_author_id)
    user_model = get_user_model()
    return user_model.objects.filter(
        pk__in=user_model.objects.filter(team).values('pk'),
    ).order_by('first_name', 'last_name', 'username')
