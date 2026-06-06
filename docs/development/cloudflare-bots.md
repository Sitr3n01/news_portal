# Cloudflare Anti-Bot — Runbook (VPS Hostinger)

> Como habilitar a proteção de bots do Cloudflare em **duas camadas** e manter
> os serviços dependentes (contato, newsletter, comentários, rate-limit, axes)
> operacionais. Relacionado: [SEGURANCA.md](SEGURANCA.md) · [secure-deploy.md](secure-deploy.md) · [go-live-checklist.md](go-live-checklist.md).

## As duas camadas

| Camada | O que faz | Onde |
|--------|-----------|------|
| **A — Turnstile (app)** | Widget anti-bot nos formulários públicos. Sem as chaves, os forms **falham-fechado** em produção. | `.env.prod` + `apps/common/turnstile.py` |
| **B — Borda (proxy)** | Cloudflare na frente da origem: Bot Fight Mode, WAF, TLS de borda. Exige restaurar o IP real e travar a origem. | Painel Cloudflare + `nginx` + firewall |

> **Ordem segura (anti-lockout):** A → B1 (DNS) → B2 (real-IP, já no deploy) → **verificar** → B3 (firewall). Nunca trave o firewall (B3) antes do tráfego já entrar via Cloudflare e do SSH estar garantido.

---

## Camada A — Turnstile (torna os formulários operacionais)

1. No painel: **Cloudflare → Turnstile → Add widget**. Modo *Managed*. Hostnames:
   `komuniki.com.br`, `www.komuniki.com.br`, `kellyfarias.com.br`, `www.kellyfarias.com.br`.
   Anote o **Site Key** e o **Secret Key**.

2. Na VPS, adicione as chaves ao `.env.prod` (não rastreado) e ajuste a permissão:

```bash
sudo tee -a /opt/kelly_sys/.env.prod >/dev/null <<'EOF'
CLOUDFLARE_TURNSTILE_SITE_KEY=COLE_O_SITE_KEY
CLOUDFLARE_TURNSTILE_SECRET_KEY=COLE_O_SECRET_KEY
CLOUDFLARE_TURNSTILE_VERIFY_TIMEOUT=5.0
EOF
sudo chmod 600 /opt/kelly_sys/.env.prod
# Garanta que não ficaram chaves duplicadas:
grep -c CLOUDFLARE_TURNSTILE_SITE_KEY /opt/kelly_sys/.env.prod   # deve imprimir 1
```

3. Recrie só o container web (lê o novo `.env.prod`):

```bash
cd /opt/kelly_sys
docker compose -p kellysys -f docker/docker-compose.prod.yml up -d --force-recreate web
```

4. **Verifique:** abra `https://komuniki.com.br/contato/` e a newsletter no blog —
   o widget Turnstile deve renderizar e o envio deve **funcionar** (sai do
   estado fail-closed).

---

## Camada B — Borda (Cloudflare proxy + Bot Fight Mode)

### B1 — Painel / DNS (feito por você no Cloudflare + Hostinger)

1. **Add a Site** no Cloudflare para `komuniki.com.br` e `kellyfarias.com.br` (plano Free serve).
2. No registrador (Hostinger), troque os **nameservers** para os que o Cloudflare indicar. *(Propagação: minutos a horas.)*
3. Em **DNS**, registros `A` para `@` e `www` apontando para `2.25.178.16`, com **proxy LIGADO (nuvem laranja)**.
4. Em **SSL/TLS → Overview**, modo **Full (strict)**. A origem já tem certificado Let's Encrypt válido.
   > ⚠️ **Nunca use "Flexible"** — causaria loop de redirecionamento com `SECURE_SSL_REDIRECT=True`.
5. Em **Security → Bots**, ligue **Bot Fight Mode**.
6. (Opcional) **Security → WAF**: regra de rate-limit por path sensível (`/contato/`, `/admin/`).

### B2 — nginx restaura o IP real (já versionado, aplica no deploy)

Já entregue no repositório:
- [`docker/nginx/cloudflare-realip.conf`](../../docker/nginx/cloudflare-realip.conf) — `set_real_ip_from` (faixas CF) + `real_ip_header CF-Connecting-IP`.
- [`nginx.conf`](../../docker/nginx/nginx.conf) faz `include` dele e encaminha `X-Forwarded-For $remote_addr` (IP real restaurado).
- Montado no container via [`docker-compose.prod.yml`](../../docker/docker-compose.prod.yml).

Aplica sozinho no próximo deploy aprovado. Para conferir após o deploy:

```bash
cd /opt/kelly_sys
docker compose -p kellysys -f docker/docker-compose.prod.yml exec nginx nginx -t
docker compose -p kellysys -f docker/docker-compose.prod.yml logs --tail=20 nginx
# Os IPs nos logs devem ser de VISITANTES, não faixas do Cloudflare.
```

Atualizar as faixas (raro) — rode **localmente**, nunca na VPS, e abra um PR:

```bash
scripts/deploy/cloudflare-realip-update.sh
git diff docker/nginx/cloudflare-realip.conf
```

### B3 — Firewall: origem só aceita o Cloudflare

Só execute **depois** de B1 concluído e do tráfego já entrar via Cloudflare.
Sem isto, um atacante ignora o Bot Fight Mode batendo direto em `2.25.178.16`.

```bash
cd /opt/kelly_sys
# Recomendado: trave também o SSH ao seu IP. Descubra seu IP em https://ifconfig.me
sudo ADMIN_SSH_CIDR=SEU.IP.PUBLICO/32 scripts/deploy/cloudflare-firewall.sh
# (sem ADMIN_SSH_CIDR, mantém SSH aberto a todos — menos seguro, porém sem risco de lockout)
```

O script ([`cloudflare-firewall.sh`](../../scripts/deploy/cloudflare-firewall.sh)):
libera SSH **primeiro**, remove regras web antigas marcadas (idempotente),
libera 80/443 só das faixas Cloudflare e aplica `default deny incoming`.

### B4 — Verificação de borda

```bash
# 1) De uma máquina FORA das faixas Cloudflare (ex.: seu notebook):
curl -I --max-time 5 http://2.25.178.16/        # esperado: timeout / connection refused
curl -I --max-time 5 https://komuniki.com.br/   # esperado: 200/301 (via Cloudflare)

# 2) Header do Cloudflare presente (prova que passou pela borda):
curl -sI https://komuniki.com.br/ | grep -i '^cf-ray'   # deve existir

# 3) Bot conhecido recebe desafio do Bot Fight Mode:
curl -A "python-requests/2.31" -I https://komuniki.com.br/   # pode vir 403/challenge

# 4) Forms ainda funcionam (Turnstile da Camada A) e o rate-limit é por visitante.
```

---

## Rollback rápido

- **Borda com problema:** no DNS do Cloudflare, desligue o proxy (nuvem cinza) — volta a apontar direto para a origem. Reverta o firewall: `sudo ufw disable`.
- **Turnstile bloqueando tudo:** confira que `CLOUDFLARE_TURNSTILE_*` estão corretas no `.env.prod` e recrie o `web`. Em emergência, remover as duas chaves volta ao fail-closed (forms bloqueados) — prefira corrigir as chaves.

## Por que cada peça importa

- **Real-IP (B2)** mantém `rate-limit` do nginx, `django-axes` e o `remoteip` do Turnstile vendo o visitante real, não o Cloudflare.
- **Firewall (B3)** é o que torna a proteção de bots **inescapável** — sem ele, a borda é opcional para o atacante.
- **Full (strict)** preserva o `SECURE_SSL_REDIRECT` do Django sem loop.
