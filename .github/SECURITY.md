# Política de Segurança

## Versões suportadas

Apenas a versão em produção (branch `master`, ativa em `komuniki.com.br` e
`kellyfarias.com.br`) recebe correções de segurança.

## Como reportar uma vulnerabilidade

Reporte de forma **privada** — não abra issue pública para vulnerabilidades.

- Preferencial: **GitHub Security Advisories** (aba *Security* → *Report a vulnerability*).
- Alternativa: e-mail direto ao mantenedor do repositório.

Inclua descrição, passos de reprodução, impacto e, se possível, uma sugestão de
correção.

## Expectativa de resposta

- Confirmação de recebimento em até 72 horas.
- Avaliação inicial e classificação de severidade em até 7 dias.
- Correção priorizada conforme a severidade; divulgação coordenada após o patch.

## Escopo

**Em escopo:** aplicação Django (`apps/`), configuração de deploy (`docker/`,
`scripts/deploy/`, `config/settings/`) e workflows de CI/CD (`.github/`).

**Fora de escopo:** ataques volumétricos de negação de serviço, engenharia
social e relatórios automatizados sem prova de impacto.
