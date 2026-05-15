# news_portal - Plano Global do Projeto

## Visão Geral

Sistema web unificado que gerencia dois sites independentes de um grupo educacional:
- **Portal de Notícias** ("The Chronicle") — portal público de notícias. **Quase pronto** — funcional com design aplicado, faltam refinamentos
- **Site da Escola** — institucional com contratação e contato. **Inacabado** — models e views básicas existem, falta completar templates e design
- **Dashboard Admin** (Django Unfold) — painel unificado para gerenciar ambos. **Em correção** — dashboard customizado nunca funcionou, sendo reconstruído na Fase 7

Os portais são **independentes em dados** mas gerenciados pelo mesmo admin. Único link cruzado: botão na navbar do news → escola.

---

## Stack

- **Backend:** Python 3.12+ / Django 5.x
- **Database:** PostgreSQL 16
- **Frontend:** Django Templates + HTMX + Alpine.js
- **Admin:** Django Unfold
- **Static:** WhiteNoise
- **Dev:** Docker Compose (Django + PostgreSQL + Mailpit)

---

## Estrutura de Apps

| App | Responsabilidade |
|-----|-----------------|
| `apps.common` | Models abstratos, SiteExtension, utils, context processors |
| `apps.accounts` | CustomUser, roles, permissões (Groups) |
| `apps.school` | Páginas CMS, equipe, depoimentos |
| `apps.hiring` | Vagas, candidaturas, departamentos |
| `apps.contact` | Formulários de contato e inquiries |
| `apps.news` | Artigos, categorias, tags, RSS, newsletter |
| `apps.media_library` | Biblioteca de mídia compartilhada |

---

## Fases e Status

### Fase 1: Fundação ✅
| # | Tarefa | Status |
|---|--------|--------|
| 1 | Estrutura de diretórios e config Django | ✅ Concluído |
| 2 | `config/settings/base.py` completo | ✅ Concluído |
| 3 | `apps.accounts` com CustomUser | ✅ Concluído |
| 4 | `apps.common` com models abstratos | ✅ Concluído |
| 5 | Docker Compose dev | ✅ Concluído |
| 6 | Primeira migration + superuser | ✅ Concluído |
| 7 | Django Unfold configurado | ✅ Concluído |

### Fase 2: Apps de Conteúdo ✅
| # | Tarefa | Status |
|---|--------|--------|
| 8 | `apps.school` completo | ✅ Concluído |
| 9 | `apps.hiring` completo | ✅ Concluído |
| 10 | `apps.contact` completo | ✅ Concluído |
| 11 | `apps.news` básico (models, views, admin) | ✅ Concluído |
| 12 | `apps.media_library` completo | ✅ Concluído |

### Fase 3: Templates e Frontend (Básico) ✅
| # | Tarefa | Status |
|---|--------|--------|
| 13 | Base templates (base.html, base_school.html, base_news.html) | ✅ Concluído |
| 14 | Templates escola (home, page_detail, team_list) | ✅ Concluído |
| 15 | Templates notícias (article_list, article_detail, category_detail) | ✅ Concluído |
| 16 | Templates contratação (job_list, job_detail) | ✅ Concluído |
| 17 | Templates contato (contact_page) | ✅ Concluído |
| 18 | Integração HTMX (middleware configurado) | ✅ Concluído |
| 19 | Integração Alpine.js (menus, flash messages) | ✅ Concluído |

### Fase 4: Polimento e Deploy ✅
| # | Tarefa | Status |
|---|--------|--------|
| 20 | Data migrations iniciais | ✅ Concluído |
| 21 | Sitemaps (ArticleSitemap, PageSitemap) | ✅ Concluído |
| 22 | Testes (school, news, hiring, contact) | ✅ Concluído |
| 23 | Docker Compose produção + Nginx | ✅ Concluído |
| 24 | CI/CD GitHub Actions | ✅ Concluído |
| 25 | Documentação deploy (DEPLOY.md) | ✅ Concluído |

---

### Fase 5: Portal de Notícias — Funcionalidades Completas ✅
| # | Tarefa | Status |
|---|--------|--------|
| 5A | Correções backend: `get_absolute_url`, `F()` view_count, `select_related`, `utils.py` | ✅ Concluído |
| 5B | Model `NewsletterSubscription` + form + view + admin | ✅ Concluído |
| 5C | Novas views: tag, autor, busca, arquivo, load-more HTMX, relacionados | ✅ Concluído |
| 5D | RSS Feeds (`LatestArticlesFeed`, `CategoryFeed`) | ✅ Concluído |
| 5E | SEO: Open Graph, Twitter Cards, JSON-LD, canonical, RSS link | ✅ Concluído |
| 5F | Partials reutilizáveis: card, sidebar, grid, paginação, newsletter, like_button, comments_list | ✅ Concluído |
| 5G | Páginas novas: tag_detail, author_detail, search, archive | ✅ Concluído |
| 5H | Atualização templates existentes: list, detail, category, navbar | ✅ Concluído |
| 5I | Admin aprimorado: Unfold ModelAdmin, fieldsets, actions, Comment/Like/Bookmark | ✅ Concluído |
| 5J | Context processor: categorias na navegação | ✅ Concluído |
| 5K | Sistema de comentários e likes (add_comment, delete_comment, toggle_like) | ✅ Concluído |
| 5L | Autenticação e dashboard de usuário (login, register, bookmarks) | ✅ Concluído |
| 5M | Bug fixes revisão Claude: unique_per_site newsletter, sidebar filtro site, CategoryFeed 404 | ✅ Concluído |

