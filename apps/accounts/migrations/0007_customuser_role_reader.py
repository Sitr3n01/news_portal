"""Adiciona o cargo "Leitor" e o torna o default de novas contas.

Motivo: o default anterior era 'news_editor', cujo grupo ("Editor de Notícias")
carrega a permissão `wagtailadmin.access_admin`. Todo leitor que se cadastrava
em /accounts/register/ ficava gravado com esse cargo. Era inerte só porque
`sync_user_role_group` roda apenas ao salvar pelo admin — mas bastaria alguém
automatizar a sincronização para promover todos os leitores de uma vez.

A migração de dados é conservadora: só troca para 'reader' quem comprovadamente
não é da equipe (sem is_staff, sem is_superuser e sem nenhum grupo de cargo).
Ninguém perde acesso.
"""

from django.db import migrations, models

# Espelha admin_roles.MANAGED_ROLE_GROUP_NAMES. Copiado literalmente porque
# migrations não devem importar código de aplicação, que evolui com o tempo.
ADMIN_GROUP_NAMES = [
    'Administrador Komuniki',
    'Editor de Notícias',
    'Repórter',
    'Contratações (guardado)',
    'Administrador Geral',
    # Nomes legados (LEGACY_GROUP_RENAMES), caso ainda existam neste banco.
    'Administrador Escolar',
    'Contratações',
]


def move_plain_users_to_reader(apps, schema_editor):
    CustomUser = apps.get_model('accounts', 'CustomUser')
    CustomUser.objects.filter(
        is_staff=False,
        is_superuser=False,
    ).exclude(
        groups__name__in=ADMIN_GROUP_NAMES,
    ).update(role='reader')


def noop_reverse(apps, schema_editor):
    """Sem volta.

    Não dá para saber quais contas eram 'news_editor' por escolha e quais eram
    pelo default. Reverter em massa devolveria a todos um cargo com acesso ao
    CMS — exatamente o problema que esta migration fecha.
    """


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_alter_customuser_role'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(
                choices=[
                    ('reader', 'Leitor'),
                    ('super_admin', 'Super Administrador'),
                    ('school_admin', 'Administrador Komuniki'),
                    ('news_editor', 'Editor de Notícias'),
                    ('reporter', 'Repórter'),
                    ('hiring_manager', 'Contratações (guardado)'),
                ],
                default='reader',
                help_text='Define as permissões e acesso do usuário no sistema. '
                          '"Leitor" é apenas o portal público, sem acesso administrativo.',
                max_length=20,
                verbose_name='Cargo',
            ),
        ),
        migrations.RunPython(move_plain_users_to_reader, noop_reverse),
    ]
