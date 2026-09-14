"""Compare the old and new templates against the same read-only preview data."""
import hashlib
import json
import os
import re
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / 'news_portal'
sys.path.insert(0, str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.design_preview'
os.environ.setdefault('KOMUNIKI_PREVIEW_SCENARIO', 'current')

import django  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402
from django.conf import settings  # noqa: E402

settings.DATABASES['default']['NAME'] = Path(settings.DATABASES['default']['NAME']).as_uri() + '?mode=ro'
settings.DATABASES['default']['OPTIONS'] = {'uri': True}
settings.ALLOWED_HOSTS += ['testserver']
django.setup()

from django.test import Client, override_settings  # noqa: E402

from apps.school.models import Page  # noqa: E402


def normalize(text):
    return re.sub(r'\s+', ' ', text).strip()


def inventory(html):
    soup = BeautifulSoup(html, 'html.parser')
    for element in soup(['script', 'style']):
        element.decompose()
    main = soup.find('main')
    return {
        'text_fragments': sorted({normalize(str(text)) for text in main.stripped_strings if normalize(str(text))}),
        'all_text': normalize(main.get_text(' ', strip=True)),
        'links': sorted({link.get('href') for link in soup.select('a[href]')}),
        'images': sorted({image.get('src') for image in soup.select('img[src]')}),
        'translations': sorted({element.get('x-text') for element in soup.select('[x-text]')}),
        'fields': [
            {'name': field.get('name'), 'type': field.get('type', field.name), 'required': field.has_attr('required')}
            for field in soup.select('form input, form select, form textarea')
        ],
    }


report = {'scenario': settings.DESIGN_PREVIEW_SCENARIO, 'pages': [], 'unchanged_shared_files': []}
routes = ['/', '/sobre/', '/cursos/', '/contact/', '/privacidade/']
routes.extend(
    f'/{slug}/' for slug in Page.objects.filter(site_id=settings.SITE_ID, is_published=True).values_list('slug', flat=True)
    if f'/{slug}/' not in routes
)
for route in routes:
    original_templates = deepcopy(settings.TEMPLATES)
    original_templates[0]['DIRS'] = [SOURCE / 'templates']
    with override_settings(TEMPLATES=original_templates):
        original_response = Client().get(route)
        before = inventory(original_response.content.decode('utf-8'))
    updated_response = Client().get(route)
    after = inventory(updated_response.content.decode('utf-8'))
    missing = {
        'text': [text for text in before['text_fragments'] if text not in after['all_text']],
        'links': sorted(set(before['links']) - set(after['links'])),
        'images': sorted(set(before['images']) - set(after['images'])),
        'translations': sorted(set(before['translations']) - set(after['translations'])),
    }
    result = {
        'route': route, 'original_status': original_response.status_code,
        'updated_status': updated_response.status_code,
        'original_text_fragments': len(before['text_fragments']),
        'original_link_destinations': len(before['links']),
        'missing': missing,
        'form_contract_preserved': before['fields'] == after['fields'],
    }
    result['passed'] = not any(missing.values()) and result['form_contract_preserved'] and original_response.status_code == updated_response.status_code == 200
    report['pages'].append(result)

for relative in (
    'templates/base_news.html',
    'templates/components/social_feed.html', 'templates/components/social_post_card.html',
    'apps/school/views.py', 'apps/school/models.py', 'apps/contact/views.py',
    'apps/contact/forms.py', 'config/urls.py',
):
    original_hash = hashlib.sha256((SOURCE / relative).read_bytes()).hexdigest()
    current_hash = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    report['unchanged_shared_files'].append({'path': relative, 'identical': original_hash == current_hash})

report['passed'] = all(page['passed'] for page in report['pages']) and all(item['identical'] for item in report['unchanged_shared_files'])
evidence = ROOT / '.preview/evidence'
evidence.mkdir(exist_ok=True)
suffix = '' if settings.DESIGN_PREVIEW_SCENARIO == 'current' else '-' + settings.DESIGN_PREVIEW_SCENARIO
(evidence / f'content-parity{suffix}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=True, indent=2))
sys.exit(0 if report['passed'] else 1)
