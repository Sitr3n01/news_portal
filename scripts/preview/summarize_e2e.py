"""Summarize completed browser journeys and require the full declared viewport matrix."""
import json
import re
from datetime import UTC, datetime
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / '.preview/evidence/hover-e2e'
runner = (ROOT / 'scripts/preview/browser_e2e.mjs').read_text(encoding='utf-8')
matrix_source = runner.split('export const VIEWPORTS = [', 1)[1].split('].map', 1)[0]
viewports = [(int(width), int(height)) for width, height in re.findall(r'\[(\d+),\s*(\d+)\]', matrix_source)]
expected = {(width, height, dark, language) for (width, height), dark, language
            in product(viewports, (False, True), ('pt-BR', 'en'))}
attempts = [
    json.loads(line) for line in (OUTPUT / 'matrix-v5.jsonl').read_text(encoding='utf-8').splitlines() if line
]
latest = {}
excluded = []
for record in attempts:
    size = record['viewport']
    if not isinstance(size, dict):
        excluded.append({'viewport': size, 'reason': 'Invalid runner argument; no browser actions executed.'})
        continue
    key = (size['width'], size['height'], record['dark'], record['language'])
    if key not in expected:
        excluded.append({
            'viewport': size, 'dark': record['dark'], 'language': record['language'],
            'reason': 'Requested 5120px exceeded the browser viewport cap of 4096px.',
            'observed_client_widths': sorted({page['clientWidth'] for page in record['pages']}),
        })
        continue
    latest[key] = record
records = list(latest.values())
missing = sorted(expected - latest.keys())
failures = [record for record in records if not record['passed']]
height_mismatches = [
    {'viewport': record['viewport'], 'page': page['label'], 'height': page['clientHeight']}
    for record in records for page in record['pages']
    if page['clientHeight'] != record['viewport']['height']
]
summary = {
    'generated_at': datetime.now(UTC).isoformat(),
    'viewport_count': len(viewports),
    'viewports': [{'width': width, 'height': height} for width, height in viewports],
    'expected_journeys': len(expected),
    'completed_journeys': len(records),
    'page_checks': sum(len(record['pages']) for record in records),
    'interaction_checks': sum(len(record['interactions']) for record in records),
    'attempts': len(attempts),
    'excluded_attempts': excluded,
    'interrupted_attempts': [
        {'viewport': record['viewport'], 'dark': record['dark'], 'language': record['language'],
         'completed_pages': len(record['pages']), 'error': record['error'][:160]}
        for record in attempts if record.get('error') and isinstance(record['viewport'], dict)
    ],
    'missing_cases': missing,
    'failed_cases': failures,
    'height_mismatches': height_mismatches,
    'passed': not missing and not failures and not height_mismatches and set(latest) == expected,
    'scope': 'Real browser navigation, keyboard, forms and rendered layout through the CUA runtime.',
    'limitations': [
        'CSS viewport sizes on the local Chromium browser; physical devices and other browser engines were not emulated.',
        'Touch and reduced-motion guards are present in CSS; this runtime cannot override those media features.',
        'The finite matrix covers representative sizes and breakpoint boundaries, not every possible resolution.',
        '5120px requests were clamped to 4096px by the browser; coverage ends at 4096 CSS pixels.',
        'One test tab crashed during a long sequence. Interrupted cases were retried in a fresh tab; the cause is undetermined.',
    ],
}
(OUTPUT / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps({key: value for key, value in summary.items() if key not in {'viewports', 'failed_cases'}}, indent=2))
raise SystemExit(0 if summary['passed'] else 1)