### Fase 6: Admin Enhancement — Painel Unificado Bilíngue ⚠️ (parcial)
| # | Tarefa | Status |
|---|--------|--------|
| 6A | Migrar todos os admin.py para `unfold.admin.ModelAdmin` | ✅ Concluído |
| 6B | Configurar `UNFOLD` settings: branding, sidebar agrupada por portal, cores `#1152d4` | ✅ Concluído |
| 6C | Dashboard customizado: cards de stats por portal | ⚠️ Código escrito mas **nunca funcionou** — usava `INDEX_DASHBOARD` (inexistente no Unfold). Fix na Fase 7 |
| 6D | i18n PT/BR: `LocaleMiddleware`, `LANGUAGES`, path `i18n/` | ✅ Concluído |
| 6E | Melhorar admin models: fieldsets, actions, badges de role | ✅ Concluído |
| 6F | Debug dashboard: Tailwind config ordering, URL filter fix | ✅ Concluído |

### ~~Fase 7 (antiga): Portal de Notícias — Design (Google Stitch)~~ ❌ CANCELADA
> **Motivo:** O workflow Google Stitch → Google Jules falhou. Jules não entregou o design completo, Gemini alucinhou tentando adaptar HTML incompleto, e o resultado acumulou código órfão e conflitos CSS. Abordagem abandonada em 2026-02-24. Design visual será feito via CSS puro (nova Fase 9).

### Fase 7: Reorganização + Debug + Dashboard Funcional ✅
| # | Tarefa | Status |
|---|--------|--------|
| 7A | Deletar arquivos temporários (design_reference, PROGRESS_SESSION.md) | ✅ Concluído |
| 7B | Fix CRÍTICO: Dashboard — trocar `INDEX_DASHBOARD` por `DASHBOARD_CALLBACK`, reescrever View→callback, renomear template | ✅ Concluído |
| 7C | Fix RSS feeds: `Article.objects` → `Article.on_site` em feeds.py | ✅ Concluído |
| 7D | Fix admin action: renomear `mark_approved` → `mark_accepted` | ✅ Concluído |
| 7E | Corrigir template dashboard: remover wrapper `<main>`, shadow inválido, `max-w-7xl` | ✅ Concluído |
| 7F | Adicionar `help_text` PT-BR nos models para usuários não-técnicos | ✅ Concluído |
| 7G | Traduzir fieldsets, actions, verbose_names e TextChoices para PT-BR em todos os models e admin.py | ✅ Concluído |
| 7H | Atualizar arquivos .md (PLAN, CLAUDE, GEMINI) | ✅ Concluído |
| 7I | Verificação final: `manage.py check` sem erros, migrations aplicadas | ✅ Concluído |

### Fase 8: Consistência + Dashboard Funcional ✅
> Dashboard completamente reescrita por Claude. Portal de notícias com bilinguismo consistente.

| # | Tarefa | Status |
|---|--------|--------|
| 8.1 | Reescrever `admin/index.html`: single-line vars, language selector PT/EN, empty states | ✅ Concluído |
| 8.2 | Corrigir 7 strings PT-only em `article_card`, `pagination`, `category_detail`, `tag_detail`, `author_detail` | ✅ Concluído |
| 8.3 | `manage.py check` → 0 erros | ✅ Concluído |
| 8.4 | **Debug e Correções do Portal de Notícias** (9 bugs corrigidos pelo Gemini) | ✅ Concluído |
| 8.5 | Polir responsividade mobile (testar 375px, 768px) | ⬜ Pendente |
| 8.6 | **Auditoria de Segurança Final** (2ª rodada — Claude) | ✅ Concluído |

