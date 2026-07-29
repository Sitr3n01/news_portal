"""Emissão e validação de códigos de verificação (apps.accounts.verification).

Fluxo único compartilhado por confirmação de e-mail e recuperação de senha —
por isso os testes não fixam um propósito só: onde faz diferença (escopo por
propósito, por usuário), o teste cobre isso explicitamente.
"""

import secrets
from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.test import RequestFactory
from django.utils import timezone

from apps.accounts.models import GoogleIdentity, VerificationCode
from apps.accounts.verification import (
    CHECK_LIMIT_PER_IP,
    ISSUE_LIMIT_PER_IDENTITY,
    MAX_ATTEMPTS,
    CodeCheckStatus,
    check_code,
    invalidate_all,
    issue_code,
)

PURPOSE = VerificationCode.Purpose.EMAIL_VERIFICATION
OUTRO_PROPOSITO = VerificationCode.Purpose.PASSWORD_RESET


@pytest.fixture
def usuario(db, django_user_model):
    return django_user_model.objects.create_user(
        username='usuaria', email='usuaria@example.com', password='SenhaTeste#2026',
    )


@pytest.fixture
def outro_usuario(db, django_user_model):
    return django_user_model.objects.create_user(
        username='outra-pessoa', email='outra@example.com', password='SenhaTeste#2026',
    )


def codigo_errado_para(codigo_certo):
    """Gera um código de 6 dígitos garantidamente diferente do informado.

    Sorteio puro ('000000' etc.) tem 1 em 1.000.000 de chance de coincidir
    com o código real emitido e virar um teste instável — trocar cada dígito
    elimina essa chance por construção.
    """
    return ''.join('9' if digito != '9' else '8' for digito in codigo_certo)


# ── Emissão ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_issued_code_has_six_digits(usuario):
    codigo = issue_code(usuario, PURPOSE)

    assert codigo is not None
    assert len(codigo) == 6
    assert codigo.isdigit()


@pytest.mark.django_db
def test_issued_code_differs_between_emissions(usuario):
    primeiro = issue_code(usuario, PURPOSE)
    segundo = issue_code(usuario, PURPOSE)

    assert primeiro != segundo


@pytest.mark.django_db
def test_raw_code_is_never_persisted_in_any_field(usuario):
    codigo = issue_code(usuario, PURPOSE)

    linha = VerificationCode.objects.get(user=usuario, purpose=PURPOSE)
    for campo in VerificationCode._meta.fields:
        valor = getattr(linha, campo.name)
        assert str(valor) != codigo, f'o campo {campo.name} guardou o código em texto puro'


# ── Validação: caminho feliz e casos de erro ─────────────────────────────────

@pytest.mark.django_db
def test_correct_code_returns_ok_and_stamps_used_at(usuario):
    codigo = issue_code(usuario, PURPOSE)

    resultado = check_code(usuario, PURPOSE, codigo)

    assert resultado.status is CodeCheckStatus.OK
    assert resultado.code.used_at is not None


@pytest.mark.django_db
def test_wrong_code_returns_invalid_and_increments_attempts(usuario):
    codigo_certo = issue_code(usuario, PURPOSE)

    resultado = check_code(usuario, PURPOSE, codigo_errado_para(codigo_certo))

    assert resultado.status is CodeCheckStatus.INVALID
    assert resultado.code.attempts == 1


@pytest.mark.django_db
def test_expired_code_returns_expired(usuario):
    codigo = issue_code(usuario, PURPOSE)
    VerificationCode.objects.filter(user=usuario, purpose=PURPOSE).update(
        expires_at=timezone.now() - timedelta(seconds=1),
    )

    resultado = check_code(usuario, PURPOSE, codigo)

    assert resultado.status is CodeCheckStatus.EXPIRED


@pytest.mark.django_db
def test_used_code_is_not_accepted_again(usuario):
    codigo = issue_code(usuario, PURPOSE)
    primeira = check_code(usuario, PURPOSE, codigo)
    assert primeira.status is CodeCheckStatus.OK

    segunda = check_code(usuario, PURPOSE, codigo)

    assert segunda.status is not CodeCheckStatus.OK


