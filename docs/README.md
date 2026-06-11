# Documentação — news_portal

Este diretório é a fonte de verdade da documentação do projeto. A árvore foi separada por público para evitar que uma pessoa não técnica precise ler material de engenharia, e para que agentes de IA encontrem regras objetivas sem vasculhar históricos antigos.

## Por Onde Começar

| Público | Entrada recomendada |
|---------|---------------------|
| Operador não técnico | [user/index.md](user/index.md) |
| Editor do Blog da Kelly | [user/manual_noticias.md](user/manual_noticias.md) |
| Administrador Komuniki | [user/manual_escola.md](user/manual_escola.md) |
| Desenvolvedor | [technical/README.md](technical/README.md) |
| Deploy/go-live | [technical/go-live-checklist.md](technical/go-live-checklist.md) |
| Agente de IA | [ai/README.md](ai/README.md) |

## Estrutura

- `user/`: guias operacionais em linguagem simples, com foco em rotinas do admin.
- `technical/`: arquitetura, segurança, deploy, runbooks e referência técnica.
- `ai/`: visão sistêmica e regras de modificação para agentes.
- `MAINTENANCE_HISTORY.md`: registro de mudanças grandes, auditorias e manutenção pós-produção.

## Regras de Manutenção

- Atualize o índice desta pasta quando criar ou remover documento.
- Se a documentação divergir do código, corrija a documentação antes de promover deploy.
- Evite prometer recursos futuros em manuais de usuário; recursos ausentes devem aparecer como limitação conhecida ou item de backlog.
- Documentos de deploy devem usar os caminhos de produção atuais: `/opt/kelly_sys`, Compose project `kellysys`, branch `master` e tag `production-approved`.
