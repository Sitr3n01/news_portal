import os

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        'Define o domínio (e opcionalmente o nome) do Site atual no go-live. '
        'Substitui o seed inicial example.com, que quebra links de e-mail. '
        'Lê --domain/--name ou as variáveis de ambiente SITE_DOMAIN/SITE_NAME.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--domain', default=os.environ.get('SITE_DOMAIN'))
        parser.add_argument('--name', default=os.environ.get('SITE_NAME'))
        parser.add_argument('--site-id', type=int, default=settings.SITE_ID)

    def handle(self, *args, **options):
        domain = options['domain']
        if not domain:
            raise CommandError('Informe --domain ou defina SITE_DOMAIN no ambiente.')

        site_id = options['site_id']
        try:
            site = Site.objects.get(pk=site_id)
        except Site.DoesNotExist as exc:
            raise CommandError(f'Site id={site_id} não encontrado. Rode as migrações primeiro.') from exc

        changes = []
        if site.domain != domain:
            changes.append(f"domínio: '{site.domain}' -> '{domain}'")
            site.domain = domain

        name = options['name']
        if name and site.name != name:
            changes.append(f"nome: '{site.name}' -> '{name}'")
            site.name = name

        if not changes:
            self.stdout.write(self.style.SUCCESS(f'Site id={site_id} já está com domínio "{domain}". Nada a fazer.'))
            return

        site.save()
        Site.objects.clear_cache()
        for change in changes:
            self.stdout.write(self.style.SUCCESS(change))
        self.stdout.write(self.style.SUCCESS('Site atualizado com sucesso.'))