@pytest.mark.django_db
def test_five_wrong_attempts_then_sixth_check_is_too_many_attempts(usuario):
    codigo_certo = issue_code(usuario, PURPOSE)
    codigo_errado = codigo_errado_para(codigo_certo)

    for numero_tentativa in range(1, MAX_ATTEMPTS + 1):
        resultado = check_code(usuario, PURPOSE, codigo_errado)
        assert resultado.status is CodeCheckStatus.INVALID
        assert resultado.code.attempts == numero_tentativa

    resultado_seguinte = check_code(usuario, PURPOSE, codigo_errado)
    assert resultado_seguinte.status is CodeCheckStatus.TOO_MANY_ATTEMPTS
    assert resultado_seguinte.code.used_at is not None

    # Queimado: nem o código CERTO passa a valer depois do teto estourado.
    resultado_com_certo = check_code(usuario, PURPOSE, codigo_certo)
    assert resultado_com_certo.status is CodeCheckStatus.TOO_MANY_ATTEMPTS


@pytest.mark.django_db
def test_reissuing_invalidates_the_previous_code(usuario):
    antigo = issue_code(usuario, PURPOSE)
    novo = issue_code(usuario, PURPOSE)
    assert antigo != novo

    resultado_antigo = check_code(usuario, PURPOSE, antigo)
    assert resultado_antigo.status is not CodeCheckStatus.OK

    resultado_novo = check_code(usuario, PURPOSE, novo)
    assert resultado_novo.status is CodeCheckStatus.OK


@pytest.mark.django_db
def test_code_with_internal_spaces_is_accepted(usuario):
    codigo = issue_code(usuario, PURPOSE)
    formatado = f'{codigo[:3]} {codigo[3:]}'

    resultado = check_code(usuario, PURPOSE, formatado)

    assert resultado.status is CodeCheckStatus.OK


@pytest.mark.django_db
def test_code_with_dash_is_accepted(usuario):
    codigo = issue_code(usuario, PURPOSE)
    formatado = f'{codigo[:3]}-{codigo[3:]}'

    resultado = check_code(usuario, PURPOSE, formatado)

    assert resultado.status is CodeCheckStatus.OK


# ── Escopo: propósito e usuário ──────────────────────────────────────────────

@pytest.mark.django_db
def test_code_does_not_validate_for_a_different_purpose(usuario):
    codigo = issue_code(usuario, PURPOSE)

    resultado = check_code(usuario, OUTRO_PROPOSITO, codigo)

    assert resultado.status is CodeCheckStatus.NOT_FOUND


@pytest.mark.django_db
def test_code_does_not_validate_for_a_different_user(usuario, outro_usuario):
    codigo = issue_code(usuario, PURPOSE)

    resultado = check_code(outro_usuario, PURPOSE, codigo)

    assert resultado.status is CodeCheckStatus.NOT_FOUND


# ── Rate limit ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_issue_rate_limit_per_identity_blocks_after_limit(usuario):
    for _ in range(ISSUE_LIMIT_PER_IDENTITY):
        assert issue_code(usuario, PURPOSE) is not None

    assert issue_code(usuario, PURPOSE) is None


@pytest.mark.django_db
def test_check_rate_limit_per_ip_throttles_after_limit(usuario):
    issue_code(usuario, PURPOSE)
    request = RequestFactory().post('/fake-check/')

    for _ in range(CHECK_LIMIT_PER_IP):
        check_code(usuario, PURPOSE, '000000', request=request)

    resultado = check_code(usuario, PURPOSE, '000000', request=request)

    assert resultado.status is CodeCheckStatus.THROTTLED


@pytest.mark.django_db
def test_check_without_request_never_throttles(usuario):
    """Chamada sem request (management command/shell) não tem IP para o balde
    de validação — por isso não deve ser barrada, por mais vezes que rode."""
    issue_code(usuario, PURPOSE)

    for _ in range(CHECK_LIMIT_PER_IP + 5):
        resultado = check_code(usuario, PURPOSE, '000000')
        assert resultado.status is not CodeCheckStatus.THROTTLED


