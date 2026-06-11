# news_portal — Plano Global do Projeto

## Visão Geral

Sistema web unificado que gerencia dois sites independentes de um grupo educacional:
- **Portal de Notícias** ("The Chronicle") — portal público de notícias. **Quase pronto** — funcional com design aplicado, faltam refinamentos
- **Site da Escola** — institucional com contratação e contato. **Funcional + CMS** — design completo, backend administrável e dados isolados por site
- **Dashboard Admin** (Django Unfold) — painel unificado para gerenciar ambos. **Funcional + UX operacional completa** — dashboard, guias por área, listas/formulários orientados a tarefa e perfis administrativos por função

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
| `apps.social` | Contas e posts de redes sociais (Instagram/TikTok) + sincronização |

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
| 5M | Bug fixes de revisão técnica: unique_per_site newsletter, sidebar filtro site, CategoryFeed 404 | ✅ Concluído |

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
| 7H | Atualizar documentação técnica e plano de execução | ✅ Concluído |
| 7I | Verificação final: `manage.py check` sem erros, migrations aplicadas | ✅ Concluído |

### Fase 8: Consistência + Dashboard Funcional ✅
> Dashboard completamente reescrita. Portal de notícias com bilinguismo consistente.

| # | Tarefa | Status |
|---|--------|--------|
| 8.1 | Reescrever `admin/index.html`: single-line vars, language selector PT/EN, empty states | ✅ Concluído |
| 8.2 | Corrigir 7 strings PT-only em `article_card`, `pagination`, `category_detail`, `tag_detail`, `author_detail` | ✅ Concluído |
| 8.3 | `manage.py check` → 0 erros | ✅ Concluído |
| 8.4 | **Debug e Correções do Portal de Notícias** (9 bugs corrigidos pelo Gemini) | ✅ Concluído |
| 8.5 | Polir responsividade mobile (testar 375px, 768px) | ✅ Concluído |
| 8.6 | **Auditoria de Segurança Final** (2ª rodada) | ✅ Concluído |

#### Sub-tarefas da Fase 8.6 — Segurança Final (detalhes no SECURITY_REPORT.md + plano técnico):
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

### Fase 9: Site da Escola — Construção Completa ✅
> Site institucional da escola construído com home completa, identidade visual própria, páginas institucionais polidas e integração visual com vagas/contato.

| # | Tarefa | Status |
|---|--------|--------|
| 9.1 | Auditar estado atual: listar o que funciona e o que falta | ✅ Concluído |
| 9.2 | Completar templates da escola (home, páginas, equipe, depoimentos) | ✅ Concluído |
| 9.3 | Integrar hiring (vagas) e contact (formulário) nos templates | ✅ Concluído |
| 9.4 | Aplicar design visual distinto (paleta diferente do news) | ✅ Concluído |
| 9.5 | Responsividade mobile | ✅ Concluído |

### Fase 9.1: Backend CMS Escola + Isolamento Multi-site ✅
> Backend do site escolar alinhado ao frontend da Fase 9, com conteúdo editável no Django Unfold, fallbacks seguros e isolamento por `Site`.

| # | Tarefa | Status |
|---|--------|--------|
| 9.1A | Criar configuração editável da home escolar (`SchoolHomeConfig`) | ✅ Concluído |
| 9.1B | Criar cards administráveis por seção (`SchoolFeature`) | ✅ Concluído |
| 9.1C | Isolar páginas, equipe, depoimentos, departamentos e vagas por site | ✅ Concluído |
| 9.1D | Atualizar admin PT-BR com filtros, fieldsets e navegação Unfold | ✅ Concluído |
| 9.1E | Atualizar views/templates para consumir backend com fallbacks seguros | ✅ Concluído |
| 9.1F | Cobrir isolamento multi-site e conteúdo CMS com testes | ✅ Concluído |
| 9.1G | Validar quality gate local completo | ✅ Concluído |

### Fase 10: Hardening para Produção ⬜
> Segurança da aplicação já foi auditada na Fase 8.6. Esta fase fecha prontidão operacional: experiência de erro, logs, backup, configuração final e validação de deploy.

