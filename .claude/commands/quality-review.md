---
allowed-tools: Bash(gh pr view:*), Bash(gh pr diff:*), Bash(gh pr comment:*), Bash(gh pr list:*), Bash(gh issue view:*), Bash(gh api:*), Bash(gh repo view:*), Bash(git log:*), Bash(git diff:*), Bash(git show:*), Bash(git blame:*), Bash(git rev-parse:*), Bash(git merge-base:*)
argument-hint: "[<PR#> | local]"
description: Quality review do news_portal com base no checklist do ai-workflow.md
disable-model-invocation: false
---

Você é o revisor de qualidade do projeto **news_portal**. Realize uma revisão especializada das regras de `docs/development/ai-workflow.md` deste repositório (PT-BR, Unfold, multi-site, sanitização, FBV).

## Modo de operação

A partir de `$ARGUMENTS`:

- Se `$ARGUMENTS` é um número inteiro → **modo PR**: use `gh pr view $ARGUMENTS --json number,title,state,isDraft,baseRefName,headRefName,headRefOid,comments,author` e `gh pr diff $ARGUMENTS` para coletar o diff.
- Se `$ARGUMENTS` é `local` ou está vazio → **modo local**: detecte a base com `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name`, então use `git diff origin/<base>...HEAD` para o diff e `git rev-parse HEAD` para o SHA. Use `git log origin/<base>..HEAD` para a lista de commits.

Anote o SHA do head para usar nos links de citação mais tarde — você precisará dele em todos os links Markdown.

## Passos

1. **Gate de elegibilidade (somente modo PR)**: lance um Haiku agent para conferir se o PR (a) está fechado, (b) é draft, (c) é trivialmente OK (PR automatizado, mudança óbvia e mínima), ou (d) já tem um comentário de quality review meu anterior (cabeçalho `### Quality review (news_portal)`). Se qualquer condição for verdadeira, **não prossiga** — informe ao usuário e encerre.

2. **Coleta de regras**: lance um Haiku agent para retornar os caminhos (não o conteúdo) dos arquivos normativos relevantes: `docs/development/ai-workflow.md` (regras do projeto) e qualquer `CLAUDE.md` em diretórios cujos arquivos foram modificados.

3. **Sumário da mudança**: lance um Haiku agent para ler o PR/diff e retornar um sumário curto em PT-BR (1-3 frases) do que está sendo alterado.

4. **Cinco Sonnet agents em paralelo** — cada um retorna uma lista de issues com (a) descrição curta, (b) arquivo + range de linhas, (c) motivo (qual regra do ai-workflow.md ou bug). Lance todos no mesmo turno, em um único bloco de tool calls:

   **Agent #1 — Models & Schema** (`apps/**/models.py`):
   - Models herdam de `apps.common.models.TimeStampedModel`? Models de conteúdo público herdam também de `SEOModel`?
   - `__str__`, `Meta.ordering`, `verbose_name` e `verbose_name_plural` definidos?
   - Toda `ForeignKey` tem `on_delete` explícito e `related_name`?
   - Campos opcionais usam `blank=True`? `null=True` aparece **apenas** em non-strings?
   - Models com URLs públicas têm `get_absolute_url()`?
   - **Crítico**: models com `ForeignKey(Site)` declaram `on_site = CurrentSiteManager()`?
   - Sanitização HTML acontece no `save()` via `apps.common.sanitization` (nunca duplicar listas de tags)?

   **Agent #2 — Admin (Unfold + PT-BR)** (`apps/**/admin.py`, `templates/admin/**`):
   - Importa `ModelAdmin` de `unfold.admin` (NUNCA de `django.contrib.admin`)?
   - `list_display`, `list_filter`, `search_fields`, `prepopulated_fields` configurados?
   - Fieldsets, actions e `help_text` **em PT-BR**?
   - Dashboard usa chave `DASHBOARD_CALLBACK` (NÃO `INDEX_DASHBOARD`)?
   - Templates admin **sem CDN externo** (Unfold compila Tailwind + Material Symbols)?

   **Agent #3 — Views, URLs & Templates** (`apps/**/views.py`, `apps/**/urls.py`, `templates/**`):
   - Views são **FBV** (não CBV)?
   - Queries com FK/M2M usam `select_related`/`prefetch_related`?
   - Views HTMX checam `request.htmx` e retornam partial em `templates/<app>/partials/`?
   - `F()` em updates atômicos (`view_count` etc.)?
   - 404 para objetos não encontrados (via `get_object_or_404`)?
   - Paginação onde aplicável (12 itens default)?
   - URLs usam namespace por app (`school:`, `news:`, `hiring:`); `<slug:slug>/` é a **última** rota?
   - Templates: **nunca `|safe`** — sempre `|sanitize_html` ou `|striptags`?
   - `{% url %}` em todos os links (sem hardcode); `{% csrf_token %}` em todo `<form>`?
   - Imagens com `loading="lazy"` (exceto hero/above-the-fold)?

   **Agent #4 — Segurança & Multi-site**:
   - Mensagens de erro/validação em auth e candidaturas são **genéricas** (não revelam se email/username existe)?
   - HTML sanitizado SEMPRE via `apps.common.sanitization` no `save()` do model?
   - Querysets de conteúdo multi-site usam `Article.on_site` / `Page.on_site` em views/feeds/sitemaps (nunca `.objects`)?
   - Uploads validam extensão **e** MIME?
   - Operações custosas têm rate limiting?
   - Newsletter mantém `unique_together = [['email', 'site']]`?
   - Settings preservam `PASSWORD_RESET_TIMEOUT = 3600` (não 24h default)?
   - CSP não regrediu (sem novo `unsafe-*` adicionado)?

   **Agent #5 — Histórico & comentários de PR**:
   - Para cada arquivo modificado, rode `git blame` nas linhas tocadas e identifique se o autor original adicionou guidance que está sendo violada agora.
   - Liste os 3 PRs mais recentes que tocaram esses arquivos (via `gh pr list --state merged --search "<filepath>"` ou `gh api repos/Sitr3n01/news_portal/commits?path=<filepath>&per_page=5`), e veja se há review comments antigos relevantes (`gh api repos/Sitr3n01/news_portal/pulls/<n>/comments`).
   - Verifique comentários de código (`# `, `<!-- -->`, docstrings) nos arquivos modificados — alguma guidance ali contraria a mudança?

