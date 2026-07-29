"""Diagnóstico do login com Google, para rodar de dentro do container.

Existe porque a suíte de testes simula o Google (monkeypatch em exchange_code
e verify_id_token): ela prova a nossa lógica, mas não prova que ESTE servidor
alcança o Google, nem que a credencial configurada é a que o console conhece.
Este comando cobre justamente a parte que o teste não cobre — conectividade de
saída e coerência da configuração — sem precisar de um navegador nem de um
usuário de verdade.

O que ele NÃO faz: completar um login. Isso continua exigindo uma pessoa
clicando, porque depende do consentimento na tela do Google.
"""

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse

from apps.accounts import oauth_google

DISCOVERY_URL = 'https://accounts.google.com/.well-known/openid-configuration'


class Command(BaseCommand):
    help = 'Verifica a configuração e a conectividade do login com Google.'

    def _ok(self, texto):
        self.stdout.write(self.style.SUCCESS(f'  [ok]    {texto}'))

    def _erro(self, texto):
        self.stdout.write(self.style.ERROR(f'  [ERRO]  {texto}'))

    def _aviso(self, texto):
        self.stdout.write(self.style.WARNING(f'  [aviso] {texto}'))

    def handle(self, *args, **options):
        falhas = 0

        self.stdout.write('── Configuração ──')
        if not settings.GOOGLE_OAUTH_ENABLED:
            raise CommandError(
                'GOOGLE_OAUTH_ENABLED é False: falta GOOGLE_OAUTH_CLIENT_ID e/ou '
                'GOOGLE_OAUTH_CLIENT_SECRET no .env. Sem eles o botão não aparece '
                'e as rotas devolvem 404 — o login por senha segue normal.'
            )
        self._ok('GOOGLE_OAUTH_ENABLED = True')

        # Nunca imprimir o client_id inteiro nem o secret. O sufixo já basta
        # para conferir contra o console do Google.
        client_id = settings.GOOGLE_OAUTH_CLIENT_ID
        self._ok(f'CLIENT_ID termina em ...{client_id[-24:]}')
        self._ok(f'CLIENT_SECRET: {"definido" if settings.GOOGLE_OAUTH_CLIENT_SECRET else "VAZIO"}')

        redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
        caminho_esperado = reverse('accounts:google_callback')
        self.stdout.write('')
        self.stdout.write('── Redirect URI ──')
        if not redirect_uri:
            self._erro('GOOGLE_OAUTH_REDIRECT_URI está vazio.')
            falhas += 1
        else:
            self.stdout.write(f'  configurado: {redirect_uri}')
            self.stdout.write('  Registre EXATAMENTE isto no Google Cloud Console.')
            if not redirect_uri.endswith(caminho_esperado):
                self._erro(
                    f'não termina em {caminho_esperado} — o Google exige '
                    'correspondência literal e vai recusar com redirect_uri_mismatch.'
                )
                falhas += 1
            else:
                self._ok(f'caminho bate com a rota accounts:google_callback ({caminho_esperado})')

            if redirect_uri.startswith('http://') and 'localhost' not in redirect_uri:
                self._erro('http:// só é aceito pelo Google em localhost. Use https:// em produção.')
                falhas += 1
            elif redirect_uri.startswith('https://'):
                self._ok('esquema https')

            if '://www.' in redirect_uri:
                self._aviso(
                    'o redirect aponta para o host com "www.". O nginx canoniza www -> sem-www, '
                    'então a volta do Google chegaria num host diferente do que iniciou o fluxo '
                    'e a sessão (com o state) não estaria lá. Prefira o domínio sem www.'
                )

        self.stdout.write('')
        self.stdout.write('── Conectividade de saída ──')
        try:
            resposta = httpx.get(DISCOVERY_URL, timeout=oauth_google.HTTP_TIMEOUT)
            resposta.raise_for_status()
            documento = resposta.json()
        except Exception as exc:
            self._erro(
                f'não alcançou {DISCOVERY_URL} ({type(exc).__name__}). '
                'Verifique saída HTTPS e DNS do container.'
            )
            raise CommandError('Sem conectividade com o Google — o login não funcionaria.') from exc

        self._ok('alcançou o documento de descoberta do Google')

        # Confere os endpoints que estão fixos em oauth_google.py contra o que
        # o próprio Google publica: se um dia mudarem, isto acusa antes do
        # primeiro usuário descobrir.
        for nome, nosso, deles in (
            ('token endpoint', oauth_google.TOKEN_ENDPOINT, documento.get('token_endpoint')),
            ('authorization endpoint', oauth_google.AUTHORIZATION_ENDPOINT, documento.get('authorization_endpoint')),
        ):
            if nosso == deles:
                self._ok(f'{nome} confere: {nosso}')
            else:
                self._erro(f'{nome} divergente — nosso: {nosso} | Google: {deles}')
                falhas += 1

        # O JWKS é o que google-auth busca para validar a assinatura do ID
        # token. Se este passo falhar em produção, todo login morreria em
        # "Não foi possível validar sua conta Google".
        jwks_uri = documento.get('jwks_uri')
        try:
            chaves = httpx.get(jwks_uri, timeout=oauth_google.HTTP_TIMEOUT).json()
            quantidade = len(chaves.get('keys', []))
        except Exception as exc:
            self._erro(f'não alcançou o JWKS ({type(exc).__name__}) — a validação do ID token falharia.')
            raise CommandError('Sem acesso ao JWKS do Google.') from exc

        if quantidade:
            self._ok(f'JWKS acessível ({quantidade} chave(s) públicas)')
        else:
            self._erro('JWKS veio sem chaves.')
            falhas += 1

        self.stdout.write('')
        if falhas:
            raise CommandError(f'{falhas} problema(s) encontrado(s) — corrija antes de liberar o login com Google.')

        self.stdout.write(self.style.SUCCESS(
            'Configuração e conectividade OK. Falta o teste que só uma pessoa faz: '
            'abrir /accounts/login/, clicar em "Entrar com Google" e conferir em /admin/ '
            'que a conta nasceu como Leitor, sem grupo e sem acesso administrativo.'
        ))