| # | Tarefa | Status |
|---|--------|--------|
| 10.1 | Criar páginas de erro customizadas para 404, 500, 403 e 400 com identidade visual dos portais | ⬜ Pendente |
| 10.2 | Configurar logging de produção com rotação, níveis por módulo e captura de erros críticos | ⬜ Pendente |
| 10.3 | Definir monitoramento mínimo: healthcheck HTTP, status do container, espaço em disco e falhas de e-mail/newsletter | ⬜ Pendente |
| 10.4 | Criar rotina de backup: dump PostgreSQL, cópia de `media/`, retenção e local de armazenamento | ⬜ Pendente |
| 10.5 | Documentar e testar restore completo em ambiente local/staging com banco e arquivos de mídia | ⬜ Pendente |
| 10.6 | Revisar configuração final de produção: `DEBUG=False`, `ALLOWED_HOSTS`, HTTPS, cookies seguros, `CSRF_TRUSTED_ORIGINS` e variáveis SMTP | ⬜ Pendente |
| 10.7 | Validar pipeline de deploy: migrations, collectstatic, containers, Nginx, headers e rotas públicas/admin | ⬜ Pendente |
| 10.8 | Criar checklist de go-live e runbook operacional em `docs/development/DEPLOY.md` | ⬜ Pendente |
| 10.9 | Revisão de segurança final (CSRF, XSS, headers, uploads e permissões) | ✅ Coberta pela Fase 8.6; revisar apenas se houver mudança estrutural |

#### Critérios de aceite da Fase 10
- Produção sobe com `docker compose` sem depender de ferramentas locais.
- Rotas `/`, `/news/`, `/admin/`, `sitemap.xml` e fluxos principais respondem corretamente.
- Erros 404/500 exibem páginas próprias, sem stack trace para usuário final.
- Logs e backups têm instruções claras de operação e recuperação.
- Restore de banco e mídia foi testado pelo menos uma vez.
- Checklist de go-live cobre DNS, HTTPS, e-mail, superusuário, Site Framework e smoke tests.

### Fase 11: Go-live e Operação Inicial ⬜
> Fase pós-hardening para colocar o projeto em uso real, validar conteúdo final e acompanhar os primeiros dias de operação.

| # | Tarefa | Status |
|---|--------|--------|
| 11.1 | Revisar conteúdo inicial dos dois portais: textos, imagens, SEO e links internos | ⬜ Pendente |
| 11.2 | Criar usuários/grupos reais do admin com permissões por área | ⬜ Pendente |
| 11.3 | Testar fluxos reais: contato, candidatura, newsletter, comentário, login e reset de senha | ⬜ Pendente |
| 11.4 | Executar validação responsiva final em mobile, tablet e desktop nos dois portais | ⬜ Pendente |
| 11.5 | Acompanhar logs, backups e entregas de e-mail nos primeiros dias pós-publicação | ⬜ Pendente |

### Fase 12: UX Operacional do Admin ✅
> Camada operacional sobre Django Admin + Unfold para equipe não técnica gerenciar escola, notícias e sistema sem navegar por telas soltas.

| # | Tarefa | Status |
|---|--------|--------|
| 12.1 | Criar guias autenticados `/admin/guias/escola/`, `/admin/guias/noticias/`, `/admin/guias/gerenciamento/` | ✅ Concluído |
| 12.2 | Adicionar guias na dashboard e na sidebar como entradas principais | ✅ Concluído |
| 12.3 | Criar templates reutilizáveis de cabeçalho, fluxos, checklist, empty states e próximos passos | ✅ Concluído |
| 12.4 | Criar `static/admin/css/admin_ux.css` reaproveitando tokens `.kb-*` e Material Symbols | ✅ Concluído |
| 12.5 | Refinar ModelAdmins com copy contextual, filtros rápidos, abas, radio fields e aviso de formulário não salvo | ✅ Concluído |
| 12.6 | Criar perfis administrativos iniciais: Administrador Escolar, Editor de Notícias, Contratações e Administrador Geral | ✅ Concluído |
| 12.7 | Traduzir e integrar Biblioteca de Mídia à navegação operacional | ✅ Concluído |
| 12.8 | Validar `manage.py check`, `makemigrations --check`, testes automatizados e responsividade em 768px/390px | ✅ Concluído |

#### Validação da Fase 12
- `python manage.py check` → 0 erros; mantém apenas warnings conhecidos do `django-axes`.
- `python manage.py makemigrations --check --dry-run` → sem mudanças pendentes.
- `python -m pytest` → 36 testes passando.
- Browser local validado em desktop, 768px e 390px para dashboard, guias e formulário de artigo.

