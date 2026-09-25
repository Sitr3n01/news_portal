Título: [Segurança] Placeholders de segredos passam no deploy (+ defaults de dev e IP de origem)
Labels sugeridas: security, severidade: média

## Descrição
`config/settings/base.py:12` exige `SECRET_KEY`, mas nenhum check rejeita os valores de exemplo
publicados no repositório (`.env.prod.example:11, 25, 28, 39`; `.env.example:2, 10`). O Django só
emite o aviso `security.W009` para chave fraca, e o deploy roda `check --deploy --fail-level ERROR`
(`scripts/deploy/kellysys-deploy:137`), que deixa avisos passarem.

Itens agrupados, do mesmo tema:
- (baixa) `docker/docker-compose.yml:39-41, 52-53` publica Postgres (senha `news_portal_pass`) e
  Mailpit em `0.0.0.0`.
- (informativa) IP de origem da VPS em `.env.prod.example:14` e
  `docs/technical/cloudflare-bots.md:56, 86, 103`.
- (informativa) Histórico: `base.py` teve `default='django-insecure-change-me-in-production'` entre
  os commits `a3b8544` e `5033972` (23 a 25/02/2026). A varredura dos 182 commits não achou nenhum
  segredo real.

## Por que é explorável
Com o `.env.prod` copiado do exemplo, a `SECRET_KEY` é pública: dá para forjar tokens de descadastro
da newsletter (`apps/news/newsletter.py:43-61`) e cookies de mensagens, e o pepper HMAC dos códigos
de verificação deixa de ser segredo. O banco de dev e a caixa do Mailpit (com códigos de
verificação) ficam acessíveis na rede local.

Confirmado: `manage.py check --deploy --fail-level ERROR` com
`SECRET_KEY=__TROQUE_POR_UMA_CHAVE_FORTE__` terminou com exit 0.

## Evidência
```
.env.prod.example:11           SECRET_KEY=__TROQUE_POR_UMA_CHAVE_FORTE__
scripts/deploy/kellysys-deploy:137   manage.py check --deploy --fail-level ERROR
docker/docker-compose.yml:41   - "5432:5432"
```

## Impacto
Segurança da produção dependente só da disciplina do operador; exposição de ambiente de dev;
facilidade para contornar o Cloudflare se o firewall da origem não estiver aplicado.

## Sugestão de correção
```python
# apps/common/checks.py (registrar em CommonConfig.ready)
from django.conf import settings
from django.core.checks import Error, Tags, register

PLACEHOLDERS = ('__TROQUE', '__SENHA', 'your-secret-key-here', 'django-insecure', 'change-me')

@register(Tags.security, deploy=True)
def check_secret_placeholders(app_configs, **kwargs):
    errors = []
    key = settings.SECRET_KEY
    if len(key) < 50 or len(set(key)) < 5 or any(p in key for p in PLACEHOLDERS):
        errors.append(Error('SECRET_KEY fraca ou de exemplo.', id='common.E010'))
    for name, value in (('DB_PASSWORD', settings.DATABASES['default'].get('PASSWORD', '')),
                        ('EMAIL_HOST_PASSWORD', settings.EMAIL_HOST_PASSWORD)):
        if any(p in (value or '') for p in PLACEHOLDERS):
            errors.append(Error(f'{name} ainda com valor de exemplo.', id='common.E011'))
    return errors
```
- Compose de dev: `"127.0.0.1:5432:5432"`, `"127.0.0.1:8025:8025"`, `"127.0.0.1:1025:1025"`.
- Trocar o IP por `<IP_DA_VPS>` no exemplo e nos docs; confirmar `curl -I --max-time 5 http://<IP>/`
  → timeout.
- Secret scanning no CI (ex.: gitleaks); rotacionar a `SECRET_KEY` se algum ambiente subiu entre 23
  e 25/02/2026.

## Critérios de aceite
- [ ] `manage.py check --deploy --fail-level ERROR` falha com a `SECRET_KEY` ou senhas de exemplo
      (teste do check).
- [ ] O compose de dev publica portas só em `127.0.0.1`.
- [ ] O IP de origem não aparece mais no repositório e o firewall da origem foi confirmado.
- [ ] Job de secret scanning no CI; `SECRET_KEY` rotacionada, se aplicável.
