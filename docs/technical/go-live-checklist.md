# Checklist de Go-live — news_portal

Use este checklist antes de publicar uma mudança em produção ou reconfigurar a VPS. O caminho canônico é `/opt/kelly_sys`, o Compose project é `kellysys`, e o deploy aprovado passa pela tag `production-approved`.

## 1. Estado do Repositório

- [ ] Branch local da VPS está sem alterações rastreadas ou staged.
- [ ] A mudança foi revisada em PR ou aprovada manualmente antes do workflow `Deploy Production`.
- [ ] `ruff check .`, `pytest` e `collectstatic` passam no CI.
- [ ] Documentação relevante foi atualizada junto com a mudança.

## 2. Segredos e Ambiente

- [ ] `.env.prod` existe em `/opt/kelly_sys` e não está versionado.
- [ ] `SECRET_KEY` é forte e exclusivo do ambiente.
- [ ] `DEBUG=False`.
- [ ] `ALLOWED_HOSTS` inclui `komuniki.com.br`, `www.komuniki.com.br`, `kellyfarias.com.br`, `www.kellyfarias.com.br`.
- [ ] `CSRF_TRUSTED_ORIGINS` usa `https://` para os quatro domínios públicos.
- [ ] `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD` coincidem com `DB_NAME`, `DB_USER` e `DB_PASSWORD`.
- [ ] `DB_HOST=db`.
- [ ] `SECURE_SSL_REDIRECT=True` depois que TLS estiver ativo.

## 3. DNS, TLS e Nginx

- [ ] Os quatro domínios resolvem para a VPS ou para o proxy Cloudflare esperado.
- [ ] Certificado Let's Encrypt cobre `komuniki.com.br`, `www.komuniki.com.br`, `kellyfarias.com.br`, `www.kellyfarias.com.br`.
- [ ] `docker compose -p kellysys -f docker/docker-compose.prod.yml exec -T nginx nginx -t` passa.
- [ ] HTTP redireciona para HTTPS, exceto challenge ACME.
- [ ] `kellyfarias.com.br/` redireciona para `/news/`.

## 4. Banco e Dados Iniciais

- [ ] `python manage.py migrate --noinput` roda sem pendências.
- [ ] `python manage.py collectstatic --clear --noinput` roda sem erro.
- [ ] Existe superusuário ativo.
- [ ] O registro `Site` principal tem domínio correto, via admin ou `python manage.py set_site_domain`.
- [ ] `SiteExtension` contém contatos públicos e remetente da newsletter.

## 5. E-mail e Newsletter

- [ ] SMTP real configurado em `.env.prod`.
- [ ] `DEFAULT_FROM_EMAIL` usa domínio controlado.
- [ ] Remetente público da newsletter está em **Sistema → Configurações dos sites**.
- [ ] Envio pendente roda por cron/systemd ou ação do admin: `python manage.py send_pending_newsletters --batch-size 100`.
- [ ] Preview `/news/newsletter/preview/<id>/` funciona para staff.

## 6. Anti-bot e Borda

- [ ] Turnstile configurado no Cloudflare e chaves em `.env.prod`.
- [ ] Formulários públicos funcionam com `DEBUG=False`.
- [ ] Cloudflare usa SSL/TLS Full (strict).
- [ ] Real IP aparece nos logs por `CF-Connecting-IP`.
- [ ] Firewall só é fechado para Cloudflare depois de validar DNS, HTTPS e acesso SSH.
- [ ] Runbook completo: [cloudflare-bots.md](cloudflare-bots.md).

## 7. Backups e Manutenção

- [ ] `kellysys-deploy` cria backup gzipado em `/opt/kelly_sys/backups/` antes de alterar containers.
- [ ] `kellysys-maintenance.timer` está ativo.
- [ ] Backups antigos são podados com retenção de 30 dias.
- [ ] Nunca foi executado `docker volume prune` no ambiente de produção.

## 8. Smoke Tests

- [ ] `https://komuniki.com.br/healthz/` retorna 200.
- [ ] `https://www.komuniki.com.br/healthz/` retorna 200.
- [ ] `https://komuniki.com.br/` carrega a home.
- [ ] `https://kellyfarias.com.br/news/` carrega o portal de notícias.
- [ ] `https://kellyfarias.com.br/` redireciona para `/news/`.
- [ ] `/admin/` abre com HTTPS e login válido.
- [ ] Criar/editar rascunho de artigo não envia newsletter automaticamente.
- [ ] Ação manual de newsletter mostra resumo de entregas.
- [ ] Currículos de candidaturas não abrem por URL pública direta.

## 9. Rollback

- [ ] Commit anterior aprovado está identificado.
- [ ] Backups recentes existem antes do deploy.
- [ ] Para emergência de borda, é possível desligar proxy Cloudflare e reabrir firewall conforme [cloudflare-bots.md](cloudflare-bots.md).
- [ ] Para emergência de app, executar novo deploy apontando `production-approved` para o commit anterior validado.
