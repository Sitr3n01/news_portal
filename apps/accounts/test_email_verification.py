"""Confirmação de e-mail por código, com BLOQUEIO SUAVE (Fase 3).

Bloqueio suave = a conta existe e a pessoa ENTRA normalmente; só fica
impedida de comentar/curtir/salvar enquanto não confirmar. Por isso os testes
de "não consegue comentar" usam force_login (a pessoa está autenticada de
verdade) — o que está em jogo é email_verified, nunca is_active nem sessão.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import VerificationCode
from apps.accounts.verification import ISSUE_LIMIT_PER_IDENTITY, MAX_ATTEMPTS, issue_code
from apps.common import turnstile
from apps.news.models import Article

PURPOSE = VerificationCode.Purpose.EMAIL_VERIFICATION
SENHA = 'SenhaTeste#2026'


def mock_turnstile(monkeypatch, *, valid=True):
    """Mesmo padrão de apps/news/tests.py: substitui a chamada de rede real
    por uma checagem de token fixo, sem depender das chaves de teste da
    Cloudflare (que nem entram em jogo aqui — settings.test define DEBUG=False,
    então get_turnstile_secret_key() nem cairia no fallback de teste)."""
    monkeypatch.setattr(turnstile, 'verify_turnstile', lambda token, remote_ip='': valid and token == 'valid-token')


def codigo_errado_para(codigo_certo):
    """Gera um código de 6 dígitos garantidamente diferente do informado
    (mesma ideia de apps/accounts/test_verification.py): sorteio puro tem
    1 em 1.000.000 de chance de coincidir com o código real e virar um teste
    instável; trocar cada dígito elimina essa chance por construção."""
    return ''.join('9' if digito != '9' else '8' for digito in codigo_certo)


def make_article(site, slug='artigo-verificacao'):
    return Article.objects.create(
        title=f'Artigo {slug}',
        slug=slug,
        excerpt='Resumo do artigo',
        content='Conteúdo do artigo para o teste de comentário.',
        site=site,
        status=Article.Status.PUBLISHED,
    )


@pytest.fixture
def leitor(db, django_user_model):
    """Usuário comum recém-cadastrado: email_verified=False por padrão do modelo."""
    return django_user_model.objects.create_user(
        username='leitora', email='leitora@example.com', password=SENHA,
    )


@pytest.fixture
def staff_nao_verificado(db, django_user_model):
    """Equivalente a um usuário criado por createsuperuser/admin: nunca passou
    pelo fluxo de código, mas é isento por ser is_staff."""
    return django_user_model.objects.create_user(
        username='editor-novo', email='editor-novo@example.com', password=SENHA,
        is_staff=True,
    )


# ── Cadastro dispara o fluxo de confirmação ──────────────────────────────────

@pytest.mark.django_db
def test_register_creates_unverified_user_sends_one_email_and_redirects(client, monkeypatch, current_site):
    mock_turnstile(monkeypatch)

    response = client.post(reverse('accounts:register'), {
        'username': 'novaleitora',
        'email': 'novaleitora@example.com',
        'password1': SENHA,
        'password2': SENHA,
        'cf-turnstile-response': 'valid-token',
    })

    assert response.status_code == 302
    assert response.url == reverse('accounts:verify_email')
    user = get_user_model().objects.get(username='novaleitora')
    assert user.email_verified is False
    assert len(mail.outbox) == 1
    assert user.email in mail.outbox[0].to


@pytest.mark.django_db
def test_register_rejects_invalid_turnstile_creates_no_user_sends_no_email(client, monkeypatch, current_site):
    mock_turnstile(monkeypatch, valid=False)

    response = client.post(reverse('accounts:register'), {
        'username': 'bloqueada',
        'email': 'bloqueada@example.com',
        'password1': SENHA,
        'password2': SENHA,
        'cf-turnstile-response': 'bad-token',
    })

    assert response.status_code == 200  # form volta com erro, sem redirect
    assert not get_user_model().objects.filter(username='bloqueada').exists()
    assert len(mail.outbox) == 0


# ── Confirmação: caminho feliz e mensagens de erro ───────────────────────────

@pytest.mark.django_db
def test_correct_code_verifies_email_and_redirects_to_news_list(client, leitor):
    client.force_login(leitor)
    codigo = issue_code(leitor, PURPOSE)

    response = client.post(reverse('accounts:verify_email'), {'code': codigo})

    assert response.status_code == 302
    assert response.url == reverse('news:list')
    leitor.refresh_from_db()
    assert leitor.email_verified is True
    assert leitor.email_verified_at is not None


@pytest.mark.django_db
def test_wrong_code_keeps_unverified_and_shows_invalid_message(client, leitor):
    client.force_login(leitor)
    codigo_certo = issue_code(leitor, PURPOSE)

    response = client.post(
        reverse('accounts:verify_email'),
        {'code': codigo_errado_para(codigo_certo)},
        follow=True,
    )

    leitor.refresh_from_db()
    assert leitor.email_verified is False
    mensagens = [str(m) for m in response.context['messages']]
    assert any('Código inválido' in m for m in mensagens)


@pytest.mark.django_db
def test_expired_code_shows_expired_message(client, leitor):
    client.force_login(leitor)
    codigo = issue_code(leitor, PURPOSE)
    VerificationCode.objects.filter(user=leitor, purpose=PURPOSE).update(
        expires_at=timezone.now() - timedelta(seconds=1),
    )

    response = client.post(reverse('accounts:verify_email'), {'code': codigo}, follow=True)

    leitor.refresh_from_db()
    assert leitor.email_verified is False
    mensagens = [str(m) for m in response.context['messages']]
    assert any('expirou' in m for m in mensagens)


@pytest.mark.django_db
def test_used_code_cannot_verify_again(client, leitor):
    client.force_login(leitor)
    codigo = issue_code(leitor, PURPOSE)
    primeira = client.post(reverse('accounts:verify_email'), {'code': codigo})
    assert primeira.status_code == 302

    # Força de volta a não-verificado só para isolar o comportamento do
    # CÓDIGO reutilizado: a view em si já barra reentrada via "já verificado"
    # (ver test_already_verified_user_opening_verify_email_is_redirected) —
    # este teste prova que o código-fonte não valeria de novo mesmo que essa
    # barreira não existisse.
    leitor.email_verified = False
    leitor.save(update_fields=['email_verified'])

    response = client.post(reverse('accounts:verify_email'), {'code': codigo}, follow=True)

    leitor.refresh_from_db()
    assert leitor.email_verified is False
    mensagens = [str(m) for m in response.context['messages']]
    assert any('Nenhum código pendente' in m for m in mensagens)


@pytest.mark.django_db
def test_five_wrong_attempts_then_sixth_shows_too_many_attempts(client, leitor):
    client.force_login(leitor)
    codigo_certo = issue_code(leitor, PURPOSE)
    codigo_errado = codigo_errado_para(codigo_certo)

    for _ in range(MAX_ATTEMPTS):
        client.post(reverse('accounts:verify_email'), {'code': codigo_errado})

    response = client.post(reverse('accounts:verify_email'), {'code': codigo_errado}, follow=True)

    leitor.refresh_from_db()
    assert leitor.email_verified is False
    mensagens = [str(m) for m in response.context['messages']]
    assert any('Muitas tentativas' in m for m in mensagens)


@pytest.mark.django_db
def test_already_verified_user_opening_verify_email_is_redirected(client, leitor):
    leitor.email_verified = True
    leitor.email_verified_at = timezone.now()
    leitor.save(update_fields=['email_verified', 'email_verified_at'])
    client.force_login(leitor)

    response = client.get(reverse('accounts:verify_email'))

    assert response.status_code == 302
    assert response.url == reverse('news:list')


# ── Reenvio ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_resend_post_issues_new_code_and_sends_email(client, leitor):
    client.force_login(leitor)
    issue_code(leitor, PURPOSE)  # código "antigo", como se viesse do próprio cadastro

    response = client.post(reverse('accounts:resend_verification_code'))

    assert response.status_code == 302
    assert response.url == reverse('accounts:verify_email')
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_resend_get_is_not_allowed_and_sends_nothing(client, leitor):
    client.force_login(leitor)

    response = client.get(reverse('accounts:resend_verification_code'))

    assert response.status_code == 405
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_resend_rate_limit_shows_generic_message_without_exceeding_it(client, leitor):
    client.force_login(leitor)

    for _ in range(ISSUE_LIMIT_PER_IDENTITY):
        client.post(reverse('accounts:resend_verification_code'))
    assert len(mail.outbox) == ISSUE_LIMIT_PER_IDENTITY

    response = client.post(reverse('accounts:resend_verification_code'), follow=True)

    assert len(mail.outbox) == ISSUE_LIMIT_PER_IDENTITY  # não passou disso
    mensagens = [str(m) for m in response.context['messages']]
    assert any('Você pediu códigos demais' in m for m in mensagens)


# ── Bloqueio suave nas interações (news.views) ───────────────────────────────

@pytest.mark.django_db
def test_unverified_user_cannot_comment_but_can_after_verifying(client, leitor, current_site):
    article = make_article(current_site)
    client.force_login(leitor)

    bloqueado = client.post(reverse('news:add_comment', args=[article.id]), {'content': 'Ótimo artigo!'})
    assert bloqueado.status_code == 302
    assert bloqueado.url == reverse('accounts:verify_email')
    assert article.comments.count() == 0

    codigo = issue_code(leitor, PURPOSE)
    client.post(reverse('accounts:verify_email'), {'code': codigo})

    liberado = client.post(reverse('news:add_comment', args=[article.id]), {'content': 'Ótimo artigo!'})
    assert liberado.status_code == 302
    assert article.comments.count() == 1


@pytest.mark.django_db
def test_unverified_staff_can_comment(client, staff_nao_verificado, current_site):
    article = make_article(current_site)
    client.force_login(staff_nao_verificado)

    response = client.post(reverse('news:add_comment', args=[article.id]), {'content': 'Comentário da redação.'})

    assert response.status_code == 302
    assert article.comments.count() == 1


# ── Faixa de aviso em base_news.html ─────────────────────────────────────────

@pytest.mark.django_db
def test_banner_shows_for_unverified_reader(client, leitor, current_site):
    make_article(current_site)
    client.force_login(leitor)

    content = client.get(reverse('news:list')).content.decode()

    assert 'Confirme seu e-mail para comentar, curtir e salvar artigos.' in content


@pytest.mark.django_db
def test_banner_hidden_for_verified_reader(client, leitor, current_site):
    make_article(current_site)
    leitor.email_verified = True
    leitor.save(update_fields=['email_verified'])
    client.force_login(leitor)

    content = client.get(reverse('news:list')).content.decode()

    assert 'Confirme seu e-mail para comentar, curtir e salvar artigos.' not in content


@pytest.mark.django_db
def test_banner_hidden_for_staff(client, staff_nao_verificado, current_site):
    make_article(current_site)
    client.force_login(staff_nao_verificado)

    content = client.get(reverse('news:list')).content.decode()

    assert 'Confirme seu e-mail para comentar, curtir e salvar artigos.' not in content


# ── Regressão: login tradicional continua funcionando ────────────────────────

@pytest.mark.django_db
def test_reader_login_still_works(client, leitor):
    client.post(reverse('accounts:login'), {'username': leitor.get_username(), 'password': SENHA})

    assert client.session.get('_auth_user_id') == str(leitor.pk)


@pytest.mark.django_db
def test_panel_login_still_works(client, leitor):
    client.post(reverse('panel:login'), {'username': leitor.get_username(), 'password': SENHA})

    assert client.session.get('_auth_user_id') == str(leitor.pk)