#### Sub-tarefas da Fase 8.6 — Segurança Final (detalhes no SECURITY_REPORT.md + plano Claude):
| # | Tarefa | Severidade | Status |
|---|--------|-----------|--------|
| 8.6.A1 | Sitemap escola: Page.on_site (vazava páginas de todos os sites) | 🔴 CRÍTICO | ✅ |
| 8.6.A2 | Comment max length [:5000] (DoS) | 🔴 CRÍTICO | ✅ |
| 8.6.A3 | Remover último `\|safe` (password_reset_confirm.html) | 🔴 CRÍTICO | ✅ |
| 8.6.A4 | PASSWORD_RESET_TIMEOUT = 3600 (era 24h default) | 🔴 CRÍTICO | ✅ |
| 8.6.B1 | Mensagem genérica no registro (anti user-enumeration) | 🟡 ALTO | ✅ |
| 8.6.B2 | Email unique=True no CustomUser (constraint no banco) | 🟡 ALTO | ✅ |
| 8.6.B3 | Centralizar bleach + sanitizar Page.save() | 🟡 ALTO | ✅ |
| 8.6.B4 | CSP header no nginx | 🟡 ALTO | ✅ |
| 8.6.C1 | safe_referer_redirect usar get_current_site | 🟢 MÉDIO | ✅ |
| 8.6.C2 | Hiring mensagem genérica para duplicata | 🟢 MÉDIO | ✅ |
| 8.6.C3 | SESSION_SAVE_EVERY_REQUEST = True | 🟢 MÉDIO | ✅ |
| 8.6.D1 | Deletar arquivo `nul` (artefato Windows) | 🔵 LIMPEZA | ✅ |
| 8.6.D2 | nginx server_name: `example.com` → `_` (catch-all) | 🔵 LIMPEZA | ✅ |

### Fase 9: Site da Escola — Construção Completa ⬜
> O site da escola está **completamente inacabado**. Tem models e views básicas mas precisa de funcionalidades, templates e design completos.

| # | Tarefa | Status |
|---|--------|--------|
| 9.1 | Auditar estado atual: listar o que funciona e o que falta | ⬜ Pendente |
| 9.2 | Completar templates da escola (home, páginas, equipe, depoimentos) | ⬜ Pendente |
| 9.3 | Integrar hiring (vagas) e contact (formulário) nos templates | ⬜ Pendente |
| 9.4 | Aplicar design visual distinto (paleta diferente do news) | ⬜ Pendente |
| 9.5 | Responsividade mobile | ⬜ Pendente |

### Fase 10: Hardening para Produção ⬜ (parcial — segurança já coberta)
| # | Tarefa | Status |
|---|--------|--------|
| 10.1 | Páginas de erro customizadas (404, 500) | ⬜ Pendente |
| 10.2 | Monitoramento e logging | ⬜ Pendente |
| 10.3 | Backup e recovery de dados | ⬜ Pendente |
| 10.4 | Revisão de segurança (CSRF, XSS, headers) | ✅ Coberta pela Fase 8.6 |

---

## Decisões Arquiteturais

1. **Multi-site via Django Sites Framework** — roteamento por path inicialmente, subdomínios depois
2. **CustomUser antes da 1ª migration** — obrigatório pelo Django
3. **Django Unfold** para admin — sem construir painel customizado
4. **HTMX + Alpine.js** — SEO nativo, sem build pipeline JS
5. **WhiteNoise** — serve statics sem Nginx em dev e shared hosting
6. **Path-based routing** — escola em `/`, notícias em `/news/`
7. **Funcionalidade antes do design** — toda a lógica implementada primeiro, design visual aplicado como camada separada
8. **FBV (Function-Based Views)** — padrão consistente em todo o projeto, sem migrar para CBV
9. **Busca com Django Q()** — sem biblioteca externa (Elasticsearch desnecessário para volume escolar)
10. **`get_sidebar_context()` como utility** — evita queries desnecessárias em páginas que não precisam da sidebar
11. **Dashboard via `DASHBOARD_CALLBACK`** — função callback que o Unfold chama para injetar dados no template `admin/index.html` (não usar View class)
12. **Design CSS puro** — sem depender de ferramentas externas (Stitch/Jules). Tailwind via Unfold, sem CDN extra
13. **GEMINI.md max 3KB** — instruções concisas, sem código inline, limpar após cada fase

---

## Bugs Resolvidos (Revisão Claude — Fase 5M)

| Bug | Fix Aplicado |
|-----|-------------|
| `NewsletterSubscription.email` unique global | `unique_together = [['email', 'site']]` + migration 0005 |
| `get_sidebar_context()` sem filtro de site | `Article.on_site` em vez de `Article.objects` |
| `CategoryFeed` levantava 500 | `get_object_or_404(Category, slug=slug)` |
| Comments hardcoded no article_detail | Loop real `{% for comment in comments %}` + form autenticado |
| Like count "12" hardcoded | `{{ like_count }}` real + view `toggle_like` + partial `like_button.html` |
| Comment/Like/Bookmark sem admin | `CommentAdmin`, `ArticleLikeAdmin`, `ArticleBookmarkAdmin` registrados |
| Sem endpoint de post de comentário | View `add_comment` + URL + formulário no template |
| `user_dashboard` query ineficiente | `Article.objects.filter(bookmarks__user=user)` direto |
| `toggle_bookmark` usando HTTP_REFERER | Parâmetro `?source=dashboard` |

