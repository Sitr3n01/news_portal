from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0004_siteextension_newsletter_from_email_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='siteextension',
            name='newsletter_from_name',
            field=models.CharField(
                blank=True,
                help_text='Nome exibido como remetente. Ex: Blog da Kelly',
                max_length=100,
                verbose_name='Nome remetente da Newsletter',
            ),
        ),
    ]
