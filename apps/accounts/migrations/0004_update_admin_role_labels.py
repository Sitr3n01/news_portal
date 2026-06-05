from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_customuser_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(
                choices=[
                    ('super_admin', 'Super Administrador'),
                    ('school_admin', 'Administrador Komuniki'),
                    ('news_editor', 'Editor de Notícias'),
                    ('hiring_manager', 'Contratações (guardado)'),
                ],
                default='news_editor',
                help_text='Define as permissões e acesso do usuário no sistema.',
                max_length=20,
                verbose_name='Cargo',
            ),
        ),
    ]
