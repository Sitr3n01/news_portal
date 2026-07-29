"""Views do fluxo de confirmação de e-mail por código (bloqueio suave, Fase 3).

FBVs por regra do projeto (docs/ai/development_rules.md §2): views novas são
Function-Based View — a exceção fica só para o que herda de
django.contrib.auth.views (CustomLoginView, CustomPasswordResetView em
views.py), que não é o caso aqui.
"""

from axes.helpers import get_client_ip_address
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from . import panels
from .emails import send_password_reset_code_email, send_verification_code_email
from .forms import PasswordResetRequestForm, VerificationCodeForm
from .mailer import mask_email
from .models import CustomUser, VerificationCode
from .verification import CodeCheckStatus, check_code, invalidate_all, issue_code, throttle

PURPOSE = VerificationCode.Purpose.EMAIL_VERIFICATION
RESET_PURPOSE = VerificationCode.Purpose.PASSWORD_RESET

# Dicionário, não uma cadeia de if: cada status de CodeCheckStatus vira UMA
# mensagem em PT-BR sem detalhe interno. Reusado tal e qual na Fase 4, quando
# a recuperação de senha por código passar a validar pelo mesmo check_code()
# e precisar do mesmo mapeamento status -> mensagem amigável.
CODE_CHECK_MESSAGES = {
    CodeCheckStatus.INVALID: 'Código inválido. Verifique o código enviado para seu e-mail.',
    CodeCheckStatus.EXPIRED: 'O código expirou. Solicite um novo código.',
    CodeCheckStatus.TOO_MANY_ATTEMPTS: 'Muitas tentativas. Solicite um novo código.',
    CodeCheckStatus.NOT_FOUND: 'Nenhum código pendente. Solicite um novo código.',
    CodeCheckStatus.THROTTLED: 'Muitas tentativas em pouco tempo. Aguarde alguns minutos e tente novamente.',
}


@login_required
@require_http_methods(['GET', 'POST'])
def verify_email(request):
    """Tela de confirmação de e-mail: exibe o form de código e processa o envio.

    Sem @email_verified_required aqui — de propósito: esta view É a via de
    escape do bloqueio suave, então ela não pode ficar atrás de si mesma.
    """
    user = request.user
    if user.email_verified:
        # Não deixa a tela virar beco sem saída para quem já confirmou (ex.:
        # voltou pelo histórico do navegador, ou reabriu o e-mail antigo).
        messages.info(request, 'Seu e-mail já está confirmado.')
        return redirect('news:list')

    if request.method == 'POST':
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            result = check_code(user, PURPOSE, form.cleaned_data['code'], request=request)
            if result.ok:
                user.email_verified = True
                user.email_verified_at = timezone.now()
                user.save(update_fields=['email_verified', 'email_verified_at'])
                messages.success(request, 'E-mail confirmado! Sua conta está liberada.')
                return redirect('news:list')

            # Mensagem genérica por status, sem detalhe interno (nunca dizer
            # quantas tentativas restam nem o motivo técnico) — ver
            # CODE_CHECK_MESSAGES acima.
            messages.error(request, CODE_CHECK_MESSAGES[result.status])
    else:
        form = VerificationCodeForm()

    return render(request, 'accounts/verify_email.html', {
        'form': form,
        # Mascarado (apps.accounts.mailer.mask_email): a pessoa precisa
        # conferir para qual caixa foi, mas a tela pode estar aberta num
        # computador compartilhado.
        'masked_email': mask_email(user.email),
    })


@login_required
@require_POST
def resend_verification_code(request):
    """Reenvia o código de confirmação.

    Só POST (CSRF obrigatório): GET nunca muda estado nem dispara e-mail — um
    link de pré-carregamento, crawler ou favorito antigo não pode reenviar
    código sozinho.
    """
    user = request.user
    if user.email_verified:
        messages.info(request, 'Seu e-mail já está confirmado.')
        return redirect('news:list')

    code = issue_code(user, PURPOSE, request=request)
    if code is None:
        # Rate limit: nunca revelar o teto exato nem quanto falta — isso daria
        # a quem está tentando abusar o número exato de tentativas restantes.
        messages.error(request, 'Você pediu códigos demais. Aguarde alguns minutos antes de tentar de novo.')
        return redirect('accounts:verify_email')

    sent = send_verification_code_email(user, code, request=request)
    if not sent:
        # Falha de SMTP nunca chega ao usuário como exceção/detalhe técnico —
        # apps.accounts.mailer já logou a causa real (EMAIL_SEND_FAILED com o
        # motivo classificado).
        messages.error(request, 'Não conseguimos enviar o e-mail agora. Tente novamente em alguns minutos.')
        return redirect('accounts:verify_email')

    messages.success(request, 'Enviamos um novo código para seu e-mail.')
    return redirect('accounts:verify_email')


# ── Recuperação de senha por código ─────────────────────────────────────────
#
# Substitui o fluxo por link (CustomPasswordResetView, removida): o usuário
# informa o e-mail, recebe um código, digita o código e define a senha nova.
# As rotas `password_reset_confirm`/`password_reset_complete` continuam
# roteadas em urls.py para que links já enviados não caiam em 404.

