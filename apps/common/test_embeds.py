"""Testes do resolver de embeds (apps/common/embeds.py)."""
import pytest

from apps.common.embeds import resolve_embed


# ── YouTube ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize('url', [
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'https://youtube.com/watch?v=dQw4w9WgXcQ&t=42s',
    'https://youtu.be/dQw4w9WgXcQ',
    'https://www.youtube.com/shorts/dQw4w9WgXcQ',
    'https://www.youtube.com/embed/dQw4w9WgXcQ',
])
def test_resolves_youtube_variants(url):
    data = resolve_embed(url)
    assert data is not None
    assert data.provider == 'youtube'
    assert data.embed_id == 'dQw4w9WgXcQ'
    assert data.embed_url == 'https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ'
    assert data.thumbnail_url == 'https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg'
    assert data.aspect == '16/9'


# ── Instagram ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize('url,code', [
    ('https://www.instagram.com/p/CabcDEF123/', 'CabcDEF123'),
    ('https://instagram.com/reel/XYz-9_8/', 'XYz-9_8'),
    ('https://www.instagram.com/kellyfarias/p/CabcDEF123/', 'CabcDEF123'),
])
def test_resolves_instagram(url, code):
    data = resolve_embed(url)
    assert data is not None
    assert data.provider == 'instagram'
    assert data.embed_id == code
    assert data.embed_url == f'https://www.instagram.com/p/{code}/embed/'
    assert data.thumbnail_url == ''  # facade de marca
    assert data.aspect == '4/5'


# ── TikTok ───────────────────────────────────────────────────────────────────

def test_resolves_tiktok():
    data = resolve_embed('https://www.tiktok.com/@kelly/video/7212345678901234567')
    assert data is not None
    assert data.provider == 'tiktok'
    assert data.embed_id == '7212345678901234567'
    assert data.embed_url == 'https://www.tiktok.com/embed/v2/7212345678901234567'
    assert data.aspect == '9/16'


# ── Não reconhecidos ─────────────────────────────────────────────────────────

@pytest.mark.parametrize('url', [
    '',
    None,
    'https://example.com/post/123',
    'https://vimeo.com/123456',  # ainda não suportado
    'texto qualquer sem url',
])
def test_returns_none_for_unsupported(url):
    assert resolve_embed(url) is None
