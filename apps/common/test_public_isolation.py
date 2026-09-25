"""Views públicas nunca contornam o isolamento por Site (auditoria, ISO-01).

O mecanismo de isolamento do projeto é o Sites framework: modelos com FK
`site` expõem `on_site` (CurrentSiteManager). Buscar por `Model.objects` ou
passar o modelo direto para get_object_or_404 numa view pública ignora o Site
atual — o que antes deixava leitores alcançarem notícias de outro portal por
ID. Este teste lê o código das views e falha no primeiro desvio.
"""

import ast
from pathlib import Path

from django.apps import apps
from django.conf import settings

PUBLIC_MODULES = [
    'apps/news/views.py',
    'apps/news/feeds.py',
    'apps/news/sitemaps.py',
    'apps/news/utils.py',
    'apps/school/views.py',
    'apps/school/sitemaps.py',
    'apps/contact/views.py',
    'apps/common/social_section.py',
]
SHORTCUTS = {'get_object_or_404', 'get_list_or_404'}


def _site_models():
    return {model.__name__ for model in apps.get_models() if hasattr(model, 'on_site')}


def _violations(source, site_models):
    tree = ast.parse(source)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute) and node.attr == 'objects'
            and isinstance(node.value, ast.Name) and node.value.id in site_models
        ):
            parent = parents.get(node)
            # `Model.objects.none()` é o único uso aceito: não lê nada do banco.
            if not (isinstance(parent, ast.Attribute) and parent.attr == 'none'):
                yield node.lineno, f'{node.value.id}.objects'
        if (
            isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in SHORTCUTS
            and node.args and isinstance(node.args[0], ast.Name) and node.args[0].id in site_models
        ):
            yield node.lineno, f'{node.func.id}({node.args[0].id}, ...)'


def test_public_views_only_query_site_models_through_on_site():
    site_models = _site_models()
    assert {'Article', 'Page', 'SchoolFeature'} <= site_models
    offenders = [
        f'{module}:{line} {usage}'
        for module in PUBLIC_MODULES
        for line, usage in _violations((Path(settings.BASE_DIR) / module).read_text(encoding='utf-8'), site_models)
    ]
    assert offenders == []


def test_guard_catches_the_bypass_it_exists_for():
    code = 'a = get_object_or_404(Article, id=1)\nb = Article.objects.filter(pk=1)\nc = Article.objects.none()\n'
    assert [usage for _, usage in _violations(code, {'Article'})] == ['get_object_or_404(Article, ...)', 'Article.objects']
