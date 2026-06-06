#!/usr/bin/env bash
set -Eeuo pipefail

# Imprime o bloco cloudflare-realip ATUALIZADO para colar em docker/nginx/nginx.conf,
# entre os marcadores:
#   # >>> cloudflare-realip >>>
#   # <<< cloudflare-realip <<<
#
# Rode LOCALMENTE, cole a saída entre os marcadores e abra um PR. As faixas do
# Cloudflare mudam muito raramente. É inline (não include/volume externo) para o
# deploy aplicar via `compose restart nginx`, sem recriar o container nginx.
#
# Uso:  scripts/deploy/cloudflare-realip-update.sh > /tmp/realip.txt  (depois cole)

CF_V4_URL="https://www.cloudflare.com/ips-v4"
CF_V6_URL="https://www.cloudflare.com/ips-v6"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
command -v curl >/dev/null 2>&1 || fail "curl não encontrado"

v4="$(curl -fsS --max-time 10 "${CF_V4_URL}")" || fail "falha ao baixar ${CF_V4_URL}"
v6="$(curl -fsS --max-time 10 "${CF_V6_URL}")" || fail "falha ao baixar ${CF_V6_URL}"
[[ -n "${v4}" && -n "${v6}" ]] || fail "listas do Cloudflare vazias"

printf '    # >>> cloudflare-realip >>>\n'
while read -r c; do [[ -n "${c}" ]] && printf '    set_real_ip_from %s;\n' "${c}"; done <<< "${v4}"
while read -r c; do [[ -n "${c}" ]] && printf '    set_real_ip_from %s;\n' "${c}"; done <<< "${v6}"
printf '    real_ip_header CF-Connecting-IP;\n'
printf '    # <<< cloudflare-realip <<<\n'
