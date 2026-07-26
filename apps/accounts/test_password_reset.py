"""Ciclo de vida da recuperação de senha — fluxo por CÓDIGO.

Fluxo único da plataforma: leitores e equipe usam o mesmo caminho, começando
em /accounts/password_reset/. O fluxo por link foi substituído por código de
6 dígitos (apps/accounts/code_views.py); as rotas antigas de confirmação por
uidb64/token continuam roteadas só para não quebrar link já enviado, e há um
teste de regressão aqui garantindo isso.
"""

import re

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.accounts.code_views import RESET_REQUEST_IP_LIMIT
from apps.accounts.models import VerificationCode
from apps.common import turnstile

SENHA_ANTIGA = 'SenhaAntiga#2026'
SENHA_NOVA = 'SenhaNova#2026'
PURPOSE = VerificationCode.Purpose.PASSWORD_RESET


@pytest.fixture
def usuario(db, django_user_model):
    return django_user_model.objects.create_user(
        username='esquecido',
        email='esquecido@example.com',
        password=SENHA_ANTIGA,
    )


def mock_turnstile(monkeypatch, *, valid=True):
    """Mesmo padrão de apps/news/tests.py e test_email_verification.py."""
    monkeypatch.setattr(turnstile, 'verify_turnstile', lambda token, remote_ip='': valid and token == 'valid-token')


def pedir_reset(client, email):
    return client.post(reverse('accounts:password_reset'), {
        'email': email,
        turnstile.TURNSTILE_RESPONSE_FIELD: 'valid-token',
    })


def codigo_do_email():
    """Extrai o código de 6 dígitos do último e-mail — o mesmo caminho do usuário.

    Ler o código do corpo do e-mail, em vez de chamar issue_code no teste,
    exercita a cadeia inteira (view -> verification -> emails -> template) e
    pegaria uma quebra em qualquer elo dela.
    """
    corpo = mail.outbox[-1].body
    achado = re.search(r'\b(\d{6})\b', corpo)
    assert achado, f'código de 6 dígitos não encontrado em:\n{corpo}'
    return achado.group(1)


def informar_codigo(client, codigo):
    return client.post(reverse('accounts:password_reset_code'), {'code': codigo})


def definir_senha(client, senha):
    return client.post(reverse('accounts:password_reset_new'), {
        'new_password1': senha, 'new_password2': senha,
    })


# ── Solicitação ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_valid_request_sends_code_and_advances(client, usuario, current_site, monkeypatch):
    mock_turnstile(monkeypatch)

    response = pedir_reset(client, usuario.email)

    assert response.status_code == 302
    assert response.url == reverse('accounts:password_reset_code')
    assert len(mail.outbox) == 1
    assert usuario.email in mail.outbox[0].to
    # O assunto não pode carregar o código: notificação de tela bloqueada e
    # prévia de caixa de entrada são visíveis para quem estiver por perto.
    assert codigo_do_email() not in mail.outbox[0].subject


@pytest.mark.django_db
def test_unknown_email_is_indistinguishable(client, usuario, current_site, monkeypatch):
    """Anti-enumeração: a resposta não pode denunciar se a conta existe."""
    mock_turnstile(monkeypatch)

    conhecida = pedir_reset(client, usuario.email)
    emails_apos_conhecida = len(mail.outbox)
    conteudo_conhecida = client.get(reverse('accounts:password_reset_code')).content

    desconhecida = pedir_reset(client, 'ninguem@example.com')
    conteudo_desconhecida = client.get(reverse('accounts:password_reset_code')).content

    assert conhecida.status_code == desconhecida.status_code
    assert conhecida.url == desconhecida.url
    # Nenhum e-mail extra para o endereço inexistente...
    assert len(mail.outbox) == emails_apos_conhecida
    # ...e a tela seguinte também não denuncia a diferença. O e-mail exibido é
    # mascarado, então os dois conteúdos diferem só no que a própria pessoa
    # digitou — nunca no que o sistema sabe.
    assert (b'esquecido' in conteudo_conhecida) == (b'esquecido' in conteudo_desconhecida)


@pytest.mark.django_db
def test_request_finds_account_regardless_of_capitalization(client, usuario, current_site, monkeypatch):
    """Trocar a caixa das letras tem de achar a MESMA conta."""
    mock_turnstile(monkeypatch)

    response = pedir_reset(client, usuario.email.upper())

    assert response.url == reverse('accounts:password_reset_code')
    assert len(mail.outbox) == 1
    assert usuario.email in mail.outbox[0].to