# ── invalidate_all ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_invalidate_all_burns_pending_code(usuario):
    codigo = issue_code(usuario, PURPOSE)

    invalidate_all(usuario)

    resultado = check_code(usuario, PURPOSE, codigo)
    assert resultado.status is not CodeCheckStatus.OK


@pytest.mark.django_db
def test_invalidate_all_can_be_scoped_to_a_single_purpose(usuario):
    codigo_email = issue_code(usuario, VerificationCode.Purpose.EMAIL_VERIFICATION)
    codigo_reset = issue_code(usuario, VerificationCode.Purpose.PASSWORD_RESET)

    invalidate_all(usuario, purpose=VerificationCode.Purpose.EMAIL_VERIFICATION)

    resultado_email = check_code(usuario, VerificationCode.Purpose.EMAIL_VERIFICATION, codigo_email)
    resultado_reset = check_code(usuario, VerificationCode.Purpose.PASSWORD_RESET, codigo_reset)
    assert resultado_email.status is not CodeCheckStatus.OK
    assert resultado_reset.status is CodeCheckStatus.OK


# ── VerificationCode: propriedades de estado do modelo ───────────────────────

@pytest.mark.django_db
def test_model_is_usable_true_for_a_fresh_code(usuario):
    issue_code(usuario, PURPOSE)

    linha = VerificationCode.objects.get(user=usuario, purpose=PURPOSE)

    assert linha.is_usable is True


@pytest.mark.django_db
def test_model_is_usable_false_once_used(usuario):
    codigo = issue_code(usuario, PURPOSE)
    check_code(usuario, PURPOSE, codigo)

    linha = VerificationCode.objects.get(user=usuario, purpose=PURPOSE)

    assert linha.is_used is True
    assert linha.is_usable is False


@pytest.mark.django_db
def test_model_is_usable_false_once_expired(usuario):
    issue_code(usuario, PURPOSE)
    VerificationCode.objects.filter(user=usuario, purpose=PURPOSE).update(
        expires_at=timezone.now() - timedelta(seconds=1),
    )

    linha = VerificationCode.objects.get(user=usuario, purpose=PURPOSE)

    assert linha.is_expired is True
    assert linha.is_usable is False


@pytest.mark.django_db
def test_model_is_usable_false_at_attempts_ceiling(usuario):
    issue_code(usuario, PURPOSE)
    VerificationCode.objects.filter(user=usuario, purpose=PURPOSE).update(attempts=MAX_ATTEMPTS)

    linha = VerificationCode.objects.get(user=usuario, purpose=PURPOSE)

    assert linha.is_usable is False


# ── Comparação em tempo constante ────────────────────────────────────────────

@pytest.mark.django_db
def test_check_code_uses_constant_time_comparison(usuario, monkeypatch):
    """Testa o COMPORTAMENTO (compare_digest foi de fato exercitado), não a
    implementação: o espião chama a função real por baixo, só registra que
    ela passou por ali."""
    codigo = issue_code(usuario, PURPOSE)
    chamadas = []
    original = secrets.compare_digest

    def espiao(a, b):
        chamadas.append((a, b))
        return original(a, b)

    monkeypatch.setattr(secrets, 'compare_digest', espiao)

    check_code(usuario, PURPOSE, codigo)

    assert chamadas, 'secrets.compare_digest deveria ter sido chamado para comparar os hashes'


# ── GoogleIdentity: unicidade por construção ─────────────────────────────────

@pytest.mark.django_db
def test_google_identity_duplicate_sub_raises_integrity_error(usuario, outro_usuario):
    GoogleIdentity.objects.create(user=usuario, google_sub='sub-123', email=usuario.email)

    with pytest.raises(IntegrityError):
        GoogleIdentity.objects.create(user=outro_usuario, google_sub='sub-123', email=outro_usuario.email)


@pytest.mark.django_db
def test_google_identity_second_link_for_same_user_raises_integrity_error(usuario):
    GoogleIdentity.objects.create(user=usuario, google_sub='sub-abc', email=usuario.email)

    with pytest.raises(IntegrityError):
        GoogleIdentity.objects.create(user=usuario, google_sub='sub-xyz', email=usuario.email)