---

## Lições Aprendidas

| Data | Lição | Impacto |
|------|-------|---------|
| 2026-02-24 | Workflow Stitch → Jules falhou: IA externas não entregam código confiável para integração direta | Fase 7 antiga cancelada, design será CSS puro |
| 2026-02-24 | `INDEX_DASHBOARD` nunca existiu no Unfold — Gemini alucionou a chave, Claude não verificou | Dashboard ficou órfã por dias. Sempre conferir docs oficiais |
| 2026-02-24 | GEMINI.md cresceu para 106KB com instruções acumuladas → Gemini alucinou | Regra: max 3KB, limpar após cada fase, sem blocos de código |
| 2026-02-24 | Dashboard usava Tailwind CDN sobre Tailwind compilado do Unfold → conflitos CSS | Nunca carregar CDN externo sobre framework que já compila Tailwind |

---

## Bugs Encontrados (Revisão Claude — Fase 7)

| # | Bug | Severidade | Arquivo |
|---|-----|-----------|---------|
| 1 | `INDEX_DASHBOARD` não existe no Unfold — dashboard nunca renderizou | CRÍTICO | `config/settings/base.py:265` |
| 2 | `AdminDashboardView` é View class mas Unfold espera callback function | CRÍTICO | `apps/common/dashboard.py` |
| 3 | Template `dashboard.html` — Unfold procura `index.html` | CRÍTICO | `templates/admin/dashboard.html` |
| 4 | Tailwind CDN conflita com Tailwind compilado do Unfold | ALTO | `templates/admin/dashboard.html:9-37` |
| 5 | RSS feeds usam `Article.objects` em vez de `Article.on_site` | MÉDIO | `apps/news/feeds.py:17,55` |
| 6 | `mark_approved` não bate com status `accepted` | BAIXO | `apps/hiring/admin.py` |
| 7-9 | Fieldsets, actions em inglês; sem help_text para leigos | BAIXO | Todos admin.py / models |

---

## Bugs Encontrados (Auditoria Claude — Fase 8.4)

| # | Bug | Severidade | Arquivo |
|---|-----|-----------|---------|
| 1 | Tailwind primary como flat string — `text-primary-600` etc não gera CSS | 🔴 CRÍTICO | `base_news.html` |
| 2 | Article pode ter `status=published` mas `published_at=None` → desaparece | 🔴 CRÍTICO | `apps/news/models.py` |
| 3 | Sitemap usa `Article.objects` → expõe artigos de todos os sites | 🔴 CRÍTICO | `apps/news/sitemaps.py` |
| 4 | HTMX load-more aponta para `#articles-grid` inexistente | 🔴 CRÍTICO | `article_list.html` |
| 5 | `is_liked` hardcoded False — like nunca reflete estado real | 🟡 MODERADO | `views.py` / template |
| 6 | Page size HTMX (9) ≠ main view (12) | 🟡 MODERADO | `views.py` |
| 7 | Container width inconsistente (1200/1280/7xl) entre páginas | 🟡 MODERADO | Vários templates |
| 8 | Sidebar "trending" ordena por views mas mostra horário | 🟢 MENOR | `sidebar.html` |
| 9 | Load-more HTMX inclui featured duplicado | 🟢 MENOR | `views.py` |

---

## Estado Atual

- **Fase:** 8.6 concluída — Auditoria de Segurança Final
- **Tarefa ativa:** Nenhuma — tudo implementado
- **Próximo:** 8.5 (responsividade mobile) ou Fase 9 (site da escola)
- **Bloqueios:** Nenhum. Pendente apenas `makemigrations` + `migrate` para email unique e Page manager
- **Última atualização:** 2026-02-25

### Resumo do estado por área:
| Área | Estado | Nota |
|------|--------|------|
| **Portal de Notícias** | 🟢 Funcional + Seguro | Bugs corrigidos (8.4), segurança auditada 2x (Gemini + Claude) |
| **Dashboard Admin** | 🟢 Funcional + Seguro | Export emails restrito, axes ativo, CSRF/session hardened |
| **Site da Escola** | 🔴 Inacabado | Models/views básicas existem, templates e design incompletos (Fase 9) |
| **Infraestrutura** | 🟢 Hardened | nginx com CSP/headers/rate-limit, Docker non-root, expose vs ports |
| **Segurança** | 🟢 Auditada 2x | 20+ proteções ativas. Nenhum `\|safe` em templates. Bleach centralizado |
