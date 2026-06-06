#!/usr/bin/env bash
set -Eeuo pipefail

# Trava a origem (VPS) para que 80/443 só aceitem conexões das faixas do
# Cloudflare. Sem isto, um atacante ignora o Cloudflare/Bot Fight Mode batendo
# direto no IP da origem. Preserva SSH PRIMEIRO para evitar lockout.
#
# Uso (como root na VPS), DEPOIS de o DNS já estar proxied pelo Cloudflare:
#   sudo scripts/deploy/cloudflare-firewall.sh
#   # trava também o SSH ao seu IP (recomendado):
#   sudo ADMIN_SSH_CIDR=SEU.IP.AQUI/32 scripts/deploy/cloudflare-firewall.sh
#
# Idempotente: remove as regras web antigas marcadas com o comentário antes de
# reaplicar as faixas atuais.

SSH_PORT="${SSH_PORT:-22}"
ADMIN_SSH_CIDR="${ADMIN_SSH_CIDR:-0.0.0.0/0}"
CF_V4_URL="https://www.cloudflare.com/ips-v4"
CF_V6_URL="https://www.cloudflare.com/ips-v6"
TAG="cf-edge"

log() { printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"; }
fail() { log "ERROR: $*"; exit 1; }

[[ "$(id -u)" -eq 0 ]] || fail "execute como root (sudo)"
command -v ufw >/dev/null 2>&1 || fail "ufw não instalado — apt-get install -y ufw"
command -v curl >/dev/null 2>&1 || fail "curl não encontrado"

log "Baixando faixas do Cloudflare"
v4="$(curl -fsS --max-time 10 "${CF_V4_URL}")" || fail "falha ao baixar ${CF_V4_URL}"
v6="$(curl -fsS --max-time 10 "${CF_V6_URL}")" || fail "falha ao baixar ${CF_V6_URL}"
[[ -n "${v4}" ]] || fail "lista IPv4 vazia"

# 1. SSH PRIMEIRO (anti-lockout), antes de qualquer política de deny.
log "Garantindo SSH em ${ADMIN_SSH_CIDR} porta ${SSH_PORT}"
ufw allow from "${ADMIN_SSH_CIDR}" to any port "${SSH_PORT}" proto tcp comment "${TAG}-ssh" >/dev/null

# 2. Remove regras web antigas marcadas (idempotência). Re-consulta a cada
#    iteração porque a numeração muda após cada remoção.
log "Removendo regras ${TAG}-web antigas"
while true; do
    num="$(ufw status numbered | grep -F "${TAG}-web" | sed -E 's/^\[[[:space:]]*([0-9]+)\].*/\1/' | head -n1 || true)"
    [[ -n "${num}" ]] || break
    yes | ufw delete "${num}" >/dev/null
done

# 3. Allow 80/443 somente das faixas Cloudflare (IPv4 + IPv6).
add_web_rules() {
    local list="$1"
    while read -r cidr; do
        [[ -n "${cidr}" ]] || continue
        ufw allow from "${cidr}" to any port 80 proto tcp comment "${TAG}-web" >/dev/null
        ufw allow from "${cidr}" to any port 443 proto tcp comment "${TAG}-web" >/dev/null
    done <<< "${list}"
}
log "Liberando 80/443 para as faixas Cloudflare"
add_web_rules "${v4}"
add_web_rules "${v6}"

# 4. Política padrão: nega entrada, permite saída.
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null

# 5. Habilita (idempotente — não derruba conexões SSH ativas).
ufw --force enable >/dev/null

log "Firewall aplicado. Resumo:"
ufw status verbose
log "Valide de FORA das faixas Cloudflare: o IP da origem deve recusar 80/443."
