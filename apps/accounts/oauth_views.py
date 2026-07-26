"""Entrada e volta do login com Google.

A REGRA que rege este arquivo inteiro: o Google AUTENTICA, o banco AUTORIZA.
Nenhuma linha aqui atribui cargo, grupo, is_staff ou is_superuser, e
`sync_user_role_group` não é chamada em lugar nenhum — é exatamente a
automação que a docstring da migration 0007 aponta como vetor de escalada de
privilégio. Conseguir provar posse de um e-mail no Google não é, e não pode
virar, uma credencial administrativa.

Depois de identificar a pessoa, o destino sai de `panels.post_login_target` —
a MESMA função do login por senha. Um repórter cai na publicação de matérias,
um leitor no portal, e quem alcança as duas áreas escolhe na tela: não há aqui
uma segunda regra de roteamento que pudesse divergir da original.
"""

import logging
import secrets

from axes.handlers.proxy import AxesProxyHandler
from django.contrib import messages
from django.contrib.auth import login
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from . import oauth_google, panels
from .models import CustomUser, GoogleIdentity

security_log = logging.getLogger('apps.security')

SESSION_KEY = 'google_oauth'
# Prazo do "ida e volta" ao Google. Curto porque não há razão legítima para
# demorar mais: é o tempo de escolher a conta e autorizar.
FLOW_TTL = 600  # 10 minutos


def _require_enabled():
    """Sem credencial configurada, a rota não existe.

    404 e não 500: uma instalação sem Google (CI, teste, um fork) não deve
    expor um endpoint quebrado, e o botão também não aparece na tela.
    """
    if not oauth_google.is_enabled():
        raise Http404('Login com Google não está configurado.')


def _fail(request, mensagem):
    """Devolve a pessoa ao login com uma mensagem em português claro.

    Sempre a tela do leitor: quem falhou não foi identificado, então não há
    como saber se pertence à equipe — e mandar um leitor para a porta dos
    painéis seria mais confuso do que o contrário.
    """
    messages.error(request, mensagem)
    return redirect('accounts:login')


def _unique_username(email):
    """Deriva um username livre a partir do e-mail.

    USERNAME_FIELD do projeto é `username` (não o e-mail), então uma conta
    nascida no Google ainda precisa de um. A parte local do endereço é o
    palpite mais reconhecível para a própria pessoa; o sufixo numérico só
    entra quando já existe alguém com aquele nome — e a busca é
    case-insensitive porque `username` do Django também colide assim.
    """
    base = ''.join(char for char in email.split('@')[0] if char.isalnum() or char in '._-')[:140]
    base = base or 'usuario'
    if not CustomUser.objects.filter(username__iexact=base).exists():
        return base
    for sufixo in range(2, 1000):
        candidato = f'{base}{sufixo}'
        if not CustomUser.objects.filter(username__iexact=candidato).exists():
            return candidato
    # Fim de campo improvável; um sufixo aleatório é melhor do que estourar na
    # cara de quem só queria entrar.
    return f'{base[:100]}_{secrets.token_hex(4)}'


def resolve_google_user(claims):
    """Encontra (ou cria) a conta local desta identidade Google.

    Devolve (user, criado). A ordem das três tentativas é o coração da
    segurança deste fluxo:

    1. Pelo `sub` — o identificador imutável do Google. Se já existe vínculo,
       acabou: nada mais é consultado, e trocar o e-mail no Google não muda a
       conta que a pessoa alcança.
    2. Pelo e-mail, e SOMENTE porque oauth_google.verify_id_token já exigiu
       `email_verified`. É o caminho de quem já tinha conta com senha e
       resolveu entrar pelo Google: a conta é RECONHECIDA, com cargo, grupos
       e is_staff exatamente como estavam. Nada é escrito além do vínculo.
    3. Conta nova, sempre no piso: role=READER (que não tem grupo nenhum em
       ROLE_TO_GROUP), is_staff=False, is_superuser=False e senha inutilizável.
       Quem precisar de acesso administrativo continua recebendo isso de um
       administrador, no admin, como sempre foi.

    A busca do passo 2 é `__iexact` porque o e-mail vem do Google normalizado
    em minúsculas, e contas antigas podem ter sido gravadas com maiúsculas
    (ver migration 0009).
    """
    identity = GoogleIdentity.objects.filter(google_sub=claims['sub']).select_related('user').first()
    if identity is not None:
        return identity.user, False

    user = CustomUser.objects.filter(email__iexact=claims['email']).first()
    if user is not None:
        # Vínculo criado, permissões INTOCADAS — nem role, nem groups, nem
        # is_staff aparecem nesta escrita.
        GoogleIdentity.objects.create(user=user, google_sub=claims['sub'], email=claims['email'])
        return user, False

    user = CustomUser.objects.create(
        username=_unique_username(claims['email']),
        email=claims['email'],
        first_name=claims['given_name'][:150],
        last_name=claims['family_name'][:150],
        role=CustomUser.Role.READER,
        is_staff=False,
        is_superuser=False,
        # O Google já confirmou este endereço (verify_id_token exigiu isso),
        # então pedir de novo um código por e-mail seria atrito sem ganho.
        email_verified=True,
        email_verified_at=timezone.now(),
    )
    # Senha inutilizável, não uma senha aleatória: assim `check_password`
    # recusa qualquer entrada e a pessoa é levada ao fluxo de "esqueci minha
    # senha" se quiser criar uma senha local depois.
    user.set_unusable_password()
    user.save(update_fields=['password'])

    GoogleIdentity.objects.create(user=user, google_sub=claims['sub'], email=claims['email'])
    return user, True


