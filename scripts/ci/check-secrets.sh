#!/usr/bin/env bash
# Varredura de segredos nos arquivos versionados, contra .secrets.baseline.
#
# A baseline guarda os falsos positivos já triados (fixtures de teste,
# placeholders do .env.*.example, chaves públicas de teste da Cloudflare,
# senhas do Postgres descartável do CI). Qualquer segredo FORA dela reprova.
#
# O detect-secrets-hook também sai com erro quando só os NÚMEROS DE LINHA da
# baseline mudaram (alguém inseriu linhas acima de uma fixture). Isso não é
# segredo novo, então não reprova aqui. Para atualizar a baseline de verdade:
#   detect-secrets scan --baseline .secrets.baseline
#   detect-secrets audit .secrets.baseline     # marque cada item novo
set -uo pipefail

cd "$(git rev-parse --show-toplevel)"
log="$(mktemp)"
git ls-files -z | xargs -0 detect-secrets-hook --baseline .secrets.baseline >"$log" 2>&1
status=$?
cat "$log"
git checkout --quiet -- .secrets.baseline  # descarta a reescrita de números de linha

if grep -q "Potential secrets about to be committed" "$log"; then
    echo "::error::Segredo fora da .secrets.baseline. Remova-o (e troque a credencial) ou, se for falso positivo, atualize a baseline."
    exit 1
fi
if [ "$status" -ne 0 ] && ! grep -q "The baseline file was updated" "$log"; then
    echo "::error::detect-secrets falhou (código $status)."
    exit "$status"
fi
echo "Nenhum segredo novo fora da baseline."
