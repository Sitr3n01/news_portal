#!/usr/bin/env bash
set -Eeuo pipefail

# Regenera docker/nginx/cloudflare-realip.conf a partir das faixas oficiais do
# Cloudflare (https://www.cloudflare.com/ips-v4 e ips-v6).
#
# Rode LOCALMENTE e commite o resultado via PR. NÃO rode na VPS: o deploy é
# pull-based e exige árvore git limpa (kellysys-deploy aborta com mudanças
# rastreadas presentes). As faixas do Cloudflare mudam muito raramente.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUT="${REPO_ROOT}/docker/nginx/cloudflare-realip.conf"
CF_V4_URL="https://www.cloudflare.com/ips-v4"
CF_V6_URL="https://www.cloudflare.com/ips-v6"

log() { printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"; }
fail() { log "ERROR: $*"; exit 1; }

command -v curl >/dev/null 2>&1 || fail "curl não encontrado"

log "Baixando faixas do Cloudflare"
v4="$(curl -fsS --max-time 10 "${CF_V4_URL}")" || fail "falha ao baixar ${CF_V4_URL}"
v6="$(curl -fsS --max-time 10 "${CF_V6_URL}")" || fail "falha ao baixar ${CF_V6_URL}"
[[ -n "${v4}" ]] || fail "lista IPv4 vazia"
[[ -n "${v6}" ]] || fail "lista IPv6 vazia"

tmp="$(mktemp)"
trap 'rm -f "${tmp}"' EXIT
{
    printf '# GERADO/mantido por scripts/deploy/cloudflare-realip-update.sh — não edite à mão.\n'
    printf '# Restaura o IP real do visitante quando a requisição chega via proxy Cloudflare.\n'
    printf '# Incluído por docker/nginx/nginx.conf no contexto http{}.\n\n'
    printf '# Cloudflare IPv4\n'
    while read -r c; do [[ -n "${c}" ]] && printf 'set_real_ip_from %s;\n' "${c}"; done <<< "${v4}"
    printf '\n# Cloudflare IPv6\n'
    while read -r c; do [[ -n "${c}" ]] && printf 'set_real_ip_from %s;\n' "${c}"; done <<< "${v6}"
    printf '\nreal_ip_header CF-Connecting-IP;\n'
} > "${tmp}"

mv "${tmp}" "${OUT}"
trap - EXIT
log "Atualizado: ${OUT}"
log "Revise com 'git diff' e abra um PR. 'nginx -t' roda no deploy."