@require_http_methods(['GET'])
def google_start(request):
    """Guarda os segredos do fluxo na sessão e manda a pessoa ao Google."""
    _require_enabled()

    url, state, nonce, code_verifier = oauth_google.build_authorization_request()

    next_url = request.GET.get('next', '')
    if not (next_url and panels.is_safe_next(next_url, request)):
        # Descarta destino externo (open redirect) em silêncio: quem forjou o
        # link não precisa de aviso, e quem clicou num link legítimo interno
        # não perde nada.
        next_url = ''

    # Sessão do lado do servidor (SESSION_ENGINE default = backend db), nunca
    # cookie legível: state, nonce e code_verifier são justamente o que não
    # pode chegar ao navegador.
    request.session[SESSION_KEY] = {
        'state': state,
        'nonce': nonce,
        'code_verifier': code_verifier,
        'next': next_url,
        'started': timezone.now().timestamp(),
    }
    return redirect(str(url))


@require_http_methods(['GET'])
def google_callback(request):
    """Valida a volta do Google e entra na conta correspondente."""
    _require_enabled()

    flow = request.session.pop(SESSION_KEY, None)
    # pop() e não get(): o fluxo é de uso único. Sem isto, um `state` válido
    # continuaria aceitável e daria para repetir a volta.
    request.session.modified = True

    if not flow:
        # Chegar aqui sem fluxo na sessão é a assinatura clássica de
        # login-CSRF: alguém entregou a URL de retorno DELE para a vítima.
        security_log.warning('AUTH_OAUTH_NO_FLOW')
        return _fail(request, 'Sua sessão expirou. Tente entrar novamente.')

    if timezone.now().timestamp() - flow.get('started', 0) > FLOW_TTL:
        return _fail(request, 'Sua sessão expirou. Tente entrar novamente.')

    if request.GET.get('error'):
        # Usuário clicou em "cancelar" na tela do Google — não é erro nosso.
        return _fail(request, 'Entrada com Google cancelada.')

    recebido = request.GET.get('state', '')
    if not secrets.compare_digest(recebido, flow.get('state', '')):
        security_log.warning('AUTH_OAUTH_STATE_MISMATCH')
        return _fail(request, 'Não foi possível concluir a entrada com o Google. Tente novamente.')

    code = request.GET.get('code', '')
    if not code:
        return _fail(request, 'Não foi possível concluir a entrada com o Google. Tente novamente.')

    try:
        raw_id_token = oauth_google.exchange_code(code, flow['code_verifier'])
        claims = oauth_google.verify_id_token(raw_id_token, flow['nonce'])
    except oauth_google.GoogleOAuthError as exc:
        return _fail(request, exc.mensagem)

    user, criado = resolve_google_user(claims)

    # is_active=False é "conta desativada pelo administrador" — recusar ANTES
    # do login(), nunca depois. Entrar e só então descobrir a recusa deixaria
    # uma sessão autenticada de alguém que não devia ter nenhuma.
    if not user.is_active:
        security_log.warning('AUTH_OAUTH_INACTIVE user_id=%s', user.pk)
        return render(request, 'accounts/oauth_disabled.html', status=403)

    # O axes protege o login por SENHA, e o Google não usa senha — mas uma
    # conta em cooloff por tentativas repetidas não pode ter no Google uma
    # porta lateral para ignorar o bloqueio que acabou de ser aplicado.
    if AxesProxyHandler.is_locked(request, credentials={'username': user.get_username()}):
        security_log.warning('AUTH_OAUTH_LOCKED user_id=%s', user.pk)
        return _fail(request, 'Muitas tentativas de acesso. Aguarde alguns minutos e tente de novo.')

    GoogleIdentity.objects.filter(user=user).update(last_login_at=timezone.now())

    # backend explícito: com múltiplos AUTHENTICATION_BACKENDS (axes +
    # ModelBackend) e um usuário que não veio de authenticate(), login() não
    # tem como inferir o backend e levanta ValueError (mesmo motivo comentado
    # em views.register_view). login() também roda cycle_key(), que é o que
    # fecha session fixation.
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    security_log.info(
        'AUTH_OAUTH_LOGIN_OK user_id=%s created=%s staff=%s', user.pk, criado, user.is_staff,
    )

    # Mesma função do login por senha: aqui não existe uma segunda regra de
    # roteamento, e o Google não influencia em nada qual área a pessoa alcança.
    return redirect(panels.post_login_target(user, request, next_url=flow.get('next', '')))
