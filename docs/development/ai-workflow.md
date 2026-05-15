# AI Workflow — news_portal

> Referência normativa do projeto. Claude é arquiteto e revisor — coordena, não escreve código bruto.

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.12+ / Django 5.x |
| Database | PostgreSQL 16 |
| Frontend | Django Templates + HTMX + Alpine.js |
| Admin | Django Unfold |
| Static | WhiteNoise |
| Dev | Docker Compose (Django + PostgreSQL + Mailpit) |
| Deploy | Docker Compose prod + Nginx + VPS |

---

## Estrutura de Apps

```
apps/
  common/        — Models abstratos, SiteExtension, context processors, sanitization
  accounts/      — CustomUser, autenticação, permissões (Groups)
  school/        — CMS de páginas, equipe, depoimentos
  hiring/        — Vagas, candidaturas, departamentos
  contact/       — Formulários de contato
  news/          — Artigos, categorias, tags, newsletter, RSS, comentários
  media_library/ — Biblioteca de mídia compartilhada
```

Multi-site via Django Sites Framework. Portais independentes em dados, gerenciados pelo mesmo admin.

---

## Padrões de Código

### Python / Django
- Models herdam de `TimeStampedModel` (timestamps), também de `SEOModel` (conteúdo público)
- Todos os apps em `apps/` registrados como `apps.nome`
- Settings divididas: `base.py`, `development.py`, `production.py`, `test.py`, `local_sqlite.py`
- Imports: stdlib → django → third-party → local (isort order)
- Aspas simples para Python; aspas duplas para strings de UI
- UI e admin **em PT-BR** (fieldsets, actions, help_text, verbose_names)
- **Views:** Function-Based Views (FBV) — padrão consistente
- **Queries:** SEMPRE `select_related`/`prefetch_related` com FK/M2M
- **Admin:** Importar `ModelAdmin` de `unfold.admin` (NUNCA de `django.contrib.admin`)
- **Sanitização:** SEMPRE importar de `apps.common.sanitization` — nunca duplicar listas de tags
- **Segurança:** Mensagens de erro genéricas — nunca revelar se email/username existe
- Models com `ForeignKey(Site)` DEVEM ter `on_site = CurrentSiteManager()`

### Templates
- Base: `base.html`, `base_school.html`, `base_news.html`
- Componentes: `templates/components/`
- Partials HTMX: `templates/<app>/partials/`
- Naming: `snake_case.html`
- Imagens: `loading="lazy"` (exceto hero/above the fold)
- NUNCA usar `|safe` — usar `|sanitize_html` ou `|striptags`
- Links: `{% url %}` (nunca hardcoded)
- Formulários: `{% csrf_token %}` obrigatório

### URLs
- Namespace por app: `school:home`, `news:article_detail`, `hiring:job_list`
- Slugs para URLs públicas
- `<slug:slug>/` SEMPRE como última rota no urlpatterns

### Admin
- `list_display`, `list_filter`, `search_fields`, `prepopulated_fields`
- Fieldsets em PT-BR, organizados logicamente
- Actions com descriptions em PT-BR
- `help_text` em PT-BR para campos que confundem leigos
- Inline admins onde faz sentido
- **Dashboard:** `DASHBOARD_CALLBACK` (NÃO `INDEX_DASHBOARD`) → função callback, template `admin/index.html`
- Sem CDN externo em templates admin — Unfold já compila Tailwind + Material Symbols

### Verificação de libs terceiras
Antes de usar qualquer chave de configuração, conferir na documentação oficial.
- Unfold: https://unfoldadmin.com/docs/configuration/settings/

---

## Checklist de Review

### Models
- [ ] Herda de `TimeStampedModel`/`SEOModel` quando apropriado?
- [ ] `__str__`, `Meta.ordering`, `verbose_name`/`verbose_name_plural` definidos?
- [ ] ForeignKeys com `on_delete`, `related_name`?
- [ ] Campos opcionais: `blank=True` (e `null=True` só para non-string)?
- [ ] `get_absolute_url()` para models com URLs públicas?
- [ ] Models com `ForeignKey(Site)` têm `on_site = CurrentSiteManager()`?

### Admin
- [ ] Usa `unfold.admin.ModelAdmin`?
- [ ] `list_display`, `list_filter`, `search_fields`, `prepopulated_fields` configurados?
- [ ] Fieldsets em PT-BR?
- [ ] Actions com descriptions em PT-BR?
- [ ] Campos com `help_text` em PT-BR?

