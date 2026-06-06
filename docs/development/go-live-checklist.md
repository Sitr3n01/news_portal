# Checklist de Go-Live - news_portal

Passos para colocar o projeto em producao com seguranca. Itens marcados como
**[dominio]** dependem de DNS publico resolvendo corretamente.

## 1. Segredos e ambiente

- [ ] Copiar `.env.prod.example` para `.env.prod` (nunca commitar).
- [ ] Gerar `SECRET_KEY` forte: `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
- [ ] Definir senhas fortes do Postgres (`POSTGRES_PASSWORD` == `DB_PASSWORD`).
- [ ] **[dominio]** Preencher `ALLOWED_HOSTS` com:
      `komuniki.com.br,www.komuniki.com.br,kellyfarias.com.br,www.kellyfarias.com.br,2.25.178.16,localhost,127.0.0.1`.
- [ ] **[dominio]** Preencher `CSRF_TRUSTED_ORIGINS` com:
      `https://komuniki.com.br,https://www.komuniki.com.br,https://kellyfarias.com.br,https://www.kellyfarias.com.br`.
- [ ] Confirmar `DB_HOST=db` (nome do servico no compose, nao `localhost`).

## 2. E-mail (newsletter/contato)

- [ ] Configurar SMTP real em `.env.prod` (`EMAIL_BACKEND=...smtp...`, host, user, senha).
- [ ] Definir `DEFAULT_FROM_EMAIL` com o dominio real.
- [ ] No admin -> Configuracoes do Site, definir o remetente de newsletter por site.

## 3. Banco e dados iniciais

- [ ] `docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py migrate`
- [ ] **[dominio]** Corrigir o dominio do Site:
      `docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py set_site_domain`
      ou ajustar manualmente em admin -> Sites.
- [ ] Criar superusuario:
      `docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py createsuperuser`.

## 4. TLS / Nginx

- [ ] **[dominio]** Confirmar que estes quatro DNS resolvem para `2.25.178.16`:
      `komuniki.com.br`, `www.komuniki.com.br`, `kellyfarias.com.br`,
      `www.kellyfarias.com.br`.
- [ ] Emitir um unico certificado com nome principal `komuniki.com.br` e SANs para os quatro dominios:
      `docker compose --profile tools -p kellysys -f docker/docker-compose.prod.yml run --rm certbot certonly --webroot --webroot-path=/var/www/certbot --email SEU_EMAIL --agree-tos --no-eff-email -d komuniki.com.br -d www.komuniki.com.br -d kellyfarias.com.br -d www.kellyfarias.com.br`.
- [ ] Aplicar o `docker/nginx/nginx.conf` final, que mantem ACME em HTTP,
      redireciona HTTP para HTTPS e serve HTTPS com
      `/etc/letsencrypt/live/komuniki.com.br/`.
- [ ] Confirmar `SECURE_SSL_REDIRECT=True` no `.env.prod`.

## 5. Deploy GitHub -> VPS

- [ ] Instalar `/usr/local/sbin/kellysys-deploy` e `/usr/local/sbin/kellysys-deploy-approved`.
- [ ] Ativar `kellysys-approved-deploy.timer` para a VPS buscar a tag `production-approved`.
- [ ] Rodar o workflow `Deploy Production` manualmente em `master`.

## 6. Cloudflare anti-bot

- [ ] Camada Turnstile: criar widget no Cloudflare e preencher
      `CLOUDFLARE_TURNSTILE_SITE_KEY`/`SECRET_KEY` no `.env.prod`; recriar o `web`.
- [ ] **[dominio]** Camada de borda: ativar proxy (nuvem laranja), SSL **Full (strict)** e **Bot Fight Mode**.
- [ ] Travar o firewall as faixas Cloudflare: `sudo scripts/deploy/cloudflare-firewall.sh` (preserve o SSH).
- [ ] Validar: forms enviam, IP real nos logs, origem fechada a nao-Cloudflare.
- [ ] Runbook completo: `docs/development/cloudflare-bots.md`.

## 7. Verificacao final

- [ ] `docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py check --deploy`.
- [ ] `docker compose -p kellysys -f docker/docker-compose.prod.yml up -d`.
- [ ] Healthcheck do container `web` fica `healthy`.
- [ ] `https://komuniki.com.br/` e `https://www.komuniki.com.br/` retornam 200.
- [ ] `https://kellyfarias.com.br/` e `https://www.kellyfarias.com.br/` redirecionam para `/news/`.
- [ ] `/admin/` mostra "Bem vindo!" e nao mostra `kelly_sys`.
