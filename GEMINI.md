# GEMINI.md — Instruções news_portal

> Leia **"Tarefa Atual"** antes de começar. Máximo 3KB — limpar após cada fase concluída.

---

## Convenções Permanentes

- **Estilo:** isort, aspas simples (Python) / duplas (UI), FBV, `select_related`/`prefetch_related`
- **Admin:** `unfold.admin.ModelAdmin`, PT-BR em tudo, `DASHBOARD_CALLBACK`
- **Templates:** `{% url %}`, `{% csrf_token %}`, `loading="lazy"` — **NUNCA `|safe`** → usar `|sanitize_html`
- **Multi-site:** SEMPRE `Article.on_site` / `Page.on_site` (nunca `.objects`) em views/feeds/sitemaps
- **Paginator:** 12 items. HTMX: verificar `request.htmx` → retornar partial
- **Sanitização:** importar APENAS de `apps.common.sanitization` — nunca duplicar listas
- **Segurança:** mensagens de erro genéricas — nunca revelar se email/username/candidatura existe
- **Novo app:** ForeignKey(Site) → `CurrentSiteManager`; conteúdo HTML → sanitizar no `save()`

---

## Tarefa Atual

_Nenhuma tarefa ativa. Aguardando próxima instrução do Claude._

---

## Critérios de Aceite (genéricos)

1. `manage.py check` → 0 erros
2. Zero `|safe` em templates — `grep -r "|safe" templates/`
3. Todo model com `ForeignKey(Site)` tem `on_site = CurrentSiteManager()`
4. Mensagens de validação nunca revelam se dado já existe
5. Conteúdo HTML sanitizado no `save()` do model
