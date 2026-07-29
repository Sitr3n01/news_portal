"""Confirmação de e-mail (Fase 1): campos novos no CustomUser + duas tabelas de apoio.

Aditiva, nada destrutivo: dois AddField (BooleanField com default e
DateTimeField nulo) e dois CreateModel (VerificationCode, GoogleIdentity).
Nenhuma coluna existente muda de tipo ou é removida.

O RunPython no fim resolve um problema que esta própria migration cria: sem
ele, toda conta HOJE já cadastrada nasceria com email_verified=False e
passaria a ver a tela de "confirme seu e-mail" assim que a Fase 2 (views)
entrar no ar — inclusive quem usa o sistema há anos e nunca teve motivo para
duvidar do próprio e-mail. Ver noop_reverse() sobre por que isto não tem
volta sensata.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def mark_existing_users_as_verified(apps, schema_editor):
    """Todo usuário já existente com e-mail preenchido passa a contar como confirmado.

    `.exclude(email='')`: quem não tem e-mail cadastrado não tem para onde um
    código de confirmação seria enviado, então marcar como "confirmado" seria
    inventar um dado, não migrar um. Essas contas continuam com
    email_verified=False (o default do campo) até preencherem um endereço.
    """
    CustomUser = apps.get_model('accounts', 'CustomUser')
    CustomUser.objects.exclude(email='').update(email_verified=True, email_verified_at=timezone.now())


def noop_reverse(apps, schema_editor):
    """Sem volta, de propósito.

    Reverter marcando todo mundo como "não confirmado" de novo não desfaz um
    efeito colateral desta migration — CRIA um: o próximo rollback faria uma
    base inteira de contas antigas, que nunca duvidaram do próprio e-mail,
    ver a tela de confirmação (e disparar um código) do nada. Isso é uma
    regressão de UX (e de caixa de entrada), não uma reversão de dado. Mesmo
    raciocínio da 0007_customuser_role_reader.noop_reverse: nem toda migração
    de dados tem um inverso que valha a pena restaurar.
    """


class Migration(migrations.Migration):

    dependencies = [
        # settings.AUTH_USER_MODEL resolve para 'accounts.CustomUser' — o MESMO
        # app desta migration. Por isso makemigrations NÃO acrescentou
        # migrations.swappable_dependency(settings.AUTH_USER_MODEL) sozinho: a
        # dependência intra-app na 0007 (que já deixa a tabela customuser no
        # estado atual) já é suficiente para ordenar a criação de
        # VerificationCode/GoogleIdentity depois dela. swappable_dependency
        # existe para o FK apontar para um AUTH_USER_MODEL definido em OUTRO
        # app; aqui seria uma dependência redundante, por isso omitida.
        ('accounts', '0007_customuser_role_reader'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='email_verified',
            field=models.BooleanField(default=False, help_text='Marcado automaticamente quando o usuário confirma o endereço com o código enviado por e-mail.', verbose_name='E-mail confirmado'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='email_verified_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Confirmado em'),
        ),
        migrations.CreateModel(
            name='GoogleIdentity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('google_sub', models.CharField(db_index=True, max_length=255, unique=True)),
                ('email', models.EmailField(max_length=254)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_login_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='google_identity', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Identidade Google',
                'verbose_name_plural': 'Identidades Google',
            },
        ),
        migrations.CreateModel(
            name='VerificationCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254)),
                ('purpose', models.CharField(choices=[('email_verification', 'Confirmação de e-mail'), ('password_reset', 'Recuperação de senha')], max_length=32)),
                ('code_hash', models.CharField(max_length=64)),
                ('expires_at', models.DateTimeField()),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='verification_codes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Código de verificação',
                'verbose_name_plural': 'Códigos de verificação',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['user', 'purpose', '-created_at'], name='accounts_ve_user_id_f57e3f_idx')],
            },
        ),
        migrations.RunPython(mark_existing_users_as_verified, noop_reverse),
    ]
