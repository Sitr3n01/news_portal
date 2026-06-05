# Documentação de Desenvolvimento — news_portal

Índice da documentação técnica do projeto. **Se você se perdeu na lógica, comece por [ARQUITETURA_E_MODELOS.md](ARQUITETURA_E_MODELOS.md).**

---

## Mapa rápido

| Documento | Para quê serve |
|-----------|----------------|
| 🧭 [ARQUITETURA_E_MODELOS.md](ARQUITETURA_E_MODELOS.md) | **Comece aqui.** Visão de conjunto: os três "rostos" (admin/notícias/escola), ciclo de um request, multi-site, diagrama ER e tabela mestra de modelos |
| 📰 [FLUXO_NEWSLETTER.md](FLUXO_NEWSLETTER.md) | Como a newsletter sai, do "Publicar" ao e-mail — sistema de **fila** (`NewsletterDelivery`), comando e ação do admin |
| 💼 [APP_HIRING.md](APP_HIRING.md) | Vagas e candidaturas: isolamento por site, pipeline de status e download **protegido** de currículos |
| 🔒 [SEGURANCA.md](SEGURANCA.md) | Todas as proteções ativas por ameaça: sanitização, auth, uploads, CSP, infra |
| 🛠️ [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | Onboarding: setup, estrutura, padrões de código, como adicionar um app |
| 📚 [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md) | Referência exaustiva por app/camada para debugging profundo |
| 🚀 [DEPLOY.md](DEPLOY.md) | Procedimento de deploy em produção |
| ✅ [go-live-checklist.md](go-live-checklist.md) | Checklist de colocação no ar (DNS, TLS, e-mail, smoke tests) |
| 🗺️ [roadmap.md](roadmap.md) | Estado das fases, decisões arquiteturais e histórico de bugs |
| 🤖 [ai-workflow.md](ai-workflow.md) | Normas do projeto, convenções e checklist de review (também é o `CLAUDE.md`) |

---

## Documentos canônicos por tópico

Os quatro primeiros documentos foram escritos a partir de **leitura direta do código** (2026-06-03) e são a **fonte da verdade** para seus temas. Onde `DEVELOPER_GUIDE.md` e `TECHNICAL_REFERENCE.md` divergirem deles (especialmente sobre a **newsletter** e o **hiring**), prevalecem os canônicos — os trechos antigos foram corrigidos e apontam para cá.

| Tópico | Documento canônico |
|--------|--------------------|
| Arquitetura e modelos | [ARQUITETURA_E_MODELOS.md](ARQUITETURA_E_MODELOS.md) |
| Newsletter | [FLUXO_NEWSLETTER.md](FLUXO_NEWSLETTER.md) |
| Vagas/candidaturas | [APP_HIRING.md](APP_HIRING.md) |
| Segurança | [SEGURANCA.md](SEGURANCA.md) |

---

## Convenções de leitura

- Caminhos de código são links relativos a partir de `docs/development/` (ex.: `../../apps/news/models.py`).
- Diagramas usam **Mermaid** (renderizam no GitHub).
- Tudo em PT-BR, alinhado às normas em [ai-workflow.md](ai-workflow.md).

---

_Índice criado em 2026-06-03._
