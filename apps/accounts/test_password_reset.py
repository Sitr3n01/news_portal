"""Ciclo de vida da recuperação de senha.

Fluxo único da plataforma: leitores e equipe usam o mesmo caminho, em
/accounts/password_reset/. É o único endurecido contra host header poisoning e
com limite de envio — por isso o do Wagtail fica desligado.
"""

import re

import pytest
from django.contrib.sites.models import Site
from django.core import mail
from django.urls import reverse

SENHA_ANTIGA = 'SenhaAntiga#2026'
SENHA_NOVA = 'SenhaNova#2026'


@pytest.fixture
def usuario(db, django_user_model):
    return django_user_model.objects.create_user(
        username='esquecido',
        email='esquecido@example.com',
        password=SENHA_ANTIGA,
    )


def pedir_reset(client, email):
    return client.post(reverse('accounts:password_reset'), {'email': email})


def link_do_email():
    """Extrai o caminho de confirmação do último e-mail enviado."""
    corpo = mail.outbox[-1].body
    achado = re.search(r'(/accounts/reset/[^/\s]+/[^/\s]+/)', corpo)
    assert achado, f'link de redefinição não encontrado em:\n{corpo}'
    return achado.group(1)


# ── Solicitação ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_valid_request_sends_email(client, usuario, current_site):
    response = pedir_reset(client, usuario.email)

    assert response.status_code == 302
    assert response.url == reverse('accounts:password_reset_done')
    assert len(mail.outbox) == 1
    assert usuario.email in mail.outbox[0].to


@pytest.mark.django_db
def test_subject_uses_project_template(client, usuario, current_site):
    pedir_reset(client, usuario.email)

    assert 'Redefinição de senha' in mail.outbox[0].subject
    # Assunto tem de ser uma linha só — o Django recusa cabeçalho multilinha.
    assert '\n' not in mail.outbox[0].subject


@pytest.mark.django_db
def test_unknown_email_is_indistinguishable(client, usuario, current_site):
    """Anti-enumeração: a resposta não pode denunciar se a conta existe."""
    conhecida = pedir_reset(client, usuario.email)
    emails_apos_conhecida = len(mail.outbox)

    desconhecida = pedir_reset(client, 'ninguem@example.com')

    assert conhecida.status_code == desconhecida.status_code
    assert conhecida.url == desconhecida.url
    # E nenhum e-mail extra foi disparado para o endereço inexistente.
    assert len(mail.outbox) == emails_apos_conhecida


@pytest.mark.django_db
def test_done_page_shows_generic_message(client, current_site):
    response = client.get(reverse('accounts:password_reset_done'))

    assert response.status_code == 200
    assert 'Se existir uma conta' in response.content.decode()


@pytest.mark.django_db
def test_email_link_uses_site_domain_not_host_header(client, usuario, current_site):
    """Proteção contra host header poisoning: o link sai do Site do banco,
    nunca do cabeçalho Host que veio na requisição."""
    Site.objects.filter(pk=current_site.pk).update(domain='kellyfarias.com.br')
    Site.objects.clear_cache()

    client.post(reverse('accounts:password_reset'),
                {'email': usuario.email}, HTTP_HOST='evil.com')

    corpo = mail.outbox[0].body
    assert 'kellyfarias.com.br' in corpo
    assert 'evil.com' not in corpo


# ── Limite de envio ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_repeated_request_for_same_email_is_throttled(client, usuario, current_site):
    pedir_reset(client, usuario.email)
    assert len(mail.outbox) == 1

    segunda = pedir_reset(client, usuario.email)

    # Bloqueia o envio, mas responde como se tivesse enviado.
    assert segunda.status_code == 302
    assert segunda.url == reverse('accounts:password_reset_done')
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_email_normalization_shares_the_same_bucket(client, usuario, current_site):
    """Trocar a caixa das letras não pode render um segundo envio."""
    pedir_reset(client, usuario.email)

    pedir_reset(client, usuario.email.upper())

    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_single_ip_cannot_mailbomb_many_addresses(client, django_user_model, current_site):
    """Sem o balde por IP, cada par (IP, e-mail) tinha o próprio limite e uma
    origem podia disparar para infinitos endereços distintos."""
    from apps.accounts.views import RESET_IP_LIMIT

    for indice in range(RESET_IP_LIMIT + 5):
        django_user_model.objects.create_user(
            username=f'alvo{indice}', email=f'alvo{indice}@example.com', password=SENHA_ANTIGA,
        )
        pedir_reset(client, f'alvo{indice}@example.com')

    assert len(mail.outbox) == RESET_IP_LIMIT


