# Guia de Deploy — news_portal

Guia operacional para produção. Antes de executar, passe pelo [checklist de go-live](go-live-checklist.md).

## Premissas

- VPS Linux com Docker Engine e Docker Compose.
- Repositório em `/opt/kelly_sys`.
- Docker Compose project `kellysys`.
- Branch de produção: `master`.
- Deploy aprovado por tag `production-approved`.
- Domínios públicos:
  - `komuniki.com.br`
  - `www.komuniki.com.br`
  - `kellyfarias.com.br`
  - `www.kellyfarias.com.br`

---

## 1. Clonar ou Atualizar o Repositório

```bash
git clone https://github.com/Sitr3n01/news_portal.git /opt/kelly_sys
cd /opt/kelly_sys
git checkout master
git pull --ff-only origin master
```

Na VPS de produção, o deploy automatizado exige working tree limpo. Não edite arquivos rastreados diretamente no servidor.

---

## 2. Configurar `.env.prod`

```bash
cd /opt/kelly_sys
cp .env.prod.example .env.prod
nano .env.prod
chmod 600 .env.prod
```

Valores críticos:

```env
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
SECRET_KEY=gere_uma_chave_forte_e_unica
ALLOWED_HOSTS=komuniki.com.br,www.komuniki.com.br,kellyfarias.com.br,www.kellyfarias.com.br
CSRF_TRUSTED_ORIGINS=https://komuniki.com.br,https://www.komuniki.com.br,https://kellyfarias.com.br,https://www.kellyfarias.com.br
SECURE_SSL_REDIRECT=True

POSTGRES_DB=news_portal
POSTGRES_USER=news_portal_user
POSTGRES_PASSWORD=senha_forte
DB_NAME=news_portal
DB_USER=news_portal_user
DB_PASSWORD=senha_forte
DB_HOST=db
DB_PORT=5432
```

SMTP:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.seuprovedor.com
EMAIL_PORT=587
EMAIL_HOST_USER=usuario@seudominio.com
EMAIL_HOST_PASSWORD=senha_smtp
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Blog da Kelly <noticias@kellyfarias.com.br>
```

Turnstile é obrigatório em produção para formulários públicos:

```env
CLOUDFLARE_TURNSTILE_SITE_KEY=...
CLOUDFLARE_TURNSTILE_SECRET_KEY=...
```

Segredos como `SECRET_KEY`, banco, SMTP e Turnstile nunca são gravados no admin nem commitados.

---

## 3. Bootstrap Inicial

Suba os serviços:

```bash
docker compose -p kellysys -f docker/docker-compose.prod.yml build
docker compose -p kellysys -f docker/docker-compose.prod.yml up -d db web
```

Rode a configuração inicial:

```bash
docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py migrate --noinput
docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py collectstatic --clear --noinput
docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py createsuperuser
docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py set_site_domain
```

Configure no admin:

- **Sistema → Sites**: domínio público correto.
- **Sistema → Configurações dos sites**: identidade, contato, remetente de newsletter, analytics e links sociais.

---

## 4. TLS com Let's Encrypt

O `nginx.conf` versionado espera certificados em `/etc/letsencrypt/live/komuniki.com.br/`. Em VPS nova, emita o primeiro certificado antes de subir o Nginx final.

Opção mais simples para primeiro certificado, usando standalone na porta 80:

```bash
docker run --rm -p 80:80 \
  -v kellysys_certbot_conf:/etc/letsencrypt \
  certbot/certbot:latest certonly --standalone \
  --email seu-email@dominio.com --agree-tos --no-eff-email \
  -d komuniki.com.br -d www.komuniki.com.br \
  -d kellyfarias.com.br -d www.kellyfarias.com.br
```

Depois que o Nginx estiver no ar, renovações podem usar webroot pelo compose:

```bash
docker compose -p kellysys -f docker/docker-compose.prod.yml \
  --profile tools run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  --email seu-email@dominio.com --agree-tos --no-eff-email \
  -d komuniki.com.br -d www.komuniki.com.br \
  -d kellyfarias.com.br -d www.kellyfarias.com.br
```

Depois valide e suba o Nginx:

```bash
docker compose -p kellysys -f docker/docker-compose.prod.yml up -d nginx
docker compose -p kellysys -f docker/docker-compose.prod.yml exec -T nginx nginx -t
```

---

## 5. Instalar Deploy Aprovado na VPS

Instale os scripts root-owned:

```bash
cd /opt/kelly_sys
sudo install -o root -g root -m 0755 scripts/deploy/kellysys-deploy /usr/local/sbin/kellysys-deploy
sudo install -o root -g root -m 0755 scripts/deploy/kellysys-deploy-approved /usr/local/sbin/kellysys-deploy-approved
sudo install -o root -g root -m 0755 scripts/deploy/kellysys-maintenance /usr/local/sbin/kellysys-maintenance
```

Configure os timers conforme [secure-deploy.md](secure-deploy.md):

- `kellysys-approved-deploy.timer`: procura a tag `production-approved` e roda deploy.
- `kellysys-maintenance.timer`: limpa sessões, estatísticas, imagens/containers antigos e journal.

Teste manual:

```bash
sudo /usr/local/sbin/kellysys-deploy
```

---

## 6. Fluxo Normal de Deploy

1. Abra/mergeie mudança em `master`.
2. Rode o workflow manual **Deploy Production** em `master`.
3. Aguarde lint, `collectstatic` e testes.
4. Aprove o environment `production`.
5. O workflow move a tag `production-approved`.
6. A VPS detecta a tag e executa `/usr/local/sbin/kellysys-deploy-approved`.

O deploy local faz:

- valida working tree limpo;
- busca commit aprovado;
- cria backup PostgreSQL gzipado em `/opt/kelly_sys/backups/`;
- builda imagem web;
- roda migrations;
- roda `collectstatic --clear`;
- recria `web`;
- valida e recria `nginx`;
- executa healthchecks HTTP/HTTPS.

---

## 7. Rotinas Operacionais

Newsletter pendente:

```cron
*/5 * * * * docker compose -p kellysys -f /opt/kelly_sys/docker/docker-compose.prod.yml exec -T web python manage.py send_pending_newsletters --batch-size 100
```

Manutenção diária preferencial:

```bash
sudo systemctl status kellysys-maintenance.timer --no-pager
sudo journalctl -u kellysys-maintenance.service -n 80 --no-pager
```

Não execute `docker volume prune` em produção.

---

## 8. Smoke Tests

```bash
curl -I https://komuniki.com.br/healthz/
curl -I https://www.komuniki.com.br/healthz/
curl -I https://komuniki.com.br/
curl -I https://kellyfarias.com.br/news/
curl -I https://kellyfarias.com.br/
```

Esperado:

- healthchecks retornam 200;
- Komuniki carrega na raiz;
- Blog carrega em `/news/`;
- raiz de `kellyfarias.com.br` redireciona para `/news/`;
- `/admin/` abre por HTTPS.

---

## 9. Referência

| Serviço | Função |
|---------|--------|
| `web` | Django/Gunicorn, 3 workers, 2 threads |
| `db` | PostgreSQL 16 |
| `nginx` | TLS, proxy reverso, estáticos, mídia, `/protected/` |
| `certbot` | Emissão/renovação de certificado |

Documentos relacionados:

- [go-live-checklist.md](go-live-checklist.md)
- [secure-deploy.md](secure-deploy.md)
- [cloudflare-bots.md](cloudflare-bots.md)
- [vps-optimization.md](vps-optimization.md)