RESET_SESSION_KEY = 'pwd_reset'
# Prazo próprio do fluxo, independente do prazo da sessão do Django: uma
# sessão longa não pode deixar uma troca de senha pela metade aberta por horas
# num computador compartilhado.
RESET_SESSION_TTL = 900  # 15 minutos
RESET_REQUEST_IP_LIMIT = 10
RESET_CODE_IP_LIMIT = 20

# Uma mensagem só para "existe" e "não existe" — é o que impede o formulário
# de virar oráculo de quem tem conta no site.
RESET_SENT_MESSAGE = 'Se existir uma conta com esse e-mail, enviamos um código.'
RESET_EXPIRED_MESSAGE = 'Sua solicitação expirou. Comece de novo.'


def _reset_state(request, expected_stage):
    """Estado do fluxo na sessão, só se estiver no estágio esperado e no prazo.

    A checagem de estágio é o que impede pular direto para a tela de senha
    nova: sem ela, bastaria conhecer a URL para trocar a senha de uma conta
    sem nunca ter provado posse da caixa de entrada.

    Guardar `user_pk` na sessão é seguro aqui: o projeto não define
    SESSION_ENGINE (config/settings/base.py), então vale o default do Django,
    `django.contrib.sessions.backends.db` — o conteúdo fica no servidor e o
    cookie carrega apenas a chave da sessão.
    """
    state = request.session.get(RESET_SESSION_KEY)
    if not state or state.get('stage') != expected_stage:
        return None
    if timezone.now().timestamp() - state.get('started', 0) > RESET_SESSION_TTL:
        request.session.pop(RESET_SESSION_KEY, None)
        return None
    return state


@require_http_methods(['GET', 'POST'])
def password_reset_request(request):
    """Passo 1: recebe o e-mail e (se houver conta) dispara o código.

    Responde EXATAMENTE igual exista ou não a conta: mesma mensagem, mesmo
    redirecionamento, mesmo estado gravado na sessão. A diferença de tempo
    entre os dois caminhos (um envia e-mail, o outro não) é um oráculo
    residual conhecido e aceito — fechá-lo exigiria trabalho artificial de
    duração constante, complexidade que não se paga contra a alternativa de
    simplesmente não ter o fluxo.
    """
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST, request=request)
        if form.is_valid():
            email = form.cleaned_data['email']
            ip = get_client_ip_address(request) or 'unknown_ip'

            # Balde no nível da view, além do que issue_code já faz: issue_code
            # só roda quando a conta existe, então sem isto um atacante
            # martelaria o endpoint com endereços inexistentes sem nunca tocar
            # num limite.
            barrado = throttle((ip,), RESET_REQUEST_IP_LIMIT, 'pwd_reset:request:ip')

            # is_active=False (conta desativada pelo administrador) não recebe
            # código — mas a resposta ao visitante é a mesma, senão o
            # formulário revelaria quem foi banido.
            user = CustomUser.objects.filter(email__iexact=email, is_active=True).first()
            if user is not None and not barrado:
                code = issue_code(user, RESET_PURPOSE, request=request)
                if code is not None:
                    send_password_reset_code_email(user, code, request=request)

            request.session[RESET_SESSION_KEY] = {
                'email': email,
                'user_pk': user.pk if user is not None else None,
                'stage': 'code',
                'started': timezone.now().timestamp(),
            }
            messages.info(request, RESET_SENT_MESSAGE)
            return redirect('accounts:password_reset_code')
    else:
        form = PasswordResetRequestForm(request=request)

    return render(request, 'accounts/password_reset/request.html', {'form': form})


def _wrong_stage_redirect(request, expected_stage):
    """Para onde mandar quem chegou num passo que ainda não é o dele.

    Manda para o passo CORRETO quando o fluxo está apenas noutro estágio, em
    vez de descartar o progresso e obrigar a pedir código de novo. Só quando
    não há fluxo nenhum (ou ele venceu) é que a sessão é limpa e a pessoa
    recomeça — digitar a URL errada, ou voltar pelo histórico do navegador,
    não pode custar o código que acabou de chegar por e-mail.
    """
    for stage, destino in (('code', 'accounts:password_reset_code'), ('password', 'accounts:password_reset_new')):
        if stage != expected_stage and _reset_state(request, stage) is not None:
            return redirect(destino)

    request.session.pop(RESET_SESSION_KEY, None)
    messages.info(request, RESET_EXPIRED_MESSAGE)
    return redirect('accounts:password_reset')