@pytest.mark.django_db
def test_inactive_account_gets_no_email_but_same_response(client, django_user_model, current_site, monkeypatch):
    """Conta desativada não recebe código — e a resposta não revela isso."""
    mock_turnstile(monkeypatch)
    django_user_model.objects.create_user(
        username='banido', email='banido@example.com', password=SENHA_ANTIGA, is_active=False,
    )

    response = pedir_reset(client, 'banido@example.com')

    assert response.status_code == 302
    assert response.url == reverse('accounts:password_reset_code')
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_request_without_antibot_is_refused(client, usuario, current_site, monkeypatch):
    mock_turnstile(monkeypatch, valid=False)

    response = client.post(reverse('accounts:password_reset'), {'email': usuario.email})

    assert response.status_code == 200  # volta ao formulário
    assert len(mail.outbox) == 0


# ── Limite de envio ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_single_ip_cannot_mailbomb_many_addresses(client, django_user_model, current_site, monkeypatch):
    """Um IP não pode disparar código para endereços ilimitados.

    O balde do issue_code só conta quando a conta EXISTE; sem o balde no nível
    da view, martelar com endereços inexistentes sairia de graça.
    """
    mock_turnstile(monkeypatch)

    for indice in range(RESET_REQUEST_IP_LIMIT + 3):
        django_user_model.objects.create_user(
            username=f'alvo{indice}', email=f'alvo{indice}@example.com', password=SENHA_ANTIGA,
        )
        response = pedir_reset(client, f'alvo{indice}@example.com')
        # Mesmo bloqueado, a resposta continua idêntica — o limite não vaza.
        assert response.url == reverse('accounts:password_reset_code')

    assert len(mail.outbox) == RESET_REQUEST_IP_LIMIT


# ── Validação do código ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_correct_code_advances_to_new_password(client, usuario, current_site, monkeypatch):
    mock_turnstile(monkeypatch)
    pedir_reset(client, usuario.email)

    response = informar_codigo(client, codigo_do_email())

    assert response.status_code == 302
    assert response.url == reverse('accounts:password_reset_new')
    assert client.get(reverse('accounts:password_reset_new')).status_code == 200


@pytest.mark.django_db
def test_wrong_code_does_not_advance(client, usuario, current_site, monkeypatch):
    mock_turnstile(monkeypatch)
    pedir_reset(client, usuario.email)
    certo = codigo_do_email()
    errado = ''.join('9' if digito != '9' else '8' for digito in certo)

    response = informar_codigo(client, errado)

    assert response.status_code == 200
    assert 'Código inválido' in response.content.decode()
    # E o passo seguinte continua trancado.
    assert client.get(reverse('accounts:password_reset_new')).status_code == 302


@pytest.mark.django_db
def test_expired_code_is_refused(client, usuario, current_site, monkeypatch):
    mock_turnstile(monkeypatch)
    pedir_reset(client, usuario.email)
    codigo = codigo_do_email()
    VerificationCode.objects.filter(user=usuario, purpose=PURPOSE).update(
        expires_at=timezone.now() - timezone.timedelta(seconds=1),
    )

    response = informar_codigo(client, codigo)

    assert 'expirou' in response.content.decode()


@pytest.mark.django_db
def test_code_from_email_of_someone_else_is_refused(client, usuario, django_user_model, current_site, monkeypatch):
    """Código emitido para OUTRA conta não serve nesta sessão de recuperação."""
    mock_turnstile(monkeypatch)
    outro = django_user_model.objects.create_user(
        username='outro', email='outro@example.com', password=SENHA_ANTIGA,
    )
    pedir_reset(client, outro.email)
    codigo_do_outro = codigo_do_email()

    cliente_do_alvo = client.__class__()
    cliente_do_alvo.post(reverse('accounts:password_reset'), {
        'email': usuario.email, turnstile.TURNSTILE_RESPONSE_FIELD: 'valid-token',
    })
    response = informar_codigo(cliente_do_alvo, codigo_do_outro)

    assert response.status_code == 200
    assert 'Código inválido' in response.content.decode()


@pytest.mark.django_db
def test_code_for_nonexistent_email_is_never_accepted(client, current_site, monkeypatch):
    """Sem conta por trás, nenhum código de 6 dígitos pode passar."""
    mock_turnstile(monkeypatch)
    pedir_reset(client, 'ninguem@example.com')

    response = informar_codigo(client, '123456')

    assert response.status_code == 200
    assert 'Código inválido' in response.content.decode()