### Fase 13: Integração de Redes Sociais (Instagram + TikTok) ✅
> App `apps.social`: seção curta na home com botões oficiais e os últimos posts como
> cards próprios (dados do banco, sem embed/scraping). Gestão manual no admin como
> fallback e estrutura pronta para as APIs oficiais via management command + cron.

| # | Tarefa | Status |
|---|--------|--------|
| 13.1 | Models `SocialAccount`/`SocialPost` (constraints, índices, thumbnail otimizada) + signals | ✅ Concluído |
| 13.2 | Campos da seção em `SiteExtension` (`tiktok_url`, `social_section_*`) + migration | ✅ Concluído |
| 13.3 | Admin Unfold com tokens password-like e ações de visibilidade/ativação | ✅ Concluído |
| 13.4 | Seção na home (`social_feed`/`social_post_card`) + view com fallback seguro | ✅ Concluído |
| 13.5 | Services Instagram/TikTok (timeout, erros tratados, token ausente) + `httpx` | ✅ Concluído |
| 13.6 | Command `sync_social_posts` (upsert, preserva visibilidade, resiliente) | ✅ Concluído |
| 13.7 | Testes (modelos, normalização, dry-run sem token, home) + `docs/development/REDES_SOCIAIS.md` | ✅ Concluído |

#### Validação da Fase 13
- `python manage.py check` → 0 erros (apenas warnings conhecidos do `django-axes`).
- `python -m pytest apps/social` → 16 testes passando.
- `python manage.py sync_social_posts --dry-run` → roda sem credenciais, com erro amigável.
- Renovação automática de token implementada (Instagram ≤7d, TikTok ≤1h); falta só conectar as credenciais oficiais (ver REDES_SOCIAIS_CREDENCIAIS.md).

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
13. **Notas temporárias de tarefa** — manter concisas, sem código inline, e limpar após cada fase
14. **Conteúdo escolar por site** — modelos públicos com `ForeignKey(Site)` usam `objects` + `on_site`, constraints por site e queries públicas filtradas por `request.site`

---

## Bugs Resolvidos (Revisão Técnica — Fase 5M)

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
| 2026-02-24 | `INDEX_DASHBOARD` nunca existiu no Unfold — ferramenta externa sugeriu a chave sem validação | Dashboard ficou órfã por dias. Sempre conferir docs oficiais |
| 2026-02-24 | Notas de tarefa cresceram demais com instruções acumuladas | Regra: manter notas curtas, limpar após cada fase, sem blocos de código |
| 2026-02-24 | Dashboard usava Tailwind CDN sobre Tailwind compilado do Unfold → conflitos CSS | Nunca carregar CDN externo sobre framework que já compila Tailwind |

---

## Bugs Encontrados (Revisão Técnica — Fase 7)

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

## Bugs Encontrados (Auditoria Técnica — Fase 8.4)

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

- **Fase:** 12 concluída — UX Operacional do Admin
- **Tarefa ativa:** Nenhuma — guias administrativos, perfis e ModelAdmins operacionais concluídos e verificados
- **Próximo:** Fase 10 (hardening produção)
- **Bloqueios:** Nenhum para Fase 9.1. Warnings conhecidos do `django-axes` permanecem como dívida técnica separada.
- **Última atualização:** 2026-06-10 — Fase 13 (redes sociais) concluída

### Resumo do estado por área:
| Área | Estado | Nota |
|------|--------|------|
| **Portal de Notícias** | 🟢 Funcional + Seguro + Responsivo validado | Bugs corrigidos (8.4), mobile concluído (8.5), refinamento desktop/ultrawide, Turnstile e redes sociais de rodapé segregadas por portal em 2026-06-05 |
| **Dashboard Admin** | 🟢 Funcional + Seguro + UX operacional completa | Dashboard com guias por área, telas orientadas a tarefa, perfis administrativos e biblioteca de mídia em PT-BR |
| **Site da Escola** | 🟢 Funcional + CMS administrável | Home, cards, páginas, equipe, depoimentos, departamentos e vagas integrados ao admin e isolados por site |
| **Redes Sociais** | 🟢 Funcional (manual) + pronto para APIs | App `apps.social`: seção na home, admin de contas/posts, command `sync_social_posts` e services Instagram/TikTok sem scraping. Sincronização automática aguarda credenciais oficiais |
| **Infraestrutura** | 🟢 Hardened | nginx com CSP/headers/rate-limit, Docker non-root, expose vs ports |
| **Segurança** | 🟢 Auditada 2x | 20+ proteções ativas. Nenhum `\|safe` em templates. Bleach centralizado |
