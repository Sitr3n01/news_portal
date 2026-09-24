"""Cabeçalho do painel nas listagens do Wagtail (templates/newsroom/wagtail/list_header.html).

O Wagtail monta o cabeçalho das listagens (slim_header) com a trilha, o botão
de adicionar, o menu ⋯ e a busca. A sobrescrita de wagtailadmin/generic/listing.html
troca isso pelo cabeçalho das listas do Django admin: título com contagem,
descrição, a ação principal e os demais botões, e a busca e os filtros do
Wagtail num cartão com a tabela.

Aqui ficam só os textos de cada seção (os mesmos nomes da sidebar,
apps/common/newsroom/navigation.py) e a leitura do contexto que a própria view
do Wagtail entrega. A listagem de notícias entrega o seu (``nr_list``, com as
abas de estado), que vale no lugar deste.
"""

import re

from wagtail.admin.widgets.button import BaseDropdownMenuButton

# Por nome de rota (request.resolver_match.view_name). `add`: rótulo do botão
# principal, no gênero certo (o do Wagtail é "Adicionar Categoria"). `empty`:
# lista vazia, no lugar de frases do catálogo pt-BR do Wagtail como "Não há
# Comentários para exibir" ou "Por que não foi adicionado?".
LISTS = {
    'news_workflow_report': {
        'title': 'Em revisão',
        'description': 'Notícias aguardando aprovação, com a etapa atual e há quanto tempo estão paradas.',
        'empty': 'Nenhuma notícia aguardando revisão.',
    },
    'wagtailimages:index': {
        'title': 'Biblioteca de mídia',
        'description': 'Imagens das notícias e das páginas. Envie uma vez e reaproveite onde precisar.',
        'add': 'Enviar imagens',
        'empty': 'Nenhuma imagem enviada ainda.',
    },
    'wagtaildocs:index': {
        'title': 'Documentos',
        'description': 'Arquivos para download, como PDFs e planilhas, usados nas notícias e nas páginas.',
        'add': 'Enviar documentos',
        'empty': 'Nenhum documento enviado ainda.',
    },
    'wagtailsnippets_news_comment:list': {
        'title': 'Comentários',
        'description': 'O que os leitores escrevem nas notícias. Aprove, oculte ou remova antes que apareça no site.',
        'empty': 'Nenhum comentário ainda.',
    },
    'wagtailsnippets_news_newslettersubscription:list': {
        'title': 'Newsletter',
        'description': 'Quem recebe as notícias por e-mail e se a inscrição está ativa.',
        'empty': 'Ninguém assinou a newsletter ainda.',
    },
    'wagtailsnippets_news_newsletterdelivery:list': {
        'title': 'Entregas da newsletter',
        'description': 'Cada envio por notícia e destinatário, com o resultado e as tentativas.',
        'empty': 'Nenhuma entrega registrada ainda.',
    },
    'wagtailsnippets_news_category:list': {
        'title': 'Categorias',
        'description': 'Os assuntos que organizam as notícias no site, nos filtros e nos feeds.',
        'add': 'Nova categoria',
        'empty': 'Nenhuma categoria ainda.',
    },
    'wagtailsnippets_news_tag:list': {
        'title': 'Tags',
        'description': 'Palavras-chave que ligam notícias sobre o mesmo tema.',
        'add': 'Nova tag',
        'empty': 'Nenhuma tag ainda.',
    },
    'wagtailsnippets_news_newshomeconfig:list': {
        'title': 'Home do portal',
        'description': 'Destaque principal e destaques secundários da página inicial de notícias.',
        'add': 'Nova configuração',
        'empty': 'Nenhuma configuração criada: a home usa o comportamento automático.',
    },
    'wagtailsnippets_common_siteextension:list': {
        'title': 'Configurações',
        'description': 'Identidade, contato e redes sociais de cada portal.',
        'add': 'Nova configuração',
        'empty': 'Nenhuma configuração criada.',
    },
    'wagtailadmin_reports:workflow': {
        'title': 'Relatório de revisões',
        'description': 'Todas as revisões pedidas, em andamento e encerradas, com quem pediu e o resultado.',
        'empty': 'Nenhuma revisão pedida ainda.',
    },
    'wagtailadmin_reports:workflow_tasks': {
        'title': 'Relatório de tarefas',
        'description': 'Cada etapa de revisão, com quem aprovou ou pediu mudanças.',
        'empty': 'Nenhuma etapa de revisão registrada ainda.',
    },
    'wagtailadmin_reports:site_history': {
        'title': 'Histórico do site',
        'description': 'Tudo o que foi criado, editado, publicado ou removido no CMS, e por quem.',
        'empty': 'Nada registrado no histórico ainda.',
    },
    'wagtailadmin_workflows:index': {
        'title': 'Fluxos de revisão',
        'description': 'As sequências de aprovação por que uma notícia passa antes de ir ao ar.',
        'add': 'Novo fluxo',
        'empty': 'Nenhum fluxo de revisão criado.',
    },
    'wagtailadmin_workflows:task_index': {
        'title': 'Tarefas de revisão',
        'description': 'As etapas que compõem os fluxos, com quem pode aprovar cada uma.',
        'add': 'Nova tarefa',
        'empty': 'Nenhuma tarefa de revisão criada.',
    },
    'wagtailusers_groups:index': {
        'title': 'Grupos e coleções (CMS)',
        'description': 'Grupos de permissão do CMS: o que cada equipe pode ver, editar e publicar.',
        'add': 'Novo grupo',
        'empty': 'Nenhum grupo criado.',
    },
    'wagtailadmin_collections:index': {
        'title': 'Coleções de mídia',
        'description': 'Pastas que organizam imagens e documentos e definem quem pode usá-los.',
        'add': 'Nova coleção',
        'empty': 'Nenhuma coleção criada.',
    },
    'wagtailredirects:index': {
        'title': 'Redirecionamentos',
        'description': 'Endereços antigos que levam para os novos. Os de notícias com URL trocada são criados sozinhos.',
        'add': 'Novo redirecionamento',
        'empty': 'Nenhum redirecionamento criado.',
    },
}


