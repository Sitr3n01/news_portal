"""Verify form failure paths with controlled provider replies and a read-only DB."""
import hashlib
import io
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.design_preview'
os.environ.setdefault('KOMUNIKI_PREVIEW_SCENARIO', 'demo')

import django  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402
from django.conf import settings  # noqa: E402

database = Path(settings.DATABASES['default']['NAME'])
settings.DATABASES['default']['NAME'] = database.as_uri() + '?mode=ro'
settings.DATABASES['default']['OPTIONS'] = {'uri': True}
django.setup()

from django.test import Client  # noqa: E402

before = hashlib.sha256(database.read_bytes()).hexdigest()
cases = []
for scenario in ('provider_rejected', 'provider_timeout', 'provider_invalid_json'):
    client = Client(enforce_csrf_checks=True, HTTP_HOST='127.0.0.1')
    response = client.get('/contact/')
    soup = BeautifulSoup(response.content, 'html.parser')
    data = {
        'csrfmiddlewaretoken': soup.select_one('[name=csrfmiddlewaretoken]')['value'],
        'name': 'Teste isolado de falha',
        'email': 'provider-failure@example.invalid',
        'phone': '',
        'subject': 'general',
        'message': 'Este envio sintético deve ser rejeitado.',
        'cf-turnstile-response': 'synthetic-provider-failure-token',
    }
    options = (
        {'side_effect': TimeoutError('Synthetic local preview timeout')}
        if scenario == 'provider_timeout'
        else {'return_value': io.BytesIO(b'{"success":false}' if scenario == 'provider_rejected' else b'invalid')}
    )
    with patch('apps.common.turnstile.urlopen', **options) as provider:
        response = client.post('/contact/', data)
    cases.append({
        'case': scenario,
        'provider_called': provider.call_count == 1,
        'status': response.status_code,
        'error_visible': 'Confirme a verificação anti-bot' in response.content.decode(),
    })
after = hashlib.sha256(database.read_bytes()).hexdigest()
report = {
    'scenario': settings.DESIGN_PREVIEW_SCENARIO,
    'cases': cases,
    'database_opened_read_only': True,
    'database_unchanged': before == after,
    'passed': before == after and all(
        case['provider_called'] and case['status'] == 200 and case['error_visible'] for case in cases
    ),
}
suffix = '' if settings.DESIGN_PREVIEW_SCENARIO == 'demo' else '-' + settings.DESIGN_PREVIEW_SCENARIO
destination = ROOT / f'.preview/evidence/turnstile-failures{suffix}.json'
destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
raise SystemExit(0 if report['passed'] else 1)
