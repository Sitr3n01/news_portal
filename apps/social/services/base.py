"""Camada HTTP compartilhada dos serviços de redes sociais.

Centraliza o cliente HTTP (com timeout obrigatório) e converte qualquer falha de
rede/HTTP/parse numa `SocialSyncError` com mensagem amigável em PT-BR — os serviços
e o comando de sincronização nunca lidam com exceções cruas do httpx.
"""
import logging

import httpx
from django.utils import timezone

logger = logging.getLogger(__name__)

# Toda chamada externa tem teto de tempo — nunca pendura a requisição.
DEFAULT_TIMEOUT = 10.0  # segundos


class SocialSyncError(Exception):
    """Falha tratável de sincronização (mensagem amigável já em PT-BR)."""


class TokenMissingError(SocialSyncError):
    """Conta sem credencial configurada para a API oficial."""


class RateLimitError(SocialSyncError):
    """A API sinalizou limite de requisições (HTTP 429)."""


def request_json(method, url, *, params=None, headers=None, json=None, data=None, timeout=DEFAULT_TIMEOUT):
    """Faz uma requisição com timeout e devolve o JSON, ou levanta SocialSyncError.

    `json` envia corpo JSON; `data` envia corpo form-urlencoded (ex.: endpoint de
    token do TikTok). Trata timeout, erro de conexão, status HTTP de erro
    (429 → RateLimitError) e corpo não-JSON — sempre como SocialSyncError, nunca
    propaga exceção do httpx.
    """
    try:
        response = httpx.request(
            method, url, params=params, headers=headers, json=json, data=data, timeout=timeout,
        )
    except httpx.TimeoutException as exc:
        raise SocialSyncError('Tempo de resposta esgotado ao contatar a API.') from exc
    except httpx.HTTPError as exc:
        raise SocialSyncError('Falha de conexão com a API.') from exc

    if response.status_code == 429:
        raise RateLimitError('Limite de requisições atingido (HTTP 429). Tente novamente mais tarde.')
    if response.status_code >= 400:
        raise SocialSyncError(f'A API respondeu com erro HTTP {response.status_code}.')

    try:
        return response.json()
    except ValueError as exc:
        raise SocialSyncError('Resposta da API em formato inesperado (JSON inválido).') from exc


def token_expiring_soon(account, within):
    """True se o token de acesso expira dentro de `within` (timedelta) ou já expirou.

    Sem data de expiração conhecida, retorna False — não força refresh à toa; o
    fetch tenta com o token atual e, se a API recusar, o erro é registrado.
    """
    if not account.token_expires_at:
        return False
    return account.token_expires_at - timezone.now() <= within
