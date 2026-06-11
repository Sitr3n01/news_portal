# Guia Para Agentes de IA

Leia estes documentos antes de propor ou aplicar mudanças no projeto.

## Ordem Obrigatória

1. [system_overview.md](system_overview.md) — mapa do sistema, rotas, apps e infraestrutura.
2. [development_rules.md](development_rules.md) — regras que não podem ser violadas ao alterar código.
3. [../technical/ARQUITETURA_E_MODELOS.md](../technical/ARQUITETURA_E_MODELOS.md) — explicação humana da arquitetura.
4. [../technical/SEGURANCA.md](../technical/SEGURANCA.md) — checklist de segurança.

## Resumo de Segurança Para Agentes

- O sistema está em produção.
- Não use `|safe` em templates; use `sanitize_html`.
- Não use `Model.objects` em views públicas quando o model tem `on_site`.
- Não introduza CBVs; o padrão do projeto é FBV.
- Não adicione CDN JavaScript/CSS público sem revisão explícita.
- Não documente recurso como existente sem confirmar no código versionado.
- Ao mudar models, gere e revise migrations.

## Descoberta

Arquivos locais como `AGENTS.md`, `CLAUDE.md` e `gemini.md` podem existir vazios ou ignorados pelo git. A fonte compartilhada e versionável para agentes é este diretório `docs/ai/`.