# ── Pular etapas ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_cannot_jump_straight_to_new_password(client, current_site):
    """Sem passar pelo código, a tela de senha nova não abre."""
    response = client.get(reverse('accounts:password_reset_new'))

    assert response.status_code == 302
    assert response.url == reverse('accounts:password_reset')


@pytest.mark.django_db
def test_cannot_open_code_screen_without_requesting_first(client, current_site):
    response = client.get(reverse('accounts:password_reset_code'))

    assert response.status_code == 302
    assert response.url == reverse('accounts:password_reset')


@pytest.mark.django_db
def test_code_stage_alone_does_not_unlock_password_stage(client, usuario, current_site, monkeypatch):
    """Ter pedido o código não basta: é preciso ter ACERTADO o código.

    E quem cai na URL errada volta para o passo do código — não para o começo:
    zerar o fluxo aqui obrigaria a pedir um código novo por causa de um clique
    no lugar errado, invalidando o que já chegou na caixa de entrada.
    """
    mock_turnstile(monkeypatch)
    pedir_reset(client, usuario.email)
    codigo = codigo_do_email()

    response = client.get(reverse('accounts:password_reset_new'))

    assert response.status_code == 302
    assert response.url == reverse('accounts:password_reset_code')
    # O código que já havia chegado continua valendo.
    assert informar_codigo(client, codigo).url == reverse('accounts:password_reset_new')


@pytest.mark.django_db
def test_going_back_to_code_screen_after_validating_moves_forward(client, usuario, current_site, monkeypatch):
    """Voltar pelo histórico do navegador não desfaz o passo já cumprido."""
    mock_turnstile(monkeypatch)
    pedir_reset(client, usuario.email)
    informar_codigo(client, codigo_do_email())

    response = client.get(reverse('accounts:password_reset_code'))

    assert response.status_code == 302
    assert response.url == reverse('accounts:password_reset_new')


# ── Reenvio ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_resend_uses_session_email_not_posted_one(client, usuario, django_user_model, current_site, monkeypatch):
    """O reenvio ignora qualquer e-mail no corpo do POST.

    Se aceitasse, o endpoint viraria disparador de e-mail para endereço
    arbitrário, autenticado por nada.
    """
    mock_turnstile(monkeypatch)
    vitima = django_user_model.objects.create_user(
        username='vitima', email='vitima@example.com', password=SENHA_ANTIGA,
    )
    pedir_reset(client, usuario.email)
    mail.outbox.clear()

    client.post(reverse('accounts:password_reset_resend'), {'email': vitima.email})

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [usuario.email]


@pytest.mark.django_db
def test_resend_invalidates_previous_code(client, usuario, current_site, monkeypatch):
    mock_turnstile(monkeypatch)
    pedir_reset(client, usuario.email)
    codigo_antigo = codigo_do_email()

    client.post(reverse('accounts:password_reset_resend'))
    codigo_novo = codigo_do_email()

    assert codigo_antigo != codigo_novo
    assert 'Código inválido' in informar_codigo(client, codigo_antigo).content.decode()


@pytest.mark.django_db
def test_resend_requires_post(client, usuario, current_site, monkeypatch):
    mock_turnstile(monkeypatch)
    pedir_reset(client, usuario.email)
    mail.outbox.clear()

    response = client.get(reverse('accounts:password_reset_resend'))

    assert response.status_code == 405
    assert len(mail.outbox) == 0


# ── Troca efetiva da senha ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_password_change_works_and_old_password_stops(client, usuario, current_site, monkeypatch):
    mock_turnstile(monkeypatch)
    pedir_reset(client, usuario.email)
    informar_codigo(client, codigo_do_email())

    response = definir_senha(client, SENHA_NOVA)

    assert response.status_code == 302
    usuario.refresh_from_db()
    assert usuario.check_password(SENHA_NOVA)
    assert not usuario.check_password(SENHA_ANTIGA)

    client.logout()

    # POST na tela de login em vez de client.login(): o AxesStandaloneBackend
    # exige um request de verdade e recusa a chamada direta ao backend.
    def tentar(senha):
        client.post(reverse('accounts:login'),
                    {'username': usuario.get_username(), 'password': senha})
        autenticado = '_auth_user_id' in client.session
        client.logout()
        return autenticado

    assert tentar(SENHA_ANTIGA) is False
    assert tentar(SENHA_NOVA) is True


