"""Compare the local rendering with a public DOM capture made through the browser."""
import contextlib
import io
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.design_preview'
os.environ['KOMUNIKI_PREVIEW_SCENARIO'] = 'local'

from scripts.preview.export_school_content import main as export_content  # noqa: E402


def normalize(text):
    return re.sub(r'\s+', ' ', text).strip().casefold()


def expression(text):
    return re.sub(r'\\u([0-9a-fA-F]{4})', lambda match: chr(int(match[1], 16)), text)


def main():
    evidence = ROOT / '.preview/evidence/official-content'
    source = json.loads((evidence / 'published-pages.json').read_text(encoding='utf-8'))
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        export_content()
    local = json.loads(capture.getvalue())
    results = []
    for route, before in source['pages'].items():
        soup = BeautifulSoup(local['rendered_pages'][route], 'html.parser')
        for node in soup(['script', 'style']):
            node.decompose()
        text = normalize(soup.body.get_text(' ', strip=True))
        base_url = urljoin(source['source'], route)
        links = {urljoin(base_url, node['href']) for node in soup.select('a[href]')}
        images = {urljoin(base_url, node['src']) for node in soup.select('img[src]')}
        translations = {expression(node['x-text']) for node in soup.select('[x-text]')}
        missing = {
            'text': [line for line in before['text'].splitlines() if normalize(line) and normalize(line) not in text],
            'translations': sorted({expression(node['expression']) for node in before['translations']} - translations),
            'links': sorted({node['href'] for node in before['links']} - links),
            'images': sorted({node['src'] for node in before['images']} - images),
        }
        expected_description = next(node['content'] for node in before['metadata'] if node['name'] == 'description')
        examples = ('@exemplo.', 'instagram.com/exemplo', 'youtube.com/exemplo', 'teste fase', '99999-9999', 'rua da educação')
        placeholders = [value for value in examples if value in text or value in str(soup).casefold()]
        checks = {
            'title': soup.title.get_text() == before['title'],
            'description': soup.select_one('meta[name="description"]')['content'] == expected_description,
            'no_examples': not placeholders,
            'source_preserved': not any(missing.values()),
        }
        if route == '/':
            main_text = normalize(soup.main.get_text(' ', strip=True))
            checks.update({
                'young_card_removed': 'jovem comunicador' not in main_text,
                'test_social_hidden': soup.select_one('#social-section-title') is None,
                'approved_hero_preserved': bool(soup.select_one('img[src="/static/images/komuniki-editorial-hero.png"]')),
            })
        if route == '/sobre/':
            checks['institutional_project_preserved'] = 'jovem comunicador' in normalize(soup.main.get_text(' ', strip=True))
        if route == '/cursos/':
            checks['six_courses'] = len(soup.select('.ed-course-group article')) == 6
        if route == '/contact/':
            fields = [
                {'tag': node.name.upper(), 'name': node.get('name'), 'type': node.get('type', 'select-one' if node.name == 'select' else node.name), 'required': node.has_attr('required')}
                for node in soup.select('input:not([type="hidden"]),select,textarea')
            ]
            checks['form_contract'] = fields == [{key: node[key] for key in ('tag', 'name', 'type', 'required')} for node in before['fields']]
        results.append({'route': route, 'checks': checks, 'missing': missing, 'placeholders': placeholders, 'passed': all(checks.values())})
    report = {'source': source['source'], 'consulted_on': source['consulted_on'], 'pages': results, 'passed': all(page['passed'] for page in results)}
    (evidence / 'parity.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
