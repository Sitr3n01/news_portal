"""Login com Google: autentica, mas NUNCA autoriza.

A pergunta que todo teste aqui responde é a mesma: entrar pelo Google mudou
alguma coisa no que a pessoa pode fazer? A resposta tem de ser não — nem para
mais (leitor virando equipe), nem para menos (repórter perdendo o painel).

O ida-e-volta com o Google é simulado nos limites do módulo
apps.accounts.oauth_google (exchange_code e verify_id_token): a rede real não
entra na suíte, mas TODO o resto — state, sessão, resolução de conta, axes,
roteamento pós-login — roda de verdade.
"""

import pytest
from django.urls import reverse

from apps.accounts import oauth_google, oauth_views
from apps.accounts.models import CustomUser, GoogleIdentity

SENHA = 'SenhaTeste#2026'
SUB_PADRAO = 'google-sub-1234567890'


@pytest.fixture
def oauth_ligado(settings):
    settings.GOOGLE_OAUTH_CLIENT_ID = 'client-id-de-teste.apps.googleusercontent.com'
    settings.GOOGLE_OAUTH_CLIENT_SECRET = 'segredo-de-teste'
    settings.GOOGLE_OAUTH_REDIRECT_URI = 'http://testserver/accounts/google/callback/'
    settings.GOOGLE_OAUTH_ENABLED = True
    return settings


def claims(email, sub=SUB_PADRAO, given_name='Fulano', family_name='Silva'):
    return {'sub': sub, 'email': email, 'given_name': given_name, 'family_name': family_name}


def simular_google(monkeypatch, retorno):
    """Substitui os dois pontos de rede do fluxo, mantendo o resto real."""
    monkeypatch.setattr(oauth_google, 'exchange_code', lambda code, verifier: 'id-token-falso')
    monkeypatch.setattr(oauth_google, 'verify_id_token', lambda raw, nonce: retorno)


def entrar_com_google(client, monkeypatch, retorno, next_url=''):
    """Percorre o fluxo inteiro: ida (guarda state na sessão) e volta."""
    simular_google(monkeypatch, retorno)
    url_ida = reverse('accounts:google_start')
    if next_url:
        url_ida = f'{url_ida}?next={next_url}'
    client.get(url_ida)
    state = client.session[oauth_views.SESSION_KEY]['state']
    return client.get(reverse('accounts:google_callback'), {'code': 'codigo-falso', 'state': state})


# ── Interruptor de configuração ─────────────────────────────────────────────

@pytest.mark.django_db
def test_routes_are_404_without_credentials(client, settings):
    """Sem credencial, a rota não existe — nada de endpoint meio configurado."""
    settings.GOOGLE_OAUTH_ENABLED = False

    assert client.get(reverse('accounts:google_start')).status_code == 404
    assert client.get(reverse('accounts:google_callback')).status_code == 404


@pytest.mark.django_db
def test_button_is_hidden_without_credentials(client, settings):
    settings.GOOGLE_OAUTH_ENABLED = False

    conteudo = client.get(reverse('accounts:login')).content.decode()

    assert 'Entrar com Google' not in conteudo


@pytest.mark.django_db
def test_button_shows_on_both_login_screens(client, oauth_ligado):
    """As duas portas — leitor e equipe — oferecem o Google."""
    assert 'Entrar com Google' in client.get(reverse('accounts:login')).content.decode()
    assert 'Entrar com Google' in client.get(reverse('panel:login')).content.decode()


# ── Criação de usuário ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_new_user_is_created_at_the_lowest_privilege(client, monkeypatch, oauth_ligado, current_site):
    """Conta nascida no Google entra no piso: leitor, sem grupo, sem is_staff."""
    entrar_com_google(client, monkeypatch, claims('novato@gmail.com'))

    user = CustomUser.objects.get(email='novato@gmail.com')
    assert user.role == CustomUser.Role.READER
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.groups.count() == 0
    assert user.has_perm('wagtailadmin.access_admin') is False
    # E-mail já confirmado pelo próprio Google — não faz sentido pedir código.
    assert user.email_verified is True
    assert user.has_usable_password() is False


@pytest.mark.django_db
def test_new_user_gets_google_identity_linked(client, monkeypatch, oauth_ligado, current_site):
    entrar_com_google(client, monkeypatch, claims('novato@gmail.com'))

    identity = GoogleIdentity.objects.get(google_sub=SUB_PADRAO)
    assert identity.user.email == 'novato@gmail.com'
    assert identity.last_login_at is not None


# ── Conta existente: permissões PRESERVADAS ─────────────────────────────────