### Views
- [ ] FBV?
- [ ] 404 para objetos não encontrados?
- [ ] CSRF em formulários?
- [ ] Queries otimizadas (`select_related`/`prefetch_related`)?
- [ ] Paginação (12 items por padrão)?
- [ ] HTMX: verifica `request.htmx` → partial?
- [ ] `F()` para updates atômicos (view_count etc.)?

### Templates
- [ ] Herda base correto?
- [ ] Sem `|safe` — usa `|sanitize_html`?
- [ ] Sem URLs hardcoded?
- [ ] CSRF em formulários?
- [ ] Imagens com `loading="lazy"`?
- [ ] SEO: Open Graph, Twitter Cards, JSON-LD quando aplicável?

### Segurança
- [ ] Mensagens de validação genéricas (não revelam existência de dados)?
- [ ] HTML sanitizado no `save()` do model?
- [ ] `Article.on_site` / `Page.on_site` em views/feeds/sitemaps (nunca `.objects`)?
- [ ] Uploads validam extensão + MIME?
- [ ] Rate limiting para operações custosas?

---

## Decisões Arquiteturais Permanentes

| Decisão | Justificativa |
|---------|--------------|
| Django + PostgreSQL | ORM robusto, admin built-in, Sites framework |
| HTMX + Alpine.js (sem SPA) | SEO nativo, sem build pipeline |
| Django Unfold para admin | UI moderna sem construir painel custom |
| Path-based routing (`/` escola, `/news/` notícias) | Simplicidade, sem config DNS |
| FBV como padrão | Consistência, sem migrar para CBV |
| Busca com Django Q() | Elasticsearch desnecessário para volume escolar |
| `DASHBOARD_CALLBACK` (não `INDEX_DASHBOARD`) | Chave correta do Unfold |
| Template `admin/index.html` sem CDN externo | Unfold já compila Tailwind |
| `unique_together = [['email', 'site']]` para newsletter | Mesmo email pode assinar sites diferentes |
| Bleach centralizado em `apps/common/sanitization.py` | Nunca duplicar listas de tags/attrs |
| Email `unique=True` no CustomUser | Constraint no banco > validação no form |
| `PASSWORD_RESET_TIMEOUT = 3600` | Token de 1h vs 24h default — reduz janela de ataque |
| Mensagens genéricas em autenticação/candidaturas | Previne user enumeration |
| CSP com `unsafe-inline`/`unsafe-eval` | Bloqueia scripts externos sem quebrar HTMX/Alpine |
| `server_name _` no nginx | Catch-all até domínio real ser configurado |

---

## Protocolo de Trabalho com Gemini

### Antes de cada sessão
1. Ler `roadmap.md` para estado atual
2. Atualizar `gemini-task.md` com instruções da próxima tarefa
3. Incluir: arquivos a modificar/criar, critérios de aceite
4. **NÃO incluir blocos de código** — referenciar arquivos existentes

### Depois de cada sessão
1. Revisar código produzido contra critérios de aceite
2. Testar funcionalidade — acessar rotas, verificar renderização
3. Atualizar status no `roadmap.md`
4. **Limpar `gemini-task.md`** — deletar instruções da tarefa concluída

### Regras para `gemini-task.md`
- **Máximo 3KB (~100 linhas)**
- Sem blocos de código inline — referenciar caminhos de arquivos
- Manter apenas: convenções permanentes + tarefa atual + critérios de aceite

---

## Para Adicionar um Novo App

1. Criar `apps/<nome>/` com estrutura padrão (`models.py`, `views.py`, `admin.py`, `urls.py`, `apps.py`, `migrations/`)
2. Registrar em `INSTALLED_APPS` como `'apps.<nome>'`
3. Registrar namespace em `config/urls.py`
4. Se tiver conteúdo multi-site: adicionar `ForeignKey(Site)` + `CurrentSiteManager`
5. Se tiver conteúdo HTML do usuário: sanitizar no `save()` via `apps.common.sanitization`
6. Registrar no admin com todas as convenções PT-BR

---

## Estado Atual

| Área | Estado |
|------|--------|
| Portal de Notícias | Funcional, seguro, auditado 2x |
| Dashboard Admin | Funcional, bilíngue PT/EN |
| Site da Escola | Inacabado — Fase 9 |
| Infraestrutura | Hardened (nginx CSP, Docker non-root) |
| Segurança | Auditada 2x — 20+ proteções ativas |
| Mobile | Fase 8.5 pendente |

**Próximas fases:** 8.5 (mobile) → Fase 9 (escola completa) → Fase 10 (hardening prod)
