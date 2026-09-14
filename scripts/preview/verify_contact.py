"""Exercise rejected HTTP submissions without creating inquiries or bypassing CSRF."""
import hashlib
import json
import os
import sqlite3
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / 'news_portal'
SCENARIO = os.environ.get('KOMUNIKI_PREVIEW_SCENARIO', 'demo')
if SCENARIO not in {'current', 'demo', 'local'}:
    raise ValueError('Unknown preview scenario.')
URL = 'http://127.0.0.1:' + ('8011' if SCENARIO == 'current' else '8012') + '/contact/'
DATABASES = {
    'original': SOURCE / 'db.sqlite3',
    'current': ROOT / '.preview/current.sqlite3',
    'demo': ROOT / '.preview/demo.sqlite3',
}
if (ROOT / '.preview/local.sqlite3').is_file():
    DATABASES['local'] = ROOT / '.preview/local.sqlite3'


def snapshot():
    result = {}
    for name, path in DATABASES.items():
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as database:
            result[name] = {
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'inquiries': database.execute('SELECT COUNT(*) FROM contact_contactinquiry').fetchone()[0],
                'browser_test_rows': database.execute(
                    'SELECT COUNT(*) FROM contact_contactinquiry WHERE email = ?',
                    ('visual-test@example.invalid',),
                ).fetchone()[0],
            }
    return result


def submit(overrides, *, csrf=True):
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    with opener.open(URL, timeout=15) as response:
        soup = BeautifulSoup(response.read(), 'html.parser')
    data = {
        'name': 'Teste HTTP local',
        'email': 'http-test@example.invalid',
        'phone': '',
        'subject': 'general',
        'message': 'Verificação local: este envio deve ser rejeitado.',
    }
    if csrf:
        data['csrfmiddlewaretoken'] = soup.select_one('[name=csrfmiddlewaretoken]')['value']
    data.update(overrides)
    request = Request(URL, data=urlencode(data).encode(), headers={'Referer': URL}, method='POST')
    try:
        with opener.open(request, timeout=15) as response:
            return response.status, response.read().decode()
    except HTTPError as error:
        return error.code, error.read().decode()


before = snapshot()
cases = []
for name, data, fields in (
    ('missing_turnstile', {}, []),
    ('invalid_fields', {'name': '', 'email': 'invalid', 'message': ''}, ['name', 'email', 'message']),
    ('invalid_subject', {'subject': 'not-a-public-choice'}, ['subject']),
):
    status, html = submit(data)
    soup = BeautifulSoup(html, 'html.parser')
    field_errors = {
        field: bool(soup.select_one(f'#id_{field}').parent.select_one('.ed-error-text'))
        for field in fields
    }
    cases.append({
        'case': name,
        'status': status,
        'field_errors': field_errors,
        'passed': status == 200 and 'Confirme a verificação anti-bot' in html and all(field_errors.values()),
    })
status, _ = submit({}, csrf=False)
cases.append({'case': 'missing_csrf', 'status': status, 'passed': status == 403})
after = snapshot()
report = {
    'scenario': SCENARIO,
    'cases': cases,
    'databases_before': before,
    'databases_after': after,
    'no_database_changes_from_rejected_requests': before == after,
    'browser_test_saved_only_in_demo': (
        after['demo']['browser_test_rows'] == 1
        and all(value['browser_test_rows'] == 0 for name, value in after.items() if name != 'demo')
    ),
}
report['passed'] = (
    all(case['passed'] for case in cases)
    and report['no_database_changes_from_rejected_requests']
    and report['browser_test_saved_only_in_demo']
)
suffix = '' if SCENARIO == 'demo' else '-' + SCENARIO
destination = ROOT / f'.preview/evidence/contact-isolation{suffix}.json'
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
raise SystemExit(0 if report['passed'] else 1)
