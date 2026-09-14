"""Apply the reviewed public snapshot only to the isolated local preview database."""
import argparse
import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name('komuniki-public-content.json')
ALLOWED_FIELDS = frozenset({
    'tagline', 'primary_email', 'phone_number', 'address', 'instagram_url',
    'youtube_url', 'facebook_url', 'social_section_enabled', 'social_section_title',
})


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest():
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if data['schema_version'] != 1 or set(data['site_extension']) != ALLOWED_FIELDS:
        raise ValueError('Unexpected manifest version or fields; nothing was changed.')
    if data['site'] != {'id': 1, 'name': 'Komuniki'}:
        raise ValueError('Unexpected target site.')
    if data['deactivate_feature'] != {'placement': 'trust', 'title': 'Projeto Jovem Comunicador'}:
        raise ValueError('Unexpected feature target.')
    for field, change in data['site_extension'].items():
        expected_type = bool if field == 'social_section_enabled' else str
        if any(type(change[key]) is not expected_type for key in ('before', 'value')):
            raise ValueError('Unexpected value type: ' + field)
    return data


def plan_changes(connection, data):
    site_id = data['site']['id']
    site = connection.execute('SELECT name FROM django_site WHERE id = ?', (site_id,)).fetchone()
    if site is None or site['name'] != data['site']['name']:
        raise ValueError('Expected Komuniki site was not found.')
    columns = ', '.join(sorted(ALLOWED_FIELDS))
    rows = connection.execute(f'SELECT id, {columns} FROM common_siteextension WHERE site_id = ?', (site_id,)).fetchall()
    if len(rows) != 1:
        raise ValueError('Expected exactly one site configuration.')
    extension = rows[0]
    changes = []
    for field, change in data['site_extension'].items():
        current = extension[field]
        if current == change['value']:
            continue
        if current != change['before']:
            raise ValueError('Unexpected existing content; review before overwriting: ' + field)
        changes.append({'table': 'common_siteextension', 'id': extension['id'], 'field': field, 'before': current, 'after': change['value']})
    feature = data['deactivate_feature']
    rows = connection.execute(
        'SELECT id, is_active FROM school_schoolfeature WHERE site_id = ? AND placement = ? AND title = ?',
        (site_id, feature['placement'], feature['title']),
    ).fetchall()
    if len(rows) != 1:
        raise ValueError('Expected exactly one Jovem Comunicador Home card.')
    if rows[0]['is_active']:
        changes.append({'table': 'school_schoolfeature', 'id': rows[0]['id'], 'field': 'is_active', 'before': 1, 'after': 0})
    active = connection.execute(
        'SELECT title FROM school_schoolfeature WHERE site_id = ? AND placement = ? AND is_active = 1 ORDER BY "order", title',
        (site_id, 'trust'),
    ).fetchall()
    if [row['title'] for row in active if row['title'] != feature['title']] != data['home_features']:
        raise ValueError('The remaining Home cards differ from the reviewed source.')
    return changes


def run(root=ROOT, *, apply=False):
    root = root.resolve()
    database = root / '.preview/local.sqlite3'
    # No CLI database override: this command must never point at production/current/demo.
    if root.name != 'news_portal-komuniki-design' or database.resolve() != database or not database.is_file():
        raise ValueError('Expected an existing, isolated .preview/local.sqlite3 database.')
    data = load_manifest()
    mode = 'rw' if apply else 'ro'
    before_hash = digest(database)
    with sqlite3.connect(database.as_uri() + '?mode=' + mode, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute('BEGIN IMMEDIATE' if apply else 'BEGIN')
        changes = plan_changes(connection, data)
        report = {
            'mode': 'apply' if apply else 'dry-run', 'database': str(database),
            'manifest_sha256': digest(MANIFEST), 'source_url': data['source_url'],
            'consulted_on': data['consulted_on'], 'changes': changes, 'backup': None,
            'database_sha256_before': before_hash,
        }
        if apply and changes:
            backup_root = root / '.preview/backups'
            if not backup_root.resolve().is_relative_to(root / '.preview'):
                raise ValueError('Backup location must stay inside the preview directory.')
            backup = backup_root / ('before-official-content-' + datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ'))
            backup.mkdir(parents=True)
            backup_database = backup / 'local.sqlite3'
            # A separate reader can back up while BEGIN IMMEDIATE prevents other writers.
            with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as source:
                with sqlite3.connect(backup_database) as destination:
                    source.backup(destination)
                    if destination.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise RuntimeError('Backup integrity check failed.')
            report['backup'] = str(backup_database)
            report['backup_sha256'] = digest(backup_database)
            for change in changes:
                # All identifiers originate from the fixed allowlist/targets above.
                connection.execute(
                    f'UPDATE {change["table"]} SET {change["field"]} = ? WHERE id = ?',
                    (change['after'], change['id']),
                )
            if plan_changes(connection, data) or connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('Post-application validation failed; transaction will roll back.')
            # Save restoration information before committing; failure leaves the DB untouched.
            (backup / 'changes.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            connection.commit()
        else:
            connection.rollback()
    report['database_sha256_after'] = digest(database)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Apply changes after creating a backup. Default: read-only dry run.')
    arguments = parser.parse_args()
    print(json.dumps(run(apply=arguments.apply), ensure_ascii=True, indent=2))
