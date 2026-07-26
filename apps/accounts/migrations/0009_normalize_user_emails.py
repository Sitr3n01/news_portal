"""Passa e-mails de usuário para minúsculas — só onde isso não colide.

A partir da 0009, `CustomUserCreationForm.clean_email` grava sempre em
minúsculas e busca com `__iexact`. Esta migration alinha o que já está no
banco com essa regra, para que a busca por identidade (login com Google,
recuperação de senha) encontre a conta certa em vez de achar que não existe.

O cuidado está no "só onde não colide": se hoje existirem DUAS contas cujos
e-mails diferem apenas por maiúsculas — exatamente o defeito que a 0009
fecha para o futuro —, baixar as duas para minúsculas violaria o
`unique=True` de `CustomUser.email` e derrubaria o deploy no meio da
migração. Nesse caso as duas ficam intocadas e o problema é reportado por
`manage.py find_duplicate_emails`, para uma pessoa decidir qual conta fica:
fundir contas apaga histórico (comentários, curtidas, artigos) e não é
decisão de migration.
"""

from django.db import migrations


def normalize_emails(apps, schema_editor):
    """Baixa para minúsculas apenas os e-mails cuja versão minúscula está livre."""
    from collections import Counter

    CustomUser = apps.get_model('accounts', 'CustomUser')

    # Comparação em Python, e não LOWER()/ILIKE no banco, porque o
    # comportamento de collation difere entre SQLite (dev/testes) e PostgreSQL
    # (produção) — e uma migration que se comporta diferente nos dois é pior do
    # que uma um pouco mais verbosa.
    todos = list(CustomUser.objects.exclude(email='').values_list('pk', 'email'))

    # Counter, e não uma varredura da lista para cada linha: com a busca
    # aninhada isto era O(n²) e uma base grande faria a migration travar o
    # deploy por minutos. Aqui é uma passada só.
    quantos_por_minusculo = Counter(email.lower() for _, email in todos)

    for pk, email in todos:
        minusculo = email.lower()
        if email == minusculo:
            continue
        # Mais de uma conta desemboca nesta versão minúscula: baixar violaria o
        # unique=True de CustomUser.email e derrubaria a migration no meio.
        # Nenhuma das envolvidas é tocada (ver docstring do módulo).
        if quantos_por_minusculo[minusculo] > 1:
            continue
        CustomUser.objects.filter(pk=pk).update(email=minusculo)


def noop_reverse(apps, schema_editor):
    """Sem volta, de propósito.

    A capitalização original não fica guardada em lugar nenhum, então não há
    o que restaurar — e inventar uma capitalização "provável" seria corromper
    dado, não reverter. Mesmo raciocínio da 0007 e da 0008: nem toda migração
    de dados tem inverso que valha a pena existir.
    """


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_customuser_email_verified_and_more'),
    ]

    operations = [
        migrations.RunPython(normalize_emails, noop_reverse),
    ]