@pytest.mark.django_db
def test_password_change_logs_the_user_in(client, usuario, current_site, monkeypatch):
    mock_turnstile(monkeypatch)
    pedir_reset(client, usuario.email)
    informar_codigo(client, codigo_do_email())

    definir_senha(client, SENHA_NOVA)

    assert '_auth_user_id' in client.session


@pytest.mark.django_db
def test_password_change_marks_email_as_verified(client, usuario, current_site, monkeypatch):
    """Digitar um código que só chegou na caixa prova posse dela."""
    mock_turnstile(monkeypatch)
    usuario.email_verified = False
    usuario.save(update_fields=['email_verified'])
    pedir_reset(client, usuario.email)
    informar_codigo(client, codigo_do_email())

    definir_senha(client, SENHA_NOVA)

    usuario.refresh_from_db()
    assert usuario.email_verified is True
    assert usuario.email_verified_at is not None


@pytest.mark.django_db
def test_code_cannot_be_reused_after_password_change(client, usuario, current_site, monkeypatch):
    mock_turnstile(monkeypatch)
    pedir_reset(client, usuario.email)
    codigo = codigo_do_email()
    informar_codigo(client, codigo)
    definir_senha(client, SENHA_NOVA)
    client.logout()

    # Recomeça o fluxo e tenta o código já gasto.
    pedir_reset(client, usuario.email)
    response = informar_codigo(client, codigo)

    assert 'Código inválido' in response.content.decode()
    usuario.refresh_from_db()
    assert usuario.check_password(SENHA_NOVA)


@pytest.mark.django_db
def test_password_change_invalidates_pending_codes(client, usuario, current_site, monkeypatch):
    """Trocar a senha fecha a porta de qualquer código ainda pendente."""
    mock_turnstile(monkeypatch)
    from apps.accounts.verification import issue_code
    issue_code(usuario, VerificationCode.Purpose.EMAIL_VERIFICATION)

    pedir_reset(client, usuario.email)
    informar_codigo(client, codigo_do_email())
    definir_senha(client, SENHA_NOVA)

    pendentes = VerificationCode.objects.filter(user=usuario, used_at__isnull=True)
    assert pendentes.count() == 0


@pytest.mark.django_db
def test_weak_password_is_refused(client, usuario, current_site, monkeypatch):
    """A política de senha do Django continua valendo na redefinição."""
    mock_turnstile(monkeypatch)
    pedir_reset(client, usuario.email)
    informar_codigo(client, codigo_do_email())

    response = definir_senha(client, '12345678')

    assert response.status_code == 200
    usuario.refresh_from_db()
    assert usuario.check_password(SENHA_ANTIGA)


@pytest.mark.django_db
def test_session_state_is_cleared_after_change(client, usuario, current_site, monkeypatch):
    """Concluído o fluxo, a tela de senha nova não abre de novo."""
    mock_turnstile(monkeypatch)
    pedir_reset(client, usuario.email)
    informar_codigo(client, codigo_do_email())
    definir_senha(client, SENHA_NOVA)

    response = client.get(reverse('accounts:password_reset_new'))

    assert response.status_code == 302
    assert response.url == reverse('accounts:password_reset')


# ── Regressão: links antigos continuam roteados ────────────────────────────

@pytest.mark.django_db
def test_old_link_route_still_resolves(client, usuario, current_site):
    """Ninguém emite mais estes links, mas os já enviados não podem dar 404.

    O token é montado aqui à mão exatamente porque o fluxo novo não gera mais
    link nenhum — é o que sobrou para exercitar a rota preservada.
    """
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)

    response = client.get(reverse('accounts:password_reset_confirm', args=[uid, token]), follow=True)

    assert response.status_code == 200


# ── Alcance a partir das duas telas de acesso ──────────────────────────────

@pytest.mark.django_db
def test_reset_is_linked_from_unified_login(client):
    content = client.get(reverse('panel:login')).content.decode()

    assert reverse('accounts:password_reset') in content


@pytest.mark.django_db
def test_reset_is_linked_from_reader_login(client):
    content = client.get(reverse('accounts:login')).content.decode()

    assert reverse('accounts:password_reset') in content


@pytest.mark.django_db
def test_complete_page_offers_both_entry_points(client):
    content = client.get(reverse('accounts:password_reset_complete')).content.decode()

    assert reverse('accounts:login') in content
    assert reverse('panel:login') in content
    # Comentário {# #} do Django é de UMA linha só: escrito em duas, vaza como
    # texto visível na página. Já aconteceu aqui.
    assert '{#' not in content
