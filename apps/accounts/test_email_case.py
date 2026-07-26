"""Identidade por e-mail não pode depender de maiúsculas/minúsculas.

Antes da migration 0009, `CustomUserCreationForm.clean_email` comparava com
`filter(email=...)` — sensível a maiúsculas no SQLite e no PostgreSQL. Com
'Fulano@x.com' já cadastrado, 'FULANO@X.COM' passava e nascia uma SEGUNDA
conta para a mesma caixa postal: duas identidades para uma pessoa só, o que
quebra recuperação de senha e casamento de conta no login com Google.
"""

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.accounts.forms import CustomUserCreationForm
from apps.common import turnstile

SENHA = 'SenhaTeste#2026'


def mock_turnstile(monkeypatch, *, valid=True):
    monkeypatch.setattr(turnstile, 'verify_turnstile', lambda token, remote_ip='': valid and token == 'valid-token')


def dados_cadastro(username, email):
    return {
        'username': username,
        'email': email,
        'password1': SENHA,
        'password2': SENHA,
        turnstile.TURNSTILE_RESPONSE_FIELD: 'valid-token',
    }


@pytest.mark.django_db
def test_form_refuses_same_email_in_different_case(django_user_model):
    django_user_model.objects.create_user(
        username='original', email='fulano@example.com', password=SENHA,
    )

    form = CustomUserCreationForm(data=dados_cadastro('sosia', 'FULANO@EXAMPLE.COM'))

    assert form.is_valid() is False
    assert 'email' in form.errors


@pytest.mark.django_db
def test_form_normalizes_email_to_lowercase(django_user_model):
    form = CustomUserCreationForm(data=dados_cadastro('novato', '  Novato@Example.COM  '))

    assert form.is_valid(), form.errors
    assert form.cleaned_data['email'] == 'novato@example.com'


@pytest.mark.django_db
def test_registration_stores_lowercase_email(client, django_user_model, monkeypatch, current_site):
    mock_turnstile(monkeypatch)

    client.post(reverse('accounts:register'), dados_cadastro('maiusculo', 'Maiusculo@Example.COM'))

    user = django_user_model.objects.get(username='maiusculo')
    assert user.email == 'maiusculo@example.com'


@pytest.mark.django_db
def test_registration_refuses_duplicate_by_case_end_to_end(client, django_user_model, monkeypatch, current_site):
    """O caminho HTTP completo — não só o form isolado — recusa a duplicata."""
    mock_turnstile(monkeypatch)
    django_user_model.objects.create_user(
        username='primeiro', email='alvo@example.com', password=SENHA,
    )

    response = client.post(reverse('accounts:register'), dados_cadastro('segundo', 'ALVO@EXAMPLE.COM'))

    assert response.status_code == 200  # volta ao formulário, não redireciona
    assert django_user_model.objects.filter(username='segundo').exists() is False


@pytest.mark.django_db
def test_iexact_lookup_finds_account_regardless_of_case(django_user_model):
    """A busca que os fluxos usam (__iexact) acha onde a exata não acharia."""
    django_user_model.objects.create_user(
        username='misto', email='Misto.Caso@example.com', password=SENHA,
    )

    assert django_user_model.objects.filter(email='MISTO.CASO@EXAMPLE.COM').count() == 0
    assert django_user_model.objects.filter(email__iexact='MISTO.CASO@EXAMPLE.COM').count() == 1


@pytest.mark.django_db
def test_find_duplicate_emails_reports_collision(django_user_model, capsys):
    """O comando encontra o par colidente que a 0009 deixa de propósito para trás."""
    django_user_model.objects.create_user(username='a', email='colide@example.com', password=SENHA)
    django_user_model.objects.create_user(username='b', email='COLIDE@example.com', password=SENHA)

    with pytest.raises(SystemExit) as exc:
        call_command('find_duplicate_emails')

    # Exit code != 0 para dar para encadear em script de verificação.
    assert exc.value.code == 1
    saida = capsys.readouterr().out
    assert 'colide@example.com' in saida
    assert 'a' in saida and 'b' in saida


@pytest.mark.django_db
def test_find_duplicate_emails_is_quiet_when_clean(django_user_model, capsys):
    django_user_model.objects.create_user(username='unico', email='unico@example.com', password=SENHA)

    call_command('find_duplicate_emails')

    assert 'Nenhum e-mail duplicado' in capsys.readouterr().out
