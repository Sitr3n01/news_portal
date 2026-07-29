"""Cliente OpenID Connect do Google — só a parte de AUTENTICAÇÃO.

Este módulo responde a uma pergunta e só uma: "qual identidade Google está do
outro lado?". Ele não decide o que essa pessoa pode fazer, não mexe em cargo,
grupo ou is_staff, e não sabe o que é um painel. Quem resolve a conta local é
apps.accounts.oauth_views.resolve_google_user; quem decide o destino continua
sendo apps.accounts.panels — o mesmo que o login por senha usa.

Implementação própria, e não uma biblioteca de social login: allauth e
social-auth trazem models, views, URLs e templates próprios de login/cadastro
/recuperação de senha que colidiriam de frente com o login unificado deste
projeto (PanelLoginView, as rotas-sombra de config/urls.py e o fluxo de código
por e-mail). O fluxo abaixo é Authorization Code + PKCE, que cabe em um
arquivo auditável.

Segurança embutida no fluxo:
  * `state`  — guardado na sessão do servidor e conferido na volta. É o que
               impede login-CSRF (alguém fazer você entrar na conta DELE).
  * `nonce`  — vai no pedido e volta dentro do ID token; conferido à mão,
               porque a biblioteca do Google não confere.
  * PKCE     — o code_verifier nunca trafega pelo navegador, só o desafio
               derivado; um código de autorização interceptado não vale nada
               sem ele.
  * ID token — assinatura conferida contra o JWKS do Google (google-auth), com
               emissor, público-alvo e validade.
"""

import base64
import hashlib
import logging
import secrets

import httpx
from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

logger = logging.getLogger('apps.security')

AUTHORIZATION_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_ENDPOINT = 'https://oauth2.googleapis.com/token'
SCOPES = 'openid email profile'
# Emissores aceitos: o Google assina ora com um, ora com o outro, e os dois são
# legítimos. google-auth já verifica isso, mas a lista fica explícita aqui para
# a conferência não depender do default de uma dependência externa.
VALID_ISSUERS = ('https://accounts.google.com', 'accounts.google.com')
HTTP_TIMEOUT = 10  # segundos; sem isto um endpoint travado pendura o worker


class GoogleOAuthError(Exception):
    """Falha esperada do fluxo — vira mensagem amigável, nunca 500.

    Carrega um `motivo` curto e estável para o log (nunca exibido ao usuário)
    separado da mensagem em PT-BR que a view mostra.
    """

    def __init__(self, motivo, mensagem):
        super().__init__(motivo)
        self.motivo = motivo
        self.mensagem = mensagem


def is_enabled():
    return bool(settings.GOOGLE_OAUTH_ENABLED and settings.GOOGLE_OAUTH_REDIRECT_URI)


def _redirect_uri():
    """O redirect_uri registrado no console do Google.

    Vem de variável de ambiente e nunca de request.build_absolute_uri():
    atrás do nginx o cabeçalho Host é influenciável, e derivar o destino dele
    permitiria empurrar o retorno do Google para outro domínio.
    """
    return settings.GOOGLE_OAUTH_REDIRECT_URI


def build_authorization_request():
    """Monta a URL de ida e os segredos que ficam guardados na sessão.

    Devolve (url, state, nonce, code_verifier). Os três últimos NÃO podem ir
    para o navegador em cookie legível nem para a URL — só para a sessão do
    lado do servidor.
    """
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    # 43-128 caracteres, conforme a RFC 7636. token_urlsafe(64) dá ~86.
    code_verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('ascii')).digest()
    ).decode('ascii').rstrip('=')

    params = {
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'redirect_uri': _redirect_uri(),
        'response_type': 'code',
        'scope': SCOPES,
        'state': state,
        'nonce': nonce,
        'code_challenge': challenge,
        'code_challenge_method': 'S256',
        # Sempre perguntar de qual conta se trata: sem isto, quem tem várias
        # contas Google no navegador entra silenciosamente com a errada e não
        # entende por que não acha os próprios comentários.
        'prompt': 'select_account',
    }
    return httpx.URL(AUTHORIZATION_ENDPOINT, params=params), state, nonce, code_verifier