5. **Confidence scoring**: para cada issue agregada dos 5 agents, lance em paralelo um Haiku agent que recebe (PR/diff context, descrição da issue, lista de regras do passo 2) e atribui uma nota 0-100. Para issues motivadas por ai-workflow.md, o agent deve **verificar literalmente** que a regra invocada está escrita lá. Rubrica (passar **verbatim** ao agent):
   - **0**: Falso positivo óbvio, ou issue pré-existente fora do diff.
   - **25**: Talvez seja real, talvez não. Estilo não explicitamente normado pelo ai-workflow.md.
   - **50**: É real, mas é nitpick ou raro na prática.
   - **75**: Alta confiança. Issue real que vai impactar funcionamento, OU regra mencionada literalmente no ai-workflow.md.
   - **100**: Certeza absoluta. Evidência direta no diff confirma.

6. **Filtro**: descarte issues com score `< 80`. Se sobrar zero, vá direto para o passo 8 com a saída "nenhum problema".

7. **Re-check de elegibilidade (somente modo PR)**: lance novamente o Haiku do passo 1. Se o PR fechou/virou draft no meio do caminho, encerre sem postar.

8. **Saída**:

   **Modo PR**: use `gh pr comment <n> --body "$(cat <<'EOF' ... EOF)"` para postar. Formato:

   ```markdown
   ### Quality review (news_portal)

   Encontrei N problema(s):

   1. <descrição curta em PT-BR> (ai-workflow.md: "<citação literal da regra>")

   <link https://github.com/Sitr3n01/news_portal/blob/<SHA-COMPLETO>/<arquivo>#L<a>-L<b>>

   2. ...

   🤖 Gerado com [Claude Code](https://claude.ai/code)

   <sub>Útil? Reaja com 👍. Caso contrário, 👎.</sub>
   ```

   Ou, se zero problemas:

   ```markdown
   ### Quality review (news_portal)

   Nenhum problema encontrado. Revisei contra o checklist do ai-workflow.md.

   🤖 Gerado com [Claude Code](https://claude.ai/code)
   ```

   **Modo local**: imprima exatamente o mesmo conteúdo no chat, **sem chamar `gh pr comment`**.

## Regras de link (críticas)

- Use **sempre o SHA completo** (não use `$(git rev-parse HEAD)` literal dentro de Markdown — substitua pelo SHA).
- Formato: `https://github.com/Sitr3n01/news_portal/blob/<SHA>/<path>#L<start>-L<end>`
- Inclua pelo menos 1 linha de contexto antes e depois da linha problemática.

## Falsos positivos a ignorar

- Issues pré-existentes (linhas fora do diff).
- Erros que linter/typechecker/CI pegariam (imports, tipos, formatação).
- Nitpicks não citados no `ai-workflow.md`.
- Mudanças intencionais relacionadas ao escopo do PR.
- Problemas em arquivos do diff mas em linhas **não** modificadas pelo usuário.
- Cobertura de testes ausente (a menos que `ai-workflow.md` exija explicitamente).

## Observações finais

- Faça um todo list antes de começar.
- **Não** rode `manage.py check` ou tente buildar o app — CI cuida disso.
- Use `gh` para qualquer interação com GitHub (nunca WebFetch).
- Toda citação do ai-workflow.md deve ser **literal** — não parafraseie a regra.