@require_http_methods(['GET', 'POST'])
def password_reset_code(request):
    """Passo 2: valida o código e libera a tela de senha nova."""
    state = _reset_state(request, 'code')
    if state is None:
        return _wrong_stage_redirect(request, 'code')

    if request.method == 'POST':
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            user = None
            if state.get('user_pk') is not None:
                user = CustomUser.objects.filter(pk=state['user_pk'], is_active=True).first()

            if user is None:
                # E-mail sem conta (ou conta desativada/apagada no meio do
                # fluxo): nunca aceita, e responde com a MESMA mensagem de
                # código errado. O balde por IP só entra neste ramo porque no
                # outro quem já conta a tentativa é o check_code — contar nos
                # dois lugares reduziria pela metade o limite real de quem tem
                # conta de verdade.
                if throttle((get_client_ip_address(request) or 'unknown_ip',), RESET_CODE_IP_LIMIT, 'pwd_reset:code:ip'):
                    messages.error(request, CODE_CHECK_MESSAGES[CodeCheckStatus.THROTTLED])
                else:
                    messages.error(request, CODE_CHECK_MESSAGES[CodeCheckStatus.INVALID])
            else:
                result = check_code(user, RESET_PURPOSE, form.cleaned_data['code'], request=request)
                if result.ok:
                    state['stage'] = 'password'
                    request.session[RESET_SESSION_KEY] = state
                    request.session.modified = True
                    return redirect('accounts:password_reset_new')
                messages.error(request, CODE_CHECK_MESSAGES[result.status])
    else:
        form = VerificationCodeForm()

    return render(request, 'accounts/password_reset/code.html', {
        'form': form,
        'masked_email': mask_email(state.get('email', '')),
    })


@require_POST
def password_reset_resend(request):
    """Reenvia o código do passo 2.

    O endereço vem da SESSÃO, nunca de campo do formulário: aceitar um e-mail
    do corpo do POST transformaria isto num endpoint de envio de e-mail para
    qualquer endereço, autenticado por nada.
    """
    state = _reset_state(request, 'code')
    if state is None:
        return _wrong_stage_redirect(request, 'code')

    if state.get('user_pk') is not None:
        user = CustomUser.objects.filter(pk=state['user_pk'], is_active=True).first()
        if user is not None:
            code = issue_code(user, RESET_PURPOSE, request=request)
            if code is not None:
                send_password_reset_code_email(user, code, request=request)

    # Mesma mensagem com ou sem conta, e sem revelar o rate limit: reenvio não
    # pode ser um caminho lateral para descobrir o que o passo 1 esconde.
    messages.info(request, 'Se existir uma conta com esse e-mail, enviamos um novo código.')
    return redirect('accounts:password_reset_code')


@require_http_methods(['GET', 'POST'])
def password_reset_new(request):
    """Passo 3: define a senha nova e entra com ela."""
    state = _reset_state(request, 'password')
    if state is None:
        return _wrong_stage_redirect(request, 'password')

    user = None
    if state.get('user_pk') is not None:
        user = CustomUser.objects.filter(pk=state['user_pk'], is_active=True).first()
    if user is None:
        # Chegou ao estágio de senha sem conta válida por trás (apagada ou
        # desativada no meio do fluxo): aí sim zera, não há o que continuar.
        request.session.pop(RESET_SESSION_KEY, None)
        messages.info(request, RESET_EXPIRED_MESSAGE)
        return redirect('accounts:password_reset')

    if request.method == 'POST':
        # SetPasswordForm do Django, e não validação à mão: ele já aplica os
        # AUTH_PASSWORD_VALIDATORS configurados em base.py (tamanho mínimo,
        # senha comum, só dígitos, semelhança com dados do usuário).
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()

            # Qualquer código ainda pendente morre aqui — dos DOIS propósitos.
            # Se um código de recuperação chegou a vazar (caixa comprometida,
            # e-mail reencaminhado por engano), trocar a senha tem de fechar
            # essa porta, não deixá-la aberta até expirar sozinha.
            invalidate_all(user)

            if not user.email_verified:
                # Acabou de provar posse da caixa de entrada digitando um
                # código que só chegou lá — não faz sentido continuar pedindo
                # confirmação de e-mail depois disso.
                user.email_verified = True
                user.email_verified_at = timezone.now()
                user.save(update_fields=['email_verified', 'email_verified_at'])

            request.session.pop(RESET_SESSION_KEY, None)

            # backend explícito: o projeto tem múltiplos AUTHENTICATION_BACKENDS
            # (axes + ModelBackend), e o usuário aqui não veio de authenticate() —
            # sem o backend, login() levanta ValueError (mesmo motivo comentado
            # em views.register_view).
            #
            # As OUTRAS sessões deste usuário caem sozinhas: trocar a senha muda
            # AbstractBaseUser.get_session_auth_hash(), e o AuthenticationMiddleware
            # descarta qualquer sessão que carregue o hash antigo. A sessão atual
            # sobrevive porque este login() grava o hash novo.
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            messages.success(request, 'Senha alterada com sucesso!')
            # Mesma regra de destino do login normal (panels.post_login_target):
            # um repórter cai na publicação de matérias, um leitor no portal.
            # Reimplementar esse roteamento aqui seria uma segunda fonte de
            # verdade sobre quem alcança qual área.
            return redirect(panels.post_login_target(user, request))
    else:
        form = SetPasswordForm(user)

    return render(request, 'accounts/password_reset/new_password.html', {'form': form})