@pytest.mark.django_db
def test_existing_reporter_keeps_permissions_and_lands_on_cms(client, monkeypatch, oauth_ligado, make_panel_user, current_site):
    """O cenário central: repórter entra pelo Google e continua repórter."""
    reporter = make_panel_user('repo_google', role=CustomUser.Role.REPORTER)
    grupos_antes = set(reporter.groups.values_list('name', flat=True))

    response = entrar_com_google(client, monkeypatch, claims(reporter.email))

    reporter.refresh_from_db()
    assert reporter.role == CustomUser.Role.REPORTER
    assert set(reporter.groups.values_list('name', flat=True)) == grupos_antes
    assert reporter.has_perm('wagtailadmin.access_admin') is True
    # Cai na publicação de matérias, exatamente como no login por senha.
    assert response.status_code == 302
    assert response.url == reverse('wagtailadmin_home')
    # E nenhuma conta duplicada nasceu.
    assert CustomUser.objects.filter(email__iexact=reporter.email).count() == 1


@pytest.mark.django_db
def test_existing_admin_keeps_staff_and_gets_the_picker(client, monkeypatch, oauth_ligado, make_panel_user, current_site):
    admin = make_panel_user('admin_google', role=CustomUser.Role.SUPER_ADMIN, is_staff=True)

    response = entrar_com_google(client, monkeypatch, claims(admin.email))

    admin.refresh_from_db()
    assert admin.is_staff is True
    assert admin.role == CustomUser.Role.SUPER_ADMIN
    # Alcança as duas áreas -> escolhe na tela, igual ao login por senha.
    assert response.url == reverse('panel:picker')


@pytest.mark.django_db
def test_existing_superuser_keeps_superuser(client, monkeypatch, oauth_ligado, make_panel_user, current_site):
    su = make_panel_user('su_google', role=CustomUser.Role.SUPER_ADMIN, is_staff=True, is_superuser=True)

    entrar_com_google(client, monkeypatch, claims(su.email))

    su.refresh_from_db()
    assert su.is_superuser is True
    assert su.is_staff is True


@pytest.mark.django_db
def test_plain_reader_gains_nothing(client, monkeypatch, oauth_ligado, django_user_model, current_site):
    """Entrar pelo Google não promove ninguém."""
    leitor = django_user_model.objects.create_user(
        username='leitor', email='leitor@example.com', password=SENHA,
    )

    response = entrar_com_google(client, monkeypatch, claims(leitor.email))

    leitor.refresh_from_db()
    assert leitor.is_staff is False
    assert leitor.role == CustomUser.Role.READER
    assert leitor.groups.count() == 0
    assert response.url == reverse('news:list')


# ── Identidade: sem duplicata, sem sequestro ────────────────────────────────

@pytest.mark.django_db
def test_email_capitalization_matches_the_same_account(client, monkeypatch, oauth_ligado, django_user_model, current_site):
    """Conta antiga gravada com maiúsculas é reconhecida, não duplicada."""
    django_user_model.objects.create_user(
        username='misto', email='Misto.Caso@example.com', password=SENHA,
    )

    entrar_com_google(client, monkeypatch, claims('misto.caso@example.com'))

    assert CustomUser.objects.filter(email__iexact='misto.caso@example.com').count() == 1
    assert GoogleIdentity.objects.count() == 1


@pytest.mark.django_db
def test_second_login_reuses_the_same_account(client, monkeypatch, oauth_ligado, current_site):
    entrar_com_google(client, monkeypatch, claims('repetido@gmail.com'))
    client.logout()
    entrar_com_google(client, monkeypatch, claims('repetido@gmail.com'))

    assert CustomUser.objects.filter(email='repetido@gmail.com').count() == 1
    assert GoogleIdentity.objects.count() == 1


@pytest.mark.django_db
def test_sub_wins_over_email_when_google_email_changes(client, monkeypatch, oauth_ligado, current_site):
    """Trocar o e-mail no Google não pode trocar a conta local alcançada.

    O vínculo é pelo `sub` (imutável). Se a busca fosse por e-mail, mudar o
    endereço no Google levaria a pessoa para outra conta — ou criaria uma
    duplicada.
    """
    entrar_com_google(client, monkeypatch, claims('antigo@gmail.com'))
    user_pk = CustomUser.objects.get(email='antigo@gmail.com').pk
    client.logout()

    entrar_com_google(client, monkeypatch, claims('novo-endereco@gmail.com', sub=SUB_PADRAO))

    assert CustomUser.objects.count() == 1
    assert CustomUser.objects.first().pk == user_pk


@pytest.mark.django_db
def test_different_sub_same_email_does_not_hijack(client, monkeypatch, oauth_ligado, django_user_model, current_site):
    """Outro `sub` com o mesmo e-mail confirmado casa na conta existente.

    É o caminho legítimo de quem tinha senha local e passou a usar o Google —
    e por isso mesmo depende de `email_verified`, exigido em
    oauth_google.verify_id_token: sem essa garantia, declarar o e-mail de
    outra pessoa bastaria para assumir a conta dela.
    """
    dono = django_user_model.objects.create_user(
        username='dono', email='dono@example.com', password=SENHA,
    )

    entrar_com_google(client, monkeypatch, claims(dono.email, sub='outro-sub-999'))

    assert CustomUser.objects.filter(email='dono@example.com').count() == 1
    assert GoogleIdentity.objects.get(google_sub='outro-sub-999').user_id == dono.pk
    # A senha local continua valendo: ganhar o Google não tira o outro método.
    dono.refresh_from_db()
    assert dono.check_password(SENHA) is True