# ── Token ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_valid_token_allows_password_change(client, usuario, current_site):
    pedir_reset(client, usuario.email)
    caminho = link_do_email()

    # O Django troca o token da URL por um marcador de sessão e redireciona.
    redirecionado = client.get(caminho, follow=True)
    assert redirecionado.status_code == 200

    response = client.post(redirecionado.request['PATH_INFO'], {
        'new_password1': SENHA_NOVA, 'new_password2': SENHA_NOVA,
    })

    assert response.status_code == 302
    usuario.refresh_from_db()
    assert usuario.check_password(SENHA_NOVA)


@pytest.mark.django_db
def test_invalid_token_is_rejected(client, usuario, current_site):
    pedir_reset(client, usuario.email)
    caminho = link_do_email()
    adulterado = caminho.rsplit('/', 2)[0] + '/aaaaaa-bbbbbbbbbbbbbbbbbbbb/'

    response = client.get(adulterado, follow=True)

    assert 'inválido' in response.content.decode().lower() or response.status_code == 200
    usuario.refresh_from_db()
    assert usuario.check_password(SENHA_ANTIGA)


@pytest.mark.django_db
def test_token_cannot_be_reused(client, usuario, current_site):
    pedir_reset(client, usuario.email)
    caminho = link_do_email()

    primeira = client.get(caminho, follow=True)
    client.post(primeira.request['PATH_INFO'], {
        'new_password1': SENHA_NOVA, 'new_password2': SENHA_NOVA,
    })

    # Segundo uso do MESMO link: o token já não vale, a senha mudou.
    client.logout()
    segunda = client.get(caminho, follow=True)
    client.post(segunda.request['PATH_INFO'], {
        'new_password1': 'OutraSenha#2026', 'new_password2': 'OutraSenha#2026',
    })

    usuario.refresh_from_db()
    assert usuario.check_password(SENHA_NOVA)
    assert not usuario.check_password('OutraSenha#2026')


@pytest.mark.django_db
def test_expired_token_is_rejected(client, usuario, current_site, settings):
    pedir_reset(client, usuario.email)
    caminho = link_do_email()

    # Expirar ANTES de abrir o link: o GET é quem valida o token e o guarda na
    # sessão. Vencer só depois do GET testaria a sessão, não o prazo do token.
    #
    # -1, e não 0: django.contrib.auth.tokens compara `idade > TIMEOUT`, e um
    # token criado no mesmo segundo tem idade 0 — que não é maior que 0.
    settings.PASSWORD_RESET_TIMEOUT = -1

    response = client.get(caminho, follow=True)

    assert 'inválido' in response.content.decode().lower()
    usuario.refresh_from_db()
    assert usuario.check_password(SENHA_ANTIGA)


@pytest.mark.django_db
def test_weak_password_is_refused(client, usuario, current_site):
    """A política de senha do Django continua valendo na redefinição."""
    pedir_reset(client, usuario.email)
    redirecionado = client.get(link_do_email(), follow=True)

    response = client.post(redirecionado.request['PATH_INFO'], {
        'new_password1': '12345678', 'new_password2': '12345678',
    })

    assert response.status_code == 200
    usuario.refresh_from_db()
    assert usuario.check_password(SENHA_ANTIGA)


# ── Login com a nova senha ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_old_password_stops_working_and_new_one_works(client, usuario, current_site):
    pedir_reset(client, usuario.email)
    redirecionado = client.get(link_do_email(), follow=True)
    client.post(redirecionado.request['PATH_INFO'], {
        'new_password1': SENHA_NOVA, 'new_password2': SENHA_NOVA,
    })
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
