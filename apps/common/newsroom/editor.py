"""Barra única do editor do Wagtail (criação e edição de snippets).

Monta, a partir do contexto que a própria view do Wagtail entrega, o que o
cabeçalho do editor mostra (templates/newsroom/editor/header.html): para onde
voltar, o título, o controle "Publicação" (estado, agendamento, trava) e as
ações secundárias (copiar, inspecionar, remover).

Nada aqui publica, salva ou altera conteúdo. Salvar, publicar e enviar para
moderação continuam sendo os botões nativos do Wagtail, dentro do formulário;
a barra só os aciona (static/newsroom/js/newsroom-editor.js).
"""

from django.utils import timezone
from wagtail.admin.utils import get_user_display_name
from wagtail.models import DraftStateMixin
from wagtail.snippets.views import snippets as snippet_views

from apps.news import editorial
from apps.news.models import Article

# Rótulo do "voltar" quando o nome do modelo no Wagtail difere do menu do painel.
BACK_LABELS = {Article: 'Notícias'}
NEW_TITLES = {Article: 'Nova notícia'}

# Ícones do Wagtail → sprite do painel. "Inspecionar" usa a lupa: o "i" é o
# de "Ver todos os detalhes", no controle "Publicação".
MORE_ICONS = {'copy': 'copy', 'bin': 'trash', 'info-circle': 'search', 'history': 'history', 'lock': 'lock'}
# Copiar e inspecionar viram ícones nas ferramentas; remover, botão ao lado de
# "Salvar rascunho". O que sobrar fica no menu "Mais opções".
QUICK_ICONS = ('copy', 'info-circle')
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


def _status_panel(context):
    for panel in context.get('side_panels') or []:
        if getattr(panel, 'name', '') == 'status':
            return panel
    return None


def _last_edit(model, context):
    if not _exists(context):
        return None
    stored = model._default_manager.filter(pk=context['object'].pk).select_related('latest_revision__user').first()
    revision = getattr(stored, 'latest_revision', None)
    if revision is None:
        return None
    return {'at': revision.created_at, 'by': get_user_display_name(revision.user) if revision.user else ''}


def _schedule(panel, parent):
    """Datas de entrar e sair do ar, com a mesma leitura do painel "Status" do
    Wagtail: agendada (revisão aprovada), só marcada no rascunho, ou nenhuma."""
    data = panel.get_scheduled_publishing_context(parent)
    if not data.get('draftstate_enabled'):
        return None
    # O Wagtail decide o "Definir cronograma" pela CLASSE do formulário; a
    # governança (RestrictedPublishingPanel) tira os campos da INSTÂNCIA de quem
    # não publica. Sem os campos, a janela abriria vazia.
    form = parent.get('form')
    editable = bool(data['show_schedule_publishing_toggle']) and (form is None or 'go_live_at' in form.fields)

    def row(scheduled, draft, live=None):
        if scheduled:
            return {'when': _when(scheduled), 'state': 'scheduled'}
        if draft:
            return {'when': _when(draft), 'state': 'pending'}
        if live:
            return {'when': _when(live), 'state': 'scheduled'}
        return None

    go_live = row(data['scheduled_go_live_at'], data['draft_go_live_at'])
    expire = row(data['scheduled_expire_at'], data['draft_expire_at'], data.get('live_expire_at'))
    return {
        'go_live': go_live,
        'expire': expire,
        'pending': any(item and item['state'] == 'pending' for item in (go_live, expire)),
        'active': any(item and item['state'] == 'scheduled' for item in (go_live, expire)),
        'errors': data['schedule_has_errors'],
        'editable': editable,
    }


def _lock(panel, parent):
    if not panel.locking_enabled or not _exists(parent):
        return None
    data = panel.get_lock_context(parent)
    if data['lock']:
        info = data['lock_context']
        return {
            'locked': True,
            'title': str(info['locked_by']),
            'text': str(info['description']),
            'can_toggle': bool(data['user_can_unlock']),
        }
    return {
        'locked': False,
        'title': 'Edição livre',
        'text': 'Qualquer pessoa da equipe pode editar.' + (' Trave para impedir.' if data['user_can_lock'] else ''),
        'can_toggle': bool(data['user_can_lock']),
    }


def _publication(context, model, status):
    """Controle "Publicação" da barra: estado, agendamento, trava e histórico
    num só lugar. Lê o painel "Status" do Wagtail, que continua na página e
    guarda os controles de verdade (a janela de agendamento e a trava)."""
    panel = _status_panel(context)
    if status is None or panel is None:
        return None
    parent = context.flatten() if hasattr(context, 'flatten') else dict(context)
    return {
        'last_edit': _last_edit(model, context),
        'schedule': _schedule(panel, parent),
        'lock': _lock(panel, parent),
    }


def _secondary(context):
    """Ações secundárias do Wagtail (header_more_buttons), repartidas entre os
    ícones das ferramentas, o botão de remover e o menu "Mais opções"."""
    view = context.get('view')
    buttons = getattr(view, 'header_more_buttons', None) or []
    quick, danger, more = [], [], []
    for button in sorted(buttons):
        if not getattr(button, 'url', None):
            continue
        icon = getattr(button, 'icon_name', '') or ''
        item = {
            'label': button.label,
            'url': button.url,
            'icon': MORE_ICONS.get(icon, 'arrow'),
            'attrs': getattr(button, 'base_attrs_string', ''),
            'danger': icon in DANGER_ICONS,
        }
        if icon in QUICK_ICONS:
            quick.append((QUICK_ICONS.index(icon), item))
        elif item['danger']:
            danger.append(item)
        else:
            more.append(item)
    return {
        'quick': [item for _, item in sorted(quick, key=lambda pair: pair[0])],
        'danger': danger,
        'more': more,
    }


def editor_bar(context):
    model = _model(context)
    is_create = _is_create(context)
    secondary = _secondary(context)
    status = _status(context, model)
    return {
        # Só os formulários de snippet usam a barra (templates/wagtailsnippets/snippets/).
        'enabled': isinstance(context.get('view'), (snippet_views.CreateView, snippet_views.EditView)),
        'back': _back(context, model),
        'title': _title(context, model, is_create),
        'status': status,
        'publication': _publication(context, model, status),
        'locked': bool(context.get('locked_for_user')),
        'quick': secondary['quick'],
        'danger': secondary['danger'],
        'more': secondary['more'],
        'history_url': context.get('history_url'),
    }
