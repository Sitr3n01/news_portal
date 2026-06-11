"""Serviço do Instagram (API oficial da Meta — Instagram Graph API).

Estrutura pronta para receber `access_token` + `external_user_id` reais. Sem
credenciais, a sincronização falha de forma amigável (`TokenMissingError`) sem
quebrar nada. Nenhum scraping: usamos apenas o endpoint oficial de mídia.
"""
import logging
from datetime import datetime, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ..models import MediaType, Platform
from .base import SocialSyncError, TokenMissingError, request_json

logger = logging.getLogger(__name__)

GRAPH_BASE_URL = 'https://graph.instagram.com'
GRAPH_VERSION = 'v21.0'
MEDIA_FIELDS = 'id,caption,media_type,media_url,thumbnail_url,permalink,timestamp'
REFRESH_URL = f'{GRAPH_BASE_URL}/refresh_access_token'

_MEDIA_TYPE_MAP = {
    'IMAGE': MediaType.IMAGE,
    'VIDEO': MediaType.VIDEO,
    'CAROUSEL_ALBUM': MediaType.CAROUSEL,
    'REELS': MediaType.REEL,
    'REEL': MediaType.REEL,
}


def _media_endpoint(user_id):
    return f'{GRAPH_BASE_URL}/{GRAPH_VERSION}/{user_id}/media'


def fetch_instagram_media(account, limit=6):
    """Busca as últimas mídias da conta no Instagram Graph API.

    Devolve a lista de dicts crus do campo `data`. Levanta `TokenMissingError`
    quando faltam credenciais e `SocialSyncError` para falhas de rede/HTTP/parse.
    """
    token = (account.access_token or '').strip()
    user_id = (account.external_user_id or '').strip()
    if not token or not user_id:
        raise TokenMissingError(
            'Instagram sem credenciais: configure o ID da conta e o token de acesso no admin.'
        )

    payload = request_json(
        'GET', _media_endpoint(user_id),
        params={'fields': MEDIA_FIELDS, 'access_token': token, 'limit': limit},
    )
    data = payload.get('data')
    if not isinstance(data, list):
        raise SocialSyncError('Resposta do Instagram sem a lista de mídias esperada.')
    return data


def refresh_instagram_token(account):
    """Renova o token de longa duração do Instagram e salva na conta.

    O Instagram renova o token apenas com o próprio token (sem segredo de app), e
    só funciona com tokens com mais de 24h e ainda não expirados. Levanta
    `TokenMissingError` sem token e `SocialSyncError` em falha de rede/HTTP/payload.
    Devolve o novo token.
    """
    token = (account.access_token or '').strip()
    if not token:
        raise TokenMissingError('Instagram sem token de acesso para renovar.')

    payload = request_json(
        'GET', REFRESH_URL,
        params={'grant_type': 'ig_refresh_token', 'access_token': token},
    )
    new_token = payload.get('access_token')
    if not new_token:
        raise SocialSyncError('Instagram não retornou um novo token na renovação.')

    account.access_token = new_token
    expires_in = payload.get('expires_in')
    if expires_in:
        account.token_expires_at = timezone.now() + timedelta(seconds=int(expires_in))
    account.save(update_fields=['access_token', 'token_expires_at', 'updated_at'])
    return new_token


def _map_media_type(raw_type):
    return _MEDIA_TYPE_MAP.get((raw_type or '').upper(), MediaType.UNKNOWN)


def _parse_timestamp(value):
    """Aceita ISO 8601 com fuso (`...+0000` ou `...+00:00`); devolve None se falhar."""
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is not None:
        return parsed
    for fmt in ('%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return None


def normalize_instagram_post(raw_post, account):
    """Converte um item cru do Instagram no dict canônico do SocialPost.

    Função pura e testável: tolera campos ausentes (default unknown / ''). Para
    imagens, a `thumbnail_url` cai na `media_url` (o Graph só envia thumbnail em vídeos).
    """
    external_id = str(raw_post.get('id') or '').strip()
    return {
        'platform': Platform.INSTAGRAM,
        'external_id': external_id,
        'permalink': raw_post.get('permalink') or '',
        'caption': raw_post.get('caption') or '',
        'media_type': _map_media_type(raw_post.get('media_type')),
        'thumbnail_url': raw_post.get('thumbnail_url') or raw_post.get('media_url') or '',
        'media_url': raw_post.get('media_url') or '',
        'published_at': _parse_timestamp(raw_post.get('timestamp')),
        'sync_payload': {
            'id': external_id,
            'media_type': raw_post.get('media_type'),
            'timestamp': raw_post.get('timestamp'),
            'permalink': raw_post.get('permalink'),
        },
    }
