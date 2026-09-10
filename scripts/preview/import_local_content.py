"""Copy the original local content into a new, isolated review dataset."""
import hashlib
import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / 'news_portal'
PREVIEW = ROOT / '.preview'
PUBLIC_TABLES = (
    'django_site', 'common_siteextension', 'school_page', 'school_schoolhomeconfig',
    'school_schoolfeature', 'school_teammember', 'school_testimonial', 'social_socialpost',
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_database(source, destination):
    if not source.is_file() or destination.exists():
        raise RuntimeError('Source must exist and destination must be new: ' + str(destination))
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as original:
        with sqlite3.connect(destination) as copied:
            original.backup(copied)
            if copied.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('Copied database failed integrity_check.')


def public_inventory(path):
    result = {}
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as database:
        for table in PUBLIC_TABLES:
            # Table names are the fixed internal allowlist above, never user input.
            rows = database.execute(f'SELECT * FROM "{table}" ORDER BY id').fetchall()
            serialized = json.dumps(rows, ensure_ascii=False, default=str)
            result[table] = {'count': len(rows), 'sha256': hashlib.sha256(serialized.encode()).hexdigest()}
    return result


def media_inventory(directory):
    return {str(path.relative_to(directory)): digest(path) for path in sorted(directory.rglob('*')) if path.is_file()}


def main():
    if ROOT.resolve() == SOURCE.resolve() or ROOT.name != 'news_portal-komuniki-design':
        raise RuntimeError('Run only inside the isolated design worktree.')
    destination = PREVIEW / 'local.sqlite3'
    media_destination = PREVIEW / 'local-media'
    manifest = PREVIEW / 'local-source.json'
    if manifest.exists():
        print('Local content was already imported; existing review data retained. See ' + str(manifest))
        return
    if destination.exists() or media_destination.exists():
        raise RuntimeError('An incomplete local copy exists; inspect it before importing again.')

    source_database = SOURCE / 'db.sqlite3'
    source_hash = digest(source_database)
    demo_hash = digest(PREVIEW / 'demo.sqlite3')
    source_media = media_inventory(SOURCE / 'media')
    backup = PREVIEW / 'backups' / ('before-local-content-' + datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ'))
    backup.mkdir(parents=True)
    copy_database(PREVIEW / 'demo.sqlite3', backup / 'demo.sqlite3')
    shutil.copytree(PREVIEW / 'demo-media', backup / 'demo-media')
    copy_database(source_database, destination)
    shutil.copytree(SOURCE / 'media', media_destination)

    original = public_inventory(source_database)
    imported = public_inventory(destination)
    report = {
        'imported_at': datetime.now(UTC).isoformat(),
        'source': str(source_database), 'destination': str(destination),
        'demo_backup': str(backup),
        'source_sha256_before': source_hash, 'source_sha256_after': digest(source_database),
        'source_unchanged': source_hash == digest(source_database),
        'demo_unchanged': demo_hash == digest(PREVIEW / 'demo.sqlite3'),
        'public_content': imported, 'public_content_matches_source': original == imported,
        'media_file_count': len(source_media),
        'media_matches_source': source_media == media_inventory(media_destination),
        'database_integrity': 'ok',
        'note': 'Original local content, including existing example contacts; no production synchronization.',
    }
    report['passed'] = all(report[key] for key in (
        'source_unchanged', 'demo_unchanged', 'public_content_matches_source', 'media_matches_source',
    ))
    evidence = PREVIEW / 'evidence/local-content-import.json'
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if not report['passed']:
        raise RuntimeError('Import verification failed; review remains on the previous dataset.')
    manifest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
