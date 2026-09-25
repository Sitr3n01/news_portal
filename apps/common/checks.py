"""System check de deploy: segredo de exemplo não sobe para produção.

`manage.py check --deploy --fail-level ERROR` roda antes de migrar em
scripts/deploy/kellysys-deploy. Até aqui nada ali recusava os valores de
exemplo publicados no repositório (.env.prod.example, .env.example, compose de
desenvolvimento, CI): um `.env.prod` copiado sem trocar a SECRET_KEY subia com
uma chave que qualquer pessoa lê no GitHub — e com ela dá para forjar tokens
assinados (descadastro da newsletter, cookies de mensagens) e o pepper HMAC
dos códigos de verificação deixa de ser segredo.

Só valores CONHECIDOS viram Error. Chave curta porém aleatória continua no
aviso nativo do Django (security.W009): barrar o deploy por tamanho travaria
uma produção com chave real de menos de 50 caracteres sem ganho proporcional.
"""

from django.conf import settings
from django.core.checks import Error, Tags, register

# Trechos dos placeholders de .env.prod.example/.env.example e o prefixo das
# chaves geradas pelo startproject.
PLACEHOLDER_MARKERS = (
    '__TROQUE',
    '__SENHA',
    '__SECRET_KEY_DO_PAINEL',
    'your-secret-key-here',
    'django-insecure',
    'change-me',
)
# Valores literais publicados (compose de dev, CI, Dockerfile, histórico).
PUBLIC_VALUES = {
    'news_portal_pass',
    'kelly_pass',
    'build_only',
    'build-only-not-a-secret',
    'ci-test-secret-key-not-for-production',
}
SECRET_SETTINGS = (
    'EMAIL_HOST_PASSWORD',
    'GOOGLE_OAUTH_CLIENT_SECRET',
    'TIKTOK_CLIENT_SECRET',
    'CLOUDFLARE_TURNSTILE_SECRET_KEY',
)


def is_public_value(value):
    value = str(value or '')
    return value in PUBLIC_VALUES or any(marker in value for marker in PLACEHOLDER_MARKERS)


@register(Tags.security, deploy=True)
def check_secret_placeholders(app_configs, **kwargs):
    errors = []
    if is_public_value(settings.SECRET_KEY):
        errors.append(Error(
            'SECRET_KEY é um valor de exemplo publicado no repositório.',
            hint='Gere uma chave nova no .env.prod: python -c "import secrets; print(secrets.token_urlsafe(64))"',
            id='common.E010',
        ))
    if is_public_value(settings.DATABASES.get('default', {}).get('PASSWORD', '')):
        errors.append(Error(
            'DB_PASSWORD é um valor de exemplo publicado no repositório.',
            hint='Troque a senha no Postgres e no .env.prod (POSTGRES_PASSWORD e DB_PASSWORD).',
            id='common.E011',
        ))
    for name in SECRET_SETTINGS:
        if is_public_value(getattr(settings, name, '')):
            errors.append(Error(
                f'{name} é um valor de exemplo publicado no repositório.',
                hint='Preencha o valor real no .env.prod ou deixe a variável vazia se o recurso não for usado.',
                id='common.E012',
            ))
    return errors