# ── Recusas ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_disabled_account_is_refused_before_login(client, monkeypatch, oauth_ligado, django_user_model, current_site):
    """Conta desativada não entra — e a recusa vem ANTES de abrir sessão."""
    django_user_model.objects.create_user(
        username='banido', email='banido@example.com', password=SENHA, is_active=False,
    )

    response = entrar_com_google(client, monkeypatch, claims('banido@example.com'))

    assert response.status_code == 403
    assert '_auth_user_id' not in client.session


@pytest.mark.django_db
def test_unverified_google_email_is_refused(client, monkeypatch, oauth_ligado, current_site):
    """Sem email_verified do Google, não há casamento por e-mail possível."""
    def recusar(raw, nonce):
        raise oauth_google.GoogleOAuthError('email_unverified', 'O Google ainda não confirmou esse e-mail.')

    monkeypatch.setattr(oauth_google, 'exchange_code', lambda code, verifier: 'id-token-falso')
    monkeypatch.setattr(oauth_google, 'verify_id_token', recusar)

    client.get(reverse('accounts:google_start'))
    state = client.session[oauth_views.SESSION_KEY]['state']
    response = client.get(reverse('accounts:google_callback'), {'code': 'c', 'state': state})

    assert response.status_code == 302
    assert '_auth_user_id' not in client.session
    assert CustomUser.objects.count() == 0


@pytest.mark.django_db
def test_callback_without_session_flow_is_refused(client, oauth_ligado, current_site):
    """Login-CSRF: chegar na volta sem ter passado pela ida é recusado."""
    response = client.get(reverse('accounts:google_callback'), {'code': 'c', 'state': 'inventado'})

    assert response.status_code == 302
    assert '_auth_user_id' not in client.session


@pytest.mark.django_db
def test_state_mismatch_is_refused(client, monkeypatch, oauth_ligado, current_site):
    simular_google(monkeypatch, claims('alguem@gmail.com'))
    client.get(reverse('accounts:google_start'))

    response = client.get(reverse('accounts:google_callback'), {'code': 'c', 'state': 'state-errado'})

    assert response.status_code == 302
    assert '_auth_user_id' not in client.session
    assert CustomUser.objects.count() == 0


@pytest.mark.django_db
def test_flow_is_single_use(client, monkeypatch, oauth_ligado, current_site):
    """O mesmo state não vale duas vezes."""
    entrar_com_google(client, monkeypatch, claims('umavez@gmail.com'))
    client.logout()

    # O fluxo foi consumido (pop) na primeira volta; repetir não autentica.
    response = client.get(reverse('accounts:google_callback'), {'code': 'c', 'state': 'qualquer'})

    assert '_auth_user_id' not in client.session
    assert response.status_code == 302


@pytest.mark.django_db
def test_user_cancelled_on_google(client, monkeypatch, oauth_ligado, current_site):
    simular_google(monkeypatch, claims('desistiu@gmail.com'))
    client.get(reverse('accounts:google_start'))
    state = client.session[oauth_views.SESSION_KEY]['state']

    response = client.get(reverse('accounts:google_callback'), {'error': 'access_denied', 'state': state})

    assert response.status_code == 302
    assert CustomUser.objects.count() == 0


# ── Destino pós-login ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_external_next_is_discarded(client, monkeypatch, oauth_ligado, current_site):
    """Open redirect: destino externo é jogado fora na ida."""
    simular_google(monkeypatch, claims('alguem@gmail.com'))

    client.get(reverse('accounts:google_start'), {'next': 'https://evil.example.com/'})

    assert client.session[oauth_views.SESSION_KEY]['next'] == ''


@pytest.mark.django_db
def test_forbidden_next_sends_to_no_access_not_to_the_panel(client, monkeypatch, oauth_ligado, django_user_model, current_site):
    """Pedir uma área proibida no `next` leva à página de sem acesso.

    Mesma regra do login por senha (panels.post_login_target) — o Google não
    abre atalho nenhum para um painel que a conta não alcança.
    """
    django_user_model.objects.create_user(
        username='leitor2', email='leitor2@example.com', password=SENHA,
    )

    response = entrar_com_google(client, monkeypatch, claims('leitor2@example.com'), next_url='/admin/')

    assert reverse('panel:no_access') in response.url


# ── Nome de usuário derivado ────────────────────────────────────────────────

@pytest.mark.django_db
def test_username_collision_gets_a_suffix(client, monkeypatch, oauth_ligado, django_user_model, current_site):
    """Duas pessoas com a mesma parte local do e-mail não colidem."""
    django_user_model.objects.create_user(
        username='contato', email='contato@dominio-a.com', password=SENHA,
    )

    entrar_com_google(client, monkeypatch, claims('contato@dominio-b.com'))

    novo = CustomUser.objects.get(email='contato@dominio-b.com')
    assert novo.username != 'contato'
    assert novo.username.startswith('contato')
