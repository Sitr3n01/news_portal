"""Serviço do TikTok (TikTok Display API oficial).

Estrutura pronta para receber `access_token` (e `refresh_token`) reais. Sem token,
a sincronização falha de forma amigável (`TokenMissingError`). Nenhum scraping.
"""
import logging
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.utils import timezone as dj_timezone

from ..models import MediaType, Platform
from .base import SocialSyncError, TokenMissingError, request_json

logger = logging.getLogger(__name__)

VIDEO_LIST_URL = 'https://open.tiktokapis.com/v2/video/list/'
VIDEO_FIELDS = 'id,title,video_description,cover_image_url,share_url,create_time,duration'
TOKEN_URL = 'https://open.tiktokapis.com/v2/oauth/token/'


def fetch_tiktok_videos(account, limit=6):
    """Busca os últimos vídeos da conta na TikTok Display API.

    Devolve a lista de dicts crus de `data.videos`. Levanta `TokenMissingError`
    sem credenciais e `SocialSyncError` para falhas de rede/HTTP/parse.
    """
    token = (account.access_token or '').strip()
    if not token:
        # O refresh do token (refresh_token -> novo access_token) é um passo de
        # OAuth a implementar quando houver credenciais reais. Sem refresh_token,
        # ou sem token de acesso, não há o que sincronizar.
        raise TokenMissingError(
            'TikTok sem credenciais: configure o token de acesso no admin (ou via variável de ambiente).'
        )

    payload = request_json(
        'POST', VIDEO_LIST_URL,
        params={'fields': VIDEO_FIELDS},
        headers={'Authorization': f'Bearer {token}'},
        json={'max_count': limit},
    )
    error = payload.get('error') or {}
    code = (error.get('code') or 'ok').lower()
    if code not in ('', 'ok'):
        raise SocialSyncError(f"TikTok recusou a requisição: {error.get('message') or code}.")

    videos = (payload.get('data') or {}).get('videos')
    if not isinstance(videos, list):
        raise SocialSyncError('Resposta do TikTok sem a lista de vídeos esperada.')
    return videos


def refresh_tiktok_token(account):
    """Renova o access_token do TikTok com o refresh_token + credenciais do app.

    Precisa de `account.refresh_token` e de `settings.TIKTOK_CLIENT_KEY/SECRET`.
    Levanta `TokenMissingError` se faltar algo e `SocialSyncError` em falha de
    rede/HTTP/payload. Atualiza access_token, refresh_token e expiração na conta e
    devolve o novo access_token.
    """
    refresh_token = (account.refresh_token or '').strip()
    client_key = getattr(settings, 'TIKTOK_CLIENT_KEY', '') or ''
    client_secret = getattr(settings, 'TIKTOK_CLIENT_SECRET', '') or ''
    if not refresh_token or not client_key or not client_secret:
        raise TokenMissingError(
            'TikTok sem refresh_token ou credenciais do app (TIKTOK_CLIENT_KEY/SECRET) para renovar.'
        )

    payload = request_json(
        'POST', TOKEN_URL,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data={
            'client_key': client_key,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        },
    )
    if payload.get('error'):
        detail = payload.get('error_description') or payload.get('error')
        raise SocialSyncError(f'TikTok recusou a renovação do token: {detail}.')

    new_token = payload.get('access_token')
    if not new_token:
        raise SocialSyncError('TikTok não retornou um novo token na renovação.')

    account.access_token = new_token
    if payload.get('refresh_token'):
        account.refresh_token = payload['refresh_token']
    expires_in = payload.get('expires_in')
    if expires_in:
        account.token_expires_at = dj_timezone.now() + timedelta(seconds=int(expires_in))
    account.save(update_fields=['access_token', 'refresh_token', 'token_expires_at', 'updated_at'])
    return new_token


def _parse_create_time(value):
    """create_time é um Unix timestamp (segundos); devolve datetime UTC ou None."""
    if value in (None, ''):
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        return None


def normalize_tiktok_video(raw_video, account):
    """Converte um item cru do TikTok no dict canônico do SocialPost.

    Função pura e testável: tolera campos ausentes. TikTok é sempre vídeo.
    """
    external_id = str(raw_video.get('id') or '').strip()
    caption = raw_video.get('title') or raw_video.get('video_description') or ''
    return {
        'platform': Platform.TIKTOK,
        'external_id': external_id,
        'permalink': raw_video.get('share_url') or '',
        'caption': caption,
        'media_type': MediaType.VIDEO,
        'thumbnail_url': raw_video.get('cover_image_url') or '',
        'media_url': raw_video.get('share_url') or '',
        'published_at': _parse_create_time(raw_video.get('create_time')),
        'sync_payload': {
            'id': external_id,
            'create_time': raw_video.get('create_time'),
            'share_url': raw_video.get('share_url'),
            'duration': raw_video.get('duration'),
        },
    }
