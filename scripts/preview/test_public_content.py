"""Exercise the import's data protection and repeatability on disposable SQLite files."""
import json
import sqlite3

import pytest

from scripts.preview import apply_public_content as importer


@pytest.fixture
def preview(tmp_path):
    root = tmp_path / 'news_portal-komuniki-design'
    database = root / '.preview/local.sqlite3'
    database.parent.mkdir(parents=True)
    data = importer.load_manifest()
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE django_site (id INTEGER PRIMARY KEY, name TEXT)')
        connection.execute('INSERT INTO django_site VALUES (1, ?)', ('Komuniki',))
        columns = ', '.join(f'{field} {"INTEGER" if field == "social_section_enabled" else "TEXT"}' for field in importer.ALLOWED_FIELDS)
        connection.execute(f'CREATE TABLE common_siteextension (id INTEGER PRIMARY KEY, site_id INTEGER, {columns}, private_setting TEXT)')
        names = list(data['site_extension'])
        placeholders = ', '.join('?' for _ in names)
        connection.execute(
            f'INSERT INTO common_siteextension (id, site_id, {", ".join(names)}, private_setting) VALUES (2, 1, {placeholders}, ?)',
            [data['site_extension'][field]['before'] for field in names] + ['keep this setting'],
        )
        connection.execute('CREATE TABLE school_schoolfeature (id INTEGER PRIMARY KEY, site_id INTEGER, placement TEXT, title TEXT, is_active INTEGER, "order" INTEGER)')
        for index, title in enumerate([*data['home_features'], data['deactivate_feature']['title']], 1):
            connection.execute('INSERT INTO school_schoolfeature VALUES (?, 1, ?, ?, 1, ?)', (index, 'trust', title, index))
    return root, database


def test_dry_run_never_writes(preview):
    root, database = preview
    before = importer.digest(database)
    result = importer.run(root)
    assert len(result['changes']) == 10
    assert result['backup'] is None
    assert importer.digest(database) == before
    assert not (root / '.preview/backups').exists()


def test_apply_backup_and_idempotence(preview):
    root, database = preview
    before = importer.digest(database)
    result = importer.run(root, apply=True)
    with sqlite3.connect(result['backup']) as backup:
        assert backup.execute('SELECT is_active FROM school_schoolfeature WHERE id = 4').fetchone()[0] == 1
        assert backup.execute('SELECT primary_email FROM common_siteextension').fetchone()[0] == 'contato@exemplo.edu.br'
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT COUNT(*) FROM school_schoolfeature WHERE is_active = 1').fetchone()[0] == 3
        assert connection.execute('SELECT COUNT(*) FROM school_schoolfeature').fetchone()[0] == 4
        assert connection.execute('SELECT private_setting FROM common_siteextension').fetchone()[0] == 'keep this setting'
    assert importer.digest(database) != before
    after = importer.digest(database)
    assert importer.run(root, apply=True)['changes'] == []
    assert importer.digest(database) == after
    assert len(list((root / '.preview/backups').iterdir())) == 1


def test_unexpected_existing_value_is_preserved(preview):
    root, database = preview
    with sqlite3.connect(database) as connection:
        connection.execute('UPDATE common_siteextension SET primary_email = ?', ('edited@example.invalid',))
    before = importer.digest(database)
    with pytest.raises(ValueError, match='primary_email'):
        importer.run(root, apply=True)
    assert importer.digest(database) == before
    assert not (root / '.preview/backups').exists()


def test_failed_validation_rolls_back(preview, monkeypatch):
    root, database = preview
    original_plan = importer.plan_changes
    calls = 0

    def fail_after_writes(connection, data):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError('injected validation failure')
        return original_plan(connection, data)

    before = importer.digest(database)
    monkeypatch.setattr(importer, 'plan_changes', fail_after_writes)
    with pytest.raises(RuntimeError, match='injected'):
        importer.run(root, apply=True)
    assert importer.digest(database) == before


def test_cannot_target_original_worktree(tmp_path):
    with pytest.raises(ValueError, match='isolated'):
        importer.run(tmp_path / 'news_portal', apply=True)


def test_manifest_rejects_fields_outside_allowlist(tmp_path, monkeypatch):
    data = importer.load_manifest()
    data['site_extension']['newsletter_from_email'] = {'before': '', 'value': 'wrong@example.invalid'}
    manifest = tmp_path / 'invalid.json'
    manifest.write_text(json.dumps(data), encoding='utf-8')
    monkeypatch.setattr(importer, 'MANIFEST', manifest)
    with pytest.raises(ValueError, match='fields'):
        importer.load_manifest()
