# Checklist de Go-Live — news_portal

Passos para colocar o projeto em produção com segurança. Itens marcados como
**[domínio]** dependem de ter o domínio real definido.

## 1. Segredos e ambiente

- [ ] Copiar `.env.prod.example` → `.env.prod` (nunca commitar).
- [ ] Gerar `SECRET_KEY` forte: `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
- [ ] Definir senhas fortes do Postgres (`POSTGRES_PASSWORD` == `DB_PASSWORD`).
- [ ] **[domínio]** Preencher `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` (com `https://`).
- [ ] Confirmar `DB_HOST=db` (nome do serviço no compose, não `localhost`).

## 2. E-mail (newsletter/contato)

- [ ] Configurar SMTP real em `.env.prod` (`EMAIL_BACKEND=...smtp...`, host, user, senha).
- [ ] Definir `DEFAULT_FROM_EMAIL` com o domínio real.
- [ ] No admin → Configurações do Site, definir o remetente de newsletter por site.

## 3. Banco e dados iniciais

- [ ] `docker compose -f docker/docker-compose.prod.yml run --rm web python manage.py migrate`
- [ ] **[domínio]** Corrigir o domínio do Site (seed inicial usa `example.com`, o que
      quebra links de e-mail):
      `... run --rm web python manage.py set_site_domain` (lê `SITE_DOMAIN`/`SITE_NAME`)
      — ou ajustar manualmente em **admin → Sites**.
- [ ] Criar superusuário: `... run --rm web python manage.py createsuperuser`.

## 4. TLS / Nginx (docker/nginx/nginx.conf)

- [ ] **[domínio]** Trocar `server_name _;` pelo domínio real.
- [ ] **[domínio]** Emitir o certificado via certbot (volumes `certbot_conf`/`certbot_www`
      já montados no `docker-compose.prod.yml`).
- [ ] No server `:80`, ativar o redirect `301` para HTTPS (mantendo o
      `location /.well-known/acme-challenge/`).
- [ ] Descomentar o server `:443` (bloco "GO-LIVE TLS" já preparado no arquivo) e
      preencher `SEU_DOMINIO` nos caminhos do certificado.
- [ ] Confirmar `SECURE_SSL_REDIRECT=True` no `.env.prod`.

## 5. Observabilidade (opcional, recomendado)

- [ ] Definir `SENTRY_DSN` no `.env.prod` para ativar rastreamento de erros.
- [ ] Ajustar `LOG_LEVEL`/`DJANGO_LOG_LEVEL` se necessário (default `INFO`).

## 6. Verificação final

- [ ] `... run --rm web python manage.py check --deploy` → **0 avisos**.
- [ ] Subir o stack: `docker compose -f docker/docker-compose.prod.yml up -d`.
- [ ] Healthcheck do container `web` fica `healthy` (probe em `/healthz/`).
- [ ] Abrir as 3 famílias (escola `/`, notícias `/news/`, página escolar) e conferir,
      no DevTools → Network, que **nenhuma** requisição sai para CDNs externos
      (`cdn.tailwindcss.com`, `unpkg.com`, `jsdelivr.net`) e **0 erros** no console.
- [ ] Enviar um e-mail de teste (newsletter/contato) e confirmar links com o domínio real.
