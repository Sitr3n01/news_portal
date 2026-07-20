"""Reclassifica o file_type de arquivos já existentes com a detecção atual.

A allowlist de upload passou a excluir .svg (e afins) e o admin deixou de
tratar .svg como imagem — mas linhas antigas persistidas continuavam com
file_type='image' e renderizavam <img> na changelist. Esta migração de dados
regrava o file_type de todos os MediaFile usando a mesma lógica de detecção
por extensão do admin (reimplementada aqui de propósito: migração não deve
importar código do admin, que muda com o tempo).

Reversa: noop — voltar a versão do código não exige restaurar classificações
antigas, e a detecção anterior não é recuperável a partir dos dados.
"""
from pathlib import Path

from django.db import migrations

_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
_DOCUMENT_EXTS = {'.pdf', '.doc', '.docx', '.odt', '.txt', '.rtf', '.xls', '.xlsx', '.csv', '.ppt', '.pptx'}
_VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.webm', '.mkv'}
_AUDIO_EXTS = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'}


def _detect_file_type(name):
    ext = Path(name or '').suffix.lower()
    if ext in _IMAGE_EXTS:
        return 'image'
    if ext in _DOCUMENT_EXTS:
        return 'document'
    if ext in _VIDEO_EXTS:
        return 'video'
    if ext in _AUDIO_EXTS:
        return 'audio'
    return 'other'


def refresh_file_types(apps, schema_editor):
    media_file_model = apps.get_model('media_library', 'MediaFile')
    changed = []
    for media in media_file_model.objects.all().iterator():
        detected = _detect_file_type(media.file.name if media.file else '')
        if media.file_type != detected:
            media.file_type = detected
            changed.append(media)
    if changed:
        media_file_model.objects.bulk_update(changed, ['file_type'], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('media_library', '0002_pt_br_admin_labels'),
    ]

    operations = [
        migrations.RunPython(refresh_file_types, migrations.RunPython.noop),
    ]
