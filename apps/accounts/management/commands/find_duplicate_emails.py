"""Relata contas cujo e-mail só difere por maiúsculas/minúsculas.

Existe por causa do defeito que a migration 0009 fecha: até ela, o cadastro
comparava e-mail com `filter(email=...)` (sensível a maiúsculas nos dois
bancos), então 'Fulano@x.com' e 'FULANO@X.COM' viravam duas contas para a
mesma caixa postal. A 0009 normaliza o que dá para normalizar sem colidir e
deixa os pares colidentes de lado — este comando é como se encontra o que
ficou de lado.

SÓ RELATÓRIO: nunca funde nem apaga conta. Fundir significa escolher qual
histórico sobrevive (comentários, curtidas, favoritos, artigos assinados) e
qual `role`/`is_staff` prevalece — decisão de pessoa, não de script.
"""

from collections import defaultdict

from django.core.management.base import BaseCommand

from apps.accounts.models import CustomUser


class Command(BaseCommand):
    help = 'Lista contas cujo e-mail difere apenas por maiúsculas/minúsculas.'

    def handle(self, *args, **options):
        grupos = defaultdict(list)
        for user in CustomUser.objects.exclude(email='').order_by('date_joined'):
            grupos[user.email.lower()].append(user)

        duplicados = {chave: users for chave, users in grupos.items() if len(users) > 1}

        if not duplicados:
            self.stdout.write(self.style.SUCCESS('Nenhum e-mail duplicado por diferença de maiúsculas.'))
            return

        self.stdout.write(self.style.WARNING(
            f'{len(duplicados)} endereço(s) com mais de uma conta:'
        ))
        for chave, users in sorted(duplicados.items()):
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(f'  {chave}'))
            for user in users:
                ultimo = user.last_login.strftime('%d/%m/%Y') if user.last_login else 'nunca'
                self.stdout.write(
                    f'    - {user.username} | {user.email} | role={user.role} '
                    f'| staff={user.is_staff} | criada={user.date_joined:%d/%m/%Y} | último acesso={ultimo}'
                )

        self.stdout.write('')
        self.stdout.write(
            'Decida manualmente qual conta fica. Este comando nunca funde nem apaga nada.'
        )
        # Exit code != 0 para dar para encadear em script de verificação.
        raise SystemExit(1)
