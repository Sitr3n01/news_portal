"""Resolver de embeds de redes sociais → iframe seguro + thumbnail.

Ponto único e extensível para anexar vídeos/posts em artigos. Cada plataforma é
um "matcher" de URL; adicionar uma nova (Vimeo, X, …) é só registrar mais um.

Por que aqui e não no HTML do usuário: os embeds dos artigos são montados a
partir destes dados estruturados (provider + id) e renderizados por templates
confiáveis. A URL da plataforma nunca entra como HTML cru, então não há iframe
de origem arbitrária — só os domínios já liberados no CSP (frame-src).

Política de thumbnail: o YouTube tem thumbnail determinística (i.ytimg.com), então
usamos direto. Instagram e TikTok não expõem thumbnail pública sem token/scraping,
então o facade usa um placeholder de marca (ver templates/news/partials/blocks/).
"""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class EmbedData:
    """Dados normalizados de um embed, prontos para o template do facade."""
    provider: str         # chave estável: 'youtube' | 'instagram' | 'tiktok'
    provider_label: str   # rótulo de exibição: 'YouTube' | 'Instagram' | 'TikTok'
    embed_id: str         # id do vídeo/post extraído da URL
    embed_url: str         # src do iframe (carregado só no clique do facade)
    thumbnail_url: str    # '' quando não há thumbnail pública (usa placeholder)
    aspect: str           # proporção do container, ex.: '16/9', '9/16', '4/5'


# ── YouTube ──────────────────────────────────────────────────────────────────
# Cobre watch?v=, youtu.be/, /shorts/ e /embed/. O id do YouTube tem 11 chars.
_YOUTUBE_RE = re.compile(
    r'(?:youtube\.com/(?:watch\?(?:[^&\s]*&)*v=|shorts/|embed/|live/)|youtu\.be/)'
    r'([A-Za-z0-9_-]{11})'
)


def _match_youtube(url):
    match = _YOUTUBE_RE.search(url)
    if not match:
        return None
    vid = match.group(1)
    return EmbedData(
        provider='youtube',
        provider_label='YouTube',
        embed_id=vid,
        embed_url=f'https://www.youtube-nocookie.com/embed/{vid}',
        thumbnail_url=f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg',
        aspect='16/9',
    )


# ── Instagram ────────────────────────────────────────────────────────────────
# Posts (/p/), reels (/reel/) e IGTV (/tv/). O shortcode é alfanumérico com - e _.
_INSTAGRAM_RE = re.compile(
    r'instagram\.com/(?:[A-Za-z0-9_.-]+/)?(?:p|reel|tv)/([A-Za-z0-9_-]+)'
)


def _match_instagram(url):
    match = _INSTAGRAM_RE.search(url)
    if not match:
        return None
    code = match.group(1)
    return EmbedData(
        provider='instagram',
        provider_label='Instagram',
        embed_id=code,
        embed_url=f'https://www.instagram.com/p/{code}/embed/',
        thumbnail_url='',
        aspect='4/5',
    )


# ── TikTok ───────────────────────────────────────────────────────────────────
# URL canônica de vídeo: tiktok.com/@usuario/video/<id numérico>.
_TIKTOK_RE = re.compile(r'tiktok\.com/@[A-Za-z0-9_.-]+/video/(\d+)')


def _match_tiktok(url):
    match = _TIKTOK_RE.search(url)
    if not match:
        return None
    vid = match.group(1)
    return EmbedData(
        provider='tiktok',
        provider_label='TikTok',
        embed_id=vid,
        embed_url=f'https://www.tiktok.com/embed/v2/{vid}',
        thumbnail_url='',
        aspect='9/16',
    )


# Ordem importa pouco (os domínios não se sobrepõem); registrar novos aqui.
_PROVIDERS = (_match_youtube, _match_instagram, _match_tiktok)


def resolve_embed(url):
    """URL pública → EmbedData, ou None se nenhuma plataforma for reconhecida."""
    if not url:
        return None
    url = url.strip()
    for matcher in _PROVIDERS:
        data = matcher(url)
        if data is not None:
            return data
    return None