def exchange_code(code, code_verifier):
    """Troca o código de autorização por tokens, servidor a servidor.

    Esta requisição sai daqui direto para o Google sobre TLS — o navegador não
    participa —, e é por isso que o client_secret pode entrar nela.
    """
    payload = {
        'code': code,
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
        'redirect_uri': _redirect_uri(),
        'grant_type': 'authorization_code',
        'code_verifier': code_verifier,
    }
    try:
        response = httpx.post(TOKEN_ENDPOINT, data=payload, timeout=HTTP_TIMEOUT)
    except httpx.HTTPError as exc:
        # Só o tipo da exceção no log: o payload acima carrega o client_secret
        # e o código de autorização, e nenhum dos dois pode vazar para o log.
        logger.error('AUTH_OAUTH_TOKEN_ERROR reason=network detail=%s', type(exc).__name__)
        raise GoogleOAuthError('network', 'Não foi possível falar com o Google agora. Tente de novo.') from exc

    if response.status_code != 200:
        logger.error('AUTH_OAUTH_TOKEN_ERROR reason=http_%s', response.status_code)
        raise GoogleOAuthError('token_http', 'Não foi possível concluir a entrada com o Google.')

    data = response.json()
    if not data.get('id_token'):
        logger.error('AUTH_OAUTH_TOKEN_ERROR reason=missing_id_token')
        raise GoogleOAuthError('missing_id_token', 'Não foi possível concluir a entrada com o Google.')
    return data['id_token']


def verify_id_token(raw_id_token, expected_nonce):
    """Confere assinatura, emissor, público-alvo, validade e nonce.

    google-auth busca (e mantém em cache) as chaves públicas do Google e checa
    assinatura, `iss`, `aud` e `exp`. O que ele NÃO checa é o `nonce` — por
    isso a conferência explícita abaixo, sem a qual um ID token legítimo
    capturado de outro fluxo poderia ser reapresentado aqui.
    """
    try:
        claims = google_id_token.verify_oauth2_token(
            raw_id_token,
            google_requests.Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID,
        )
    except ValueError as exc:
        logger.warning('AUTH_OAUTH_IDTOKEN_INVALID reason=verification_failed')
        raise GoogleOAuthError('idtoken_invalid', 'Não foi possível validar sua conta Google.') from exc

    if claims.get('iss') not in VALID_ISSUERS:
        logger.warning('AUTH_OAUTH_IDTOKEN_INVALID reason=issuer')
        raise GoogleOAuthError('idtoken_issuer', 'Não foi possível validar sua conta Google.')

    # compare_digest, e não ==: comparação de string comum vaza, pelo tempo de
    # resposta, quantos caracteres iniciais bateram.
    recebido = claims.get('nonce') or ''
    if not expected_nonce or not secrets.compare_digest(recebido, expected_nonce):
        logger.warning('AUTH_OAUTH_IDTOKEN_INVALID reason=nonce')
        raise GoogleOAuthError('idtoken_nonce', 'Sua sessão expirou. Tente entrar novamente.')

    if not claims.get('sub'):
        logger.warning('AUTH_OAUTH_IDTOKEN_INVALID reason=missing_sub')
        raise GoogleOAuthError('idtoken_sub', 'Não foi possível validar sua conta Google.')

    email = (claims.get('email') or '').strip().lower()
    if not email:
        raise GoogleOAuthError(
            'missing_email',
            'Sua conta Google não compartilhou um e-mail. Use o login com senha.',
        )

    # email_verified é o pilar do casamento por e-mail: sem esta garantia do
    # próprio Google, qualquer pessoa que criasse uma conta Google declarando
    # o e-mail de outra assumiria a conta local dela. Comparação com True e
    # não truthiness — o Google já mandou a string 'true' em versões antigas,
    # e uma string vazia seria falsa por acidente, não por checagem.
    if claims.get('email_verified') not in (True, 'true'):
        raise GoogleOAuthError(
            'email_unverified',
            'O Google ainda não confirmou esse e-mail. Confirme no Google e tente de novo.',
        )

    return {
        'sub': claims['sub'],
        'email': email,
        'given_name': (claims.get('given_name') or '').strip(),
        'family_name': (claims.get('family_name') or '').strip(),
    }