def list_header(context):
    """Dados do cabeçalho, ou None para manter o slim_header do Wagtail."""
    if context.get('nr_list'):
        return context['nr_list']
    request = context.get('request')
    view = context.get('view')
    match = getattr(request, 'resolver_match', None)
    if view is None or match is None:
        return None
    config = LISTS.get(match.view_name, {})
    add_url = getattr(view, 'add_url', None)

    primary = None
    secondary = []
    for button in context.get('header_buttons') or []:
        url = getattr(button, 'url', None)
        if add_url and url == add_url and primary is None:
            primary = {'label': config.get('add') or button.label, 'url': url}
        elif isinstance(button, BaseDropdownMenuButton) or not url:
            # Menu ⋯ (exportar, reordenar...): o componente do Wagtail, restilizado.
            secondary.append({'component': button})
        else:
            secondary.append({'label': button.label, 'url': url})

    return {
        'title': config.get('title') or context.get('header_title') or context.get('page_title') or '',
        'description': config.get('description', ''),
        'total': context.get('items_count'),
        'primary': primary,
        'secondary': secondary,
        'tabs': None,
    }


# A busca ao vivo e a paginação respondem por rotas "..._results".
RESULTS_SUFFIX = re.compile(r'_results$')


def empty_message(context):
    """Frase de lista vazia da seção, ou None para manter a do Wagtail."""
    match = getattr(context.get('request'), 'resolver_match', None)
    if match is None:
        return None
    config = LISTS.get(RESULTS_SUFFIX.sub('', match.view_name), {})
    if 'empty' not in config:
        return None
    if context.get('is_searching') or context.get('is_filtering'):
        return 'Nada encontrado com essa busca ou esses filtros.'
    return config['empty']
