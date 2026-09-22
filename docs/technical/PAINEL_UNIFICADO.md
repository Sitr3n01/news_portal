# Painel administrativo unificado ("Newsroom")

O Django admin (Unfold) e o Wagtail passaram a funcionar como **um único painel**: a mesma sidebar, a mesma topbar, a mesma paleta e a mesma tipografia nas três superfícies administrativas, com uma visão geral central em `/painel/`.

Contrato visual: a prévia aprovada `newsroom_dashboard_referencia.html`, inspirada na dashboard da Dub (https://dub.co/). As medidas foram escaladas cerca de 1,17× para uso real (a prévia foi desenhada num quadro compacto, com texto-base de 12px), preservando proporções, cores, raios e composição.

![Referência aprovada (acima) e implementação (abaixo), na mesma área de 1180 × 750](../assets/screenshots/painel-unificado/comparativo-referencia-x-implementacao.jpg)

---

## 1. Arquitetura em uma frase

**A porta continua em `apps/accounts/panels.py`; a mobília mora em `apps/common/newsroom/`.** Quem pode entrar em qual área não mudou. O que mudou é o que a pessoa vê depois de entrar: uma casca única, renderizada no servidor, usada por:

| Superfície | Como recebe a casca |
|---|---|
| Visão geral `/painel/` | `templates/newsroom/base.html` (FBV `apps.common.newsroom.views.dashboard`) |
| Wagtail `/cms/...` | `templates/wagtailadmin/base.html` estende o `base.html` do Wagtail (mecanismo documentado) e troca **só** a sidebar React pela sidebar do painel |
| Django admin `/admin/...` | `templates/admin/nav_sidebar.html` e `templates/unfold/helpers/header.html` trocam a sidebar e o cabeçalho do Unfold |

As três usam as mesmas inclusion tags (`apps/common/templatetags/newsroom.py`): `{% newsroom_sidebar %}`, `{% newsroom_topbar %}` / `{% newsroom_admin_topbar %}` e `{% nr_icon %}`.

### Módulos

| Arquivo | Responsabilidade |
|---|---|
| `apps/common/newsroom/branding.py` | Identidade configurável (`settings.NEWSROOM`): nome, marca e rótulos dos espaços de trabalho |
| `apps/common/newsroom/workspaces.py` | Espaços de trabalho (Blog da Kelly, Komuniki) e chave de sessão |
| `apps/common/newsroom/navigation.py` | **Registro único da navegação** e das regras de visibilidade |
| `apps/common/newsroom/dashboard.py` | Consultas da visão geral (indicadores, listagem, atividade, atalhos) |
| `apps/common/newsroom/views.py` | FBVs: visão geral, troca de espaço e os redirecionamentos de `/cms/` e `/admin/` |
| `apps/news/editorial.py` | Regras editoriais compartilhadas (contagens, estado de cada notícia, filtros). Antes viviam só no dashboard do Wagtail |
| `apps/news/wagtail_moderation.py` | Comentários e newsletter no Wagtail (ver §6) |
| `apps/common/dashboard.py` | Saúde do envio de e-mails/newsletter e guias de operação (antes era o `DASHBOARD_CALLBACK`) |

### Identidade configurável

```python
# config/settings/*.py — tudo opcional; ausente = padrão de branding.py
NEWSROOM = {
    'BRANDING': {'NAME': 'news', 'NAME_SUFFIX': 'room', 'MARK': 'n.', 'PRODUCT_NAME': 'Newsroom'},
    'WORKSPACES': {'komuniki': {'label': 'Komuniki', 'initial': 'Ko', 'tone': 'green'}},
}
```

---

## 2. Rotas

| Rota | Nome | Comportamento |
|---|---|---|
| `/painel/` | `panel:dashboard` (e `panel:picker`, mantido como alias) | Visão geral. Porta: `panels.available_panels(user)` não vazio; sem área → `panel:no_access` |
| `/painel/espaco/` | `panel:workspace` | `POST` com CSRF. Só aceita espaços que a pessoa enxerga |
| `/cms/` | `wagtailadmin_home` (inalterado) | Redireciona para `/painel/` **atrás de `require_admin_access`** — quem não alcança o Wagtail recebe a mesma resposta de antes |
| `/admin/` | `admin:index` (inalterado) | Redireciona para `/painel/` **atrás de `admin.site.admin_view`** — mesma porta de antes |

- **Destino pós-login** (`panels.post_login_target`): `next` seguro > painel escolhido no formulário (se permitido) > **visão geral para quem alcança ao menos uma área** > portal público. Antes, quem tinha uma área só entrava direto nela, e quem tinha duas via a tela de escolha. Essa tela (`panel_picker` + `templates/auth/panel_picker.html`) foi removida: a escolha virou a própria navegação.
- Nenhum nome de rota existente foi removido nem mudou de endereço.

---

## 3. Espaços de trabalho

Os dois portais compartilham o mesmo `Site` (`SITE_ID = 1`) e se separam por app. O espaço de trabalho é, portanto, um **recorte** da navegação, dos indicadores, da listagem e da atividade:

- **Blog da Kelly:** notícias, revisão, mídia do Wagtail, comentários, newsletter, categorias, tags e home do portal.
- **Komuniki:** mensagens de contato, página Cursos, home e blocos da Komuniki, redes sociais e biblioteca de arquivos legada.
- **Administração** (usuários, permissões, configurações) aparece nos dois.

O seletor também traz **“Ver <espaço> no ar”**, que abre o portal público (`KELLY_BLOG_PUBLIC_URL` / `KOMUNIKI_PUBLIC_URL`) e substitui o antigo grupo “Visualizar Portais” do Unfold e o “Ver portal” do dashboard do Wagtail. Um espaço só é oferecido a quem enxerga alguma ferramenta dele. A escolha fica na sessão, mas **a tela aberta vence**: abrir `/admin/contact/...` mostra a navegação da Komuniki mesmo com o Blog escolhido. Espaço de trabalho não é autorização. Cada tela continua checando a própria permissão.

![Espaço Komuniki](../assets/screenshots/painel-unificado/espaco-komuniki.jpg)

---

## 4. Navegação: uma fonte de verdade

Cada item de `navigation.NAV_ITEMS` delega a visibilidade à **mesma checagem que a tela de destino aplica**:

| Destino | Regra de visibilidade |
|---|---|
| Tela do Django admin | `panels.can_access_admin` (porta do `/admin/`) + `ModelAdmin.has_view_or_change_permission` (checagem do changelist) |
| Snippet do Wagtail | `panels.can_access_cms` (porta do `/cms/`) + `viewset.permission_policy.user_has_any_permission(add/change/delete/view)` (a regra do IndexView) |
| Imagens e documentos | `panels.can_access_cms` + `permission_policy` do Wagtail (a regra do `ImagesMenuItem`/`DocumentsMenuItem`, incluindo coleções) |
| "Revisão e auditoria" | Itens do `reports_menu`/`settings_menu` do próprio Wagtail, filtrados pelo `is_shown` deles |
| "Recursos guardados" | Superusuário + checagem do `ModelAdmin`, como era no menu do Unfold |

Assim o menu nunca promete uma tela que a tela recusa. E esconder um item não protege nada: as views continuam checando no backend (há testes para isso).

- `UNFOLD['SIDEBAR']['navigation']` ficou vazio: um segundo menu seria uma segunda fonte de verdade.
- Selos: total de notícias (neutro), e em revisão, comentários pendentes e mensagens novas (alerta, só com contagem > 0). Uma consulta `COUNT` por selo, e só para quem vê o item.
- Ocultos do menu, mas acessíveis por URL a quem tem permissão: relatórios e sites de **páginas** do Wagtail (o projeto não usa a árvore de páginas) e a tela de **Usuários do Wagtail**. Esta última porque editar conta por ela pularia a sincronização cargo → grupo feita em `apps/accounts/admin.py::save_related`.

---

## 5. Visão geral

A composição segue a referência: cabeçalho e ação principal, indicadores num contêiner dividido, seção central, ferramentas de busca e filtro, listagem, acesso rápido e atividade recente.

| Bloco | Fonte real |
|---|---|
| Publicadas / Rascunhos / Em revisão | `apps.news.editorial.article_status_counts()` (a mesma contagem do antigo dashboard "Redação") |
| Notas dos indicadores | `published_at` nos últimos 30 dias, `updated_at` de hoje, `WorkflowState` ativo, `Comment.is_active=False` |
| Mensagens novas / Em atendimento (Komuniki) | `ContactInquiry.status` |
| Blocos ativos / Posts visíveis (Komuniki) | `SchoolFeature` (posição de confiança), `SocialPost.is_visible`, `SocialAccount.is_active` |
| Atividade (Blog) | `wagtail.models.ModelLogEntry` das notícias + comentários recebidos |
| Atividade (Komuniki) | `django.contrib.admin.models.LogEntry` dos modelos que a pessoa pode ver + mensagens recebidas |
| Saúde do envio | `apps.common.dashboard.build_system_health` (detalhes técnicos só para superusuário) |

**Nenhum número é inventado.** O "↗ 12,8%" da prévia não tem fonte no sistema e não foi reproduzido. "Analytics" e o sino de notificações também ficaram de fora, porque não existe funcionalidade real correspondente (ver §10).

### Listagem

- Paginação, busca (título; na Komuniki, nome, e-mail ou curso), abas de estado e categoria são feitas **no servidor** (`Paginator`, 10 por página). Há teste garantindo que o número de consultas não cresce com a quantidade de linhas.
- HTMX (já vendorizado em `static/js/vendor/htmx.min.js`): a busca, as abas e a paginação trocam só a região de resultados (`#nr-results`) e as abas (`hx-select-oob`). O campo de busca nunca é substituído, então foco e texto digitado não se perdem. Sem JavaScript, tudo funciona como formulário GET comum.
- Lista e grade usam os mesmos dados. A preferência fica na URL (`?view=grid`) e no `localStorage`.
- Estado de cada linha: Em revisão > Agendada > Publicada / Arquivada / Rascunho. "Alterações não publicadas" aparece quando a versão no ar tem revisão mais nova.
- A miniatura reaproveita `Article.card_image_url` (rendition `fill-600x400` já gerada para o portal) com as renditions pré-carregadas. Sem imagem, aparece um placeholder na paleta, com tom por categoria.

### Ações: sempre as nativas

Criar, editar, revisar, despublicar, histórico e excluir são **links para as views oficiais** do `ArticleSnippetViewSet` (`wagtailsnippets_news_article:add/edit/history/unpublish/delete`). Publicar e aprovar/rejeitar revisões acontecem no editor do Wagtail (menu de ações e fluxo de trabalho). A visão geral nunca altera `status`, `live` ou revisões. Cada ação só aparece para quem tem a permissão correspondente, e a view de destino confere de novo.

---

## 6. Migração progressiva para o Wagtail

**Comentários, assinantes e entregas da newsletter** ganharam telas no Wagtail (`SnippetViewSet` em `apps/news/wagtail_moderation.py`).

Motivo concreto: o cargo *Editor de Notícias* recebe as permissões `news.*_comment` e `news.*_newsletter*` (`admin_roles.py`), mas **não é `is_staff`**, então nunca alcançou essas telas, que só existiam no `/admin/`. No Wagtail elas ficam atrás da porta que o editor já usa (`access_admin`) e das mesmas permissões de modelo. Nenhuma permissão nova foi concedida.

Paridade com o Django admin:

| Recurso | Django admin | Wagtail |
|---|---|---|
| Criar registro à mão | Não | Não (política sem `add`, inclusive para superusuário) |
| Texto do comentário / dados da inscrição | Somente leitura | Somente leitura (`FieldPanel(read_only=True)`) |
| Aprovar/ocultar comentários em lote | Action | Ação em massa "Aprovar"/"Ocultar" |
| Reativar/desativar inscrições em lote | Action | Ação em massa "Reativar"/"Desativar" |
| Entregas da newsletter | Somente leitura | Somente leitura (inspeção; política sem `add`/`change`) |
| Exportar e-mails em CSV | Superusuário, com neutralização de fórmulas (`_csv_safe`) | **Não habilitado**: a exportação nativa do Wagtail não neutraliza fórmulas |

As telas do Django admin **continuam registradas** (nada foi removido). Na navegação, a exportação aparece em "Recursos guardados › Exportar assinantes (CSV)".

![Comentários no Wagtail](../assets/screenshots/painel-unificado/comentarios-no-wagtail.jpg)

---

## 7. O que permanece no Django admin (exceções documentadas)

Continuam no Unfold, **dentro da mesma casca**, porque a migração traria risco sem ganho funcional:

| Tela | Por que fica |
|---|---|
| Usuários (`CustomUserAdmin`) | Formulário do `UserAdmin` (senha, `usable_password`) + sincronização cargo → grupo em `save_related` |
| Grupos e permissões | Editor de permissões do `GroupAdmin` |
| Komuniki: página Cursos, Home, Blocos, Depoimentos | Formulários com campos bilíngues, fieldsets condicionais por superusuário e querysets restritos (`PageAdmin.get_queryset`, `get_fieldsets`) |
| Mensagens de contato | Fila de atendimento com ações e campos somente leitura; o cargo que a usa (Admin Komuniki) já é `is_staff` |
| Redes sociais | `SocialAccountAdminForm` trata tokens como senha (nunca reexibe; em branco mantém o atual) |
| Biblioteca de mídia legada (`media_library`) | Otimização de imagem no upload (`_optimize_image_field`) |
| Vagas, candidaturas, curtidas, favoritos, códigos de verificação, identidades Google | Recursos guardados / trilhas de auditoria, só superusuário |
| Guias de operação (`/admin/guias/...`) | Páginas-tutorial do admin |

O Unfold **não foi removido**: seus formulários, filtros, ações e abas continuam em uso. Ele recebeu a paleta do painel (`UNFOLD['COLORS']`, tema claro) e a casca comum.

![Django admin dentro da casca](../assets/screenshots/painel-unificado/django-admin-na-casca.jpg)

---

## 8. Tema, design system e acessibilidade

- **Tokens:** `static/newsroom/css/newsroom.css` (prefixo `nr-`) é a fonte única de cor, raio, medida e fonte (Inter variável local, `static/fonts/editorial/`, sem CDN). Ícones: sprite local `static/newsroom/icons.svg`.
- **Wagtail:** `static/newsroom/css/newsroom-wagtail.css`, via hook oficial `insert_global_admin_css`, mapeia os tokens `--w-color-*` (mecanismo documentado de marca do Wagtail) para a paleta. Só o raio de botões e campos é ajustado. Editor de blocos, seletores de mídia, painéis de publicação e fluxos de revisão continuam com o CSS nativo.
- **Unfold:** `UNFOLD['COLORS']` (cinzas neutros; "primária" em `#171717`, botões pretos como na referência), `THEME='light'` e `static/newsroom/css/newsroom-unfold.css`. Os tokens do design system `kb-` (guias e ajudas contextuais) foram convertidos do tema escuro para a paleta clara.
- **Tema único (claro):** a referência é clara, e o projeto já forçava um tema só (o Unfold era forçado no escuro). No Wagtail, o bloco de tokens vale também para `.w-theme-dark`/`.w-theme-system`. Sem isso, quem usa o sistema operacional no modo escuro veria o Wagtail escuro e a visão geral clara.
- **Contraste:** o texto mais claro é `#737373` (4,7:1 sobre branco). Os cinzas mais claros da prévia (`#a3a3a3`, `#929292`) ficaram só para ícones e divisórias.
- **Responsivo:** a partir de 1024px, a sidebar é fixa (224px). Abaixo disso, vira gaveta com os mesmos rótulos: botão com `aria-expanded`, fundo escurecido, Esc fecha e o foco volta ao botão. A barra de indicadores passa a 2 × 2 no celular, e as listagens do Wagtail rolam dentro da própria área (sem rolagem horizontal da página).
- **Teclado e leitores de tela:** link "Pular para o conteúdo", `aria-current` no item ativo, rótulos acessíveis em botões só com ícone, menus em `<details>` (acessíveis sem JavaScript), anel de foco azul e `prefers-reduced-motion` respeitado.
- **Isolamento:** nada disso é carregado pelos portais públicos. Os templates e o CSS públicos não foram tocados.

![Gaveta no celular — Wagtail e Django admin](../assets/screenshots/painel-unificado/gaveta-celular-wagtail-e-admin.jpg)

---

## 9. Segurança e compatibilidade

- Nenhum novo sistema de login, modelo de usuário, backend, grupo ou permissão. **Sem migrations.**
- Autenticação ≠ autorização: `/painel/` exige área administrativa. Leitor autenticado vai para "sem acesso". Os redirecionamentos de `/cms/` e `/admin/` estão atrás das portas originais de cada framework.
- Troca de espaço de trabalho: só `POST` com CSRF, só para espaços visíveis, e o redirecionamento é para um destino fixo (sem `next` arbitrário).
- "Sair" envia `POST` para `panel:logout` com `next` fixo em `panel:login`: encerra a sessão das três áreas.
- Parâmetros de listagem validados (`status` numa lista fechada, categoria numérica, busca limitada a 100 caracteres). Tudo é renderizado com escape automático, sem `|safe`.
- Consultas da visão geral sempre filtradas pela mesma regra de visibilidade da navegação. O admin da Komuniki não recebe dados de notícias, nem pela URL.

---

## 10. Testes

- `apps/common/test_newsroom.py` (45 testes): login e redirecionamento, acesso e recusa, portas de `/cms/` e `/admin/`, navegação por cargo, isolamento entre espaços, busca, filtros e paginação no servidor, número de consultas constante, lista × grade, links de criação/edição, ações por permissão, reflexo de rascunho/revisão/publicação/arquivamento, agendamento, casca nas telas do Wagtail e do admin (e ausência dela em popups), logout, moderação no Wagtail (inclusive recusas), dados reais nos indicadores, auditoria e rotas preservadas.
- Testes existentes atualizados onde o comportamento mudou de propósito (destino pós-login, páginas iniciais antigas, painéis "Redação"). Cada um mantém a garantia original no endereço novo.
- Validação visual com Chromium (Playwright) em 1440, 1280, 834 e 390px, com interação real: busca HTMX, abas, grade, paginação, menus, gaveta e troca de espaço.

---

## 11. Limitações e pendências

- **Cabeçalho do Wagtail:** as telas do Wagtail mantêm o cabeçalho nativo (trilha, ações, painéis laterais de status, pré-visualização e comentários), com a paleta do painel. Ele não mostra o espaço de trabalho na trilha, como a topbar da visão geral e do admin. Substituí-lo quebraria controles essenciais do editor.
- **Preferência de tema do Wagtail:** a opção "Tema" em *Minha conta* fica sem efeito visual, porque o painel adota o tema claro. O Wagtail não oferece hook para retirar essa opção.
- **Textos em inglês do Unfold** ("Type to search", "Filters") e alguns rótulos de campo em inglês ("Created at") são anteriores a esta mudança.
- **Analytics:** existe `Article.view_count`, mas não há tela de analytics. Uma seção "Mais lidas" seria o próximo passo natural, com dados reais.
- **Notificações:** não há notificações dentro do sistema (as do Wagtail são por e-mail), por isso não há sino.
- **Migrações futuras candidatas ao Wagtail** (`ModelViewSet`/`SnippetViewSet`): mensagens de contato e posts de redes sociais, preservando ações e campos sensíveis.

---

## 12. Manutenção e reversão

- **Ao atualizar o Wagtail:** comparar `templates/wagtailadmin/base.html` com o `base.html` do Wagtail (o bloco `furniture` é cópia fiel) e conferir se o bloco escuro de `core.css` ganhou tokens novos.
- **Ao atualizar o Unfold (pinado em 0.87.0):** conferir `admin/base.html` (inclusão de `admin/nav_sidebar.html` e `unfold/helpers/header.html`).
- **Reversão:** toda a mudança está na branch da reformulação. Não há migration, então reverter o merge restaura o comportamento anterior sem tocar em dados.

![Visão geral no desktop](../assets/screenshots/painel-unificado/visao-geral-desktop.jpg)
