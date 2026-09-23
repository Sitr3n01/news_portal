"""Barra única do editor do Wagtail (criação e edição de snippets).

Monta, a partir do contexto que a própria view do Wagtail entrega, o que o
cabeçalho do editor mostra (templates/newsroom/editor/header.html): para onde
voltar, o título, o selo de status e as ações secundárias (copiar, inspecionar,
remover).

Nada aqui publica, salva ou altera conteúdo. Salvar, publicar e enviar para
moderação continuam sendo os botões nativos do Wagtail, dentro do formulário;
a barra só os aciona (static/newsroom/js/newsroom-editor.js).
"""

from django.utils import timezone
from wagtail.models import DraftStateMixin
from wagtail.snippets.views import snippets as snippet_views

from apps.news import editorial
from apps.news.models import Article

# Rótulo do "voltar" quando o nome do modelo no Wagtail difere do menu do painel.
BACK_LABELS = {Article: 'Notícias'}
NEW_TITLES = {Article: 'Nova notícia'}

# Ícones do Wagtail → sprite do painel, no menu "Mais opções".
MORE_ICONS = {'copy': 'copy', 'bin': 'trash', 'info-circle': 'info', 'history': 'history', 'lock': 'lock'}
DANGER_ICONS = {'bin'}

GENERIC_LABELS = {'published': 'Publicado', 'draft': 'Rascunho'}


def _model(context):
    model = context.get('model')
    if model is None and context.get('object') is not None:
        model = type(context['object'])
    return model


def _is_create(context):
    view = context.get('view')
    return getattr(view, 'view_name', '') == 'create'


def _back(context, model):
    """Último item da trilha que tem endereço: a listagem do modelo."""
    items = [item for item in context.get('breadcrumbs_items') or [] if item.get('url')]
    if not items:
        return None
    target = items[-1]
    return {'url': target['url'], 'label': BACK_LABELS.get(model, target['label'])}


def _exists(context):
    obj = context.get('object')
    return obj is not None and obj.pk is not None


def _title(context, model, is_create):
    # Na criação, o objeto passa a existir no primeiro salvamento automático, e
    # a barra (reenviada por edit_partials.html) passa a mostrar o título dele.
    if is_create and not _exists(context) and model in NEW_TITLES:
        return NEW_TITLES[model]
    if context.get('page_subtitle'):
        return str(context['page_subtitle'])
    items = context.get('breadcrumbs_items') or []
    if items:
        return str(items[-1]['label'])
    return str(context.get('header_title') or '')


def _article_status(obj):
    # A view entrega a última REVISÃO como objeto, e o `status` guardado nela é
    # o do momento em que foi salva. O estado real é a linha gravada no banco.
    stored = (
        Article._default_manager.filter(pk=obj.pk)
        .only('status', 'live', 'has_unpublished_changes', 'go_live_at')
        .first()
    )
    if stored is None:
        return None
    scheduled = stored.scheduled_revision
    state = editorial.editorial_state(
        stored, editorial.in_review_ids([stored.pk]), {str(stored.pk)} if scheduled else set(),
    )
    note = ''
    if state == editorial.STATE_REVIEW:
        task = stored.current_workflow_task
        note = f'Etapa: {task.name}' if task else ''
    elif scheduled:
        # Agendada (fora do ar) ou nova versão agendada de uma notícia no ar.
        when = _when(scheduled.approved_go_live_at)
        note = f'Publica em {when}' if not stored.live else f'Nova versão agendada para {when}'
    elif stored.live and stored.has_unpublished_changes:
        note = 'Alterações não publicadas'
    elif not stored.live and stored.go_live_at and stored.go_live_at > timezone.now():
        # Data preenchida e rascunho salvo, mas ninguém clicou em "Agendar
        # publicação": o Wagtail não vai publicar sozinho.
        note = f'Data marcada para {_when(stored.go_live_at)}, ainda não agendada'
    return {'key': state, 'label': editorial.STATE_LABELS[state], 'note': note}


def _when(value):
    return timezone.localtime(value).strftime('%d/%m às %H:%M')


def _generic_status(model, obj):
    stored = model._default_manager.filter(pk=obj.pk).values('live', 'has_unpublished_changes').first()
    if stored is None:
        return None
    key = 'published' if stored['live'] else 'draft'
    note = 'Alterações não publicadas' if stored['live'] and stored['has_unpublished_changes'] else ''
    return {'key': key, 'label': GENERIC_LABELS[key], 'note': note}


def _status(context, model):
    if model is None or not issubclass(model, DraftStateMixin):
        return None
    obj = context.get('object')
    if not _exists(context):
        return {'key': 'draft', 'label': 'Rascunho', 'note': 'Ainda não salvo'}
    if issubclass(model, Article):
        return _article_status(obj)
    return _generic_status(model, obj)


def _more(context):
    view = context.get('view')
    buttons = getattr(view, 'header_more_buttons', None) or []
    items = []
    for button in sorted(buttons):
        if not getattr(button, 'url', None):
            continue
        icon = getattr(button, 'icon_name', '') or ''
        items.append({
            'label': button.label,
            'url': button.url,
            'icon': MORE_ICONS.get(icon, 'arrow'),
            'attrs': getattr(button, 'base_attrs_string', ''),
            'danger': icon in DANGER_ICONS,
        })
    # Ação destrutiva sempre por último, separada das demais.
    items.sort(key=lambda item: item['danger'])
    for index, item in enumerate(items):
        item['divider_before'] = item['danger'] and index > 0 and not items[index - 1]['danger']
    return items


def editor_bar(context):
    model = _model(context)
    is_create = _is_create(context)
    return {
        # Só os formulários de snippet usam a barra (templates/wagtailsnippets/snippets/).
        'enabled': isinstance(context.get('view'), (snippet_views.CreateView, snippet_views.EditView)),
        'back': _back(context, model),
        'title': _title(context, model, is_create),
        'status': _status(context, model),
        'locked': bool(context.get('locked_for_user')),
        'more': _more(context),
        'history_url': context.get('history_url'),
    }
