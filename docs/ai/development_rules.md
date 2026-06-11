# Regras de Modificação Para Agentes

O sistema está em produção. Aplique mudanças pequenas, verificáveis e alinhadas ao código existente.

## 1. Segurança de HTML e XSS

- Nunca use `|safe` em templates para conteúdo vindo de usuário, admin ou banco.
- Use `{{ value|sanitize_html }}` ou `{{ value|striptags }}` conforme o caso.
- Sanitização de HTML rico deve passar por `apps.common.sanitization`.
- Não duplique listas de tags/atributos permitidos em outros apps.

## 2. Views e Rotas

- O padrão do projeto é Function-Based View. Não introduza Class-Based Views.
- Use `@require_GET`, `@require_POST` ou validação explícita de método quando aplicável.
- Views públicas devem usar `get_object_or_404()` e respostas controladas, não `Model.objects.get()` exposto a erro 500.
- A rota raiz da escola é catch-all; novas rotas específicas precisam vir antes de `path('', include('apps.school.urls', ...))`.

## 3. Sites Framework

- Hoje `SITE_ID = 1`; Komuniki e Blog da Kelly são separados por path/domínio, não por dois `Site` ativos.
- Mesmo assim, models públicos com `on_site` devem usar `Model.on_site` em views, feeds e sitemaps.
- `Model.objects` fica para admin, migrations, comandos internos e tarefas administrativas.

## 4. Banco e ORM

- Mudou model? Gere migration e revise o diff.
- Queries com FK/M2M em views devem usar `select_related()` e/ou `prefetch_related()`.
- Contadores e incrementos devem usar `F()` quando possível.
- Não faça mudanças que dependam de Celery/Redis sem decisão explícita; a newsletter atual usa comando/ação admin.

## 5. Admin e PT-BR

- Admins devem herdar de `unfold.admin.ModelAdmin`.
- Textos visíveis no admin devem estar em PT-BR claro.
- `help_text`, `verbose_name`, `fieldsets` e mensagens precisam ser legíveis por pessoas não técnicas.
- Não use `INDEX_DASHBOARD`; o Unfold atual usa `DASHBOARD_CALLBACK`.

## 6. Frontend Público

- Não adicione Tailwind CDN, bibliotecas JS externas ou bundlers sem aprovação explícita.
- HTMX e Alpine.js são os controladores dinâmicos permitidos.
- Links em templates devem usar `{% url %}` quando forem rotas internas.
- Imagens abaixo da primeira dobra devem usar lazy loading quando aplicável.

## 7. Produção e Deploy

- Deploy canônico: GitHub workflow manual `Deploy Production` → aprovação do environment `production` → tag `production-approved` → timer da VPS.
- Caminho de produção: `/opt/kelly_sys`.
- Compose project: `kellysys`.
- Antes de mexer em deploy, leia `docs/technical/go-live-checklist.md` e `docs/technical/secure-deploy.md`.

## 8. Documentação

- Não documente como existente um recurso que não está confirmado em fonte versionada.
- Se remover ou mover docs, atualize `README.md`, `docs/README.md` e o índice da pasta afetada.
- Manuais de usuário devem descrever apenas fluxos operacionais disponíveis hoje.
- Arquivos locais de agente na raiz (`AGENTS.md`, `CLAUDE.md`, `gemini.md`) são ignorados pelo git e podem ficar vazios. A fonte versionada para agentes é `docs/ai/`.

## 9. Checklist Antes de Entregar

- [ ] `rg` não encontra links para a pasta antiga de documentação.
- [ ] Links locais da documentação passam.
- [ ] Mudanças técnicas e documentação estão consistentes.
- [ ] Testes relevantes foram executados ou a limitação foi declarada.
