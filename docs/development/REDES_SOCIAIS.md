# Redes Sociais (Instagram + TikTok)

> App `apps.social`. Integração de redes sociais da Komuniki: uma seção curta na
> home com botão oficial do Instagram e os últimos posts como **cards próprios**
> (dados salvos no banco). **Nunca usa scraping nem embeds pesados** e a home **não
> quebra** se as APIs falharem. O TikTok permanece no backend (contas, posts e
> sincronização), mas o botão do TikTok foi removido da home.

---

## Visão geral

A seção da home tem duas fontes de conteúdo, nesta ordem de prioridade:

1. **Gestão manual no admin** (fallback que já funciona sem credenciais) — a Kelly
   cadastra posts à mão em *Posts de Redes Sociais*.
2. **Sincronização automática** com as APIs oficiais (Instagram Graph API e TikTok
   Display API) via `manage.py sync_social_posts`, normalmente agendada por cron.

Os posts vêm do banco e são renderizados como cards próprios (`templates/components/
social_feed.html` + `social_post_card.html`). Não há `<iframe>` de Instagram/TikTok,
então **a CSP não precisa ser afrouxada** (a política já permite imagens `https:`).

---

## Modelos

| Modelo | Papel |
|--------|-------|
| `SocialAccount` | Perfil oficial (Instagram/TikTok) de um `Site`. Guarda links públicos e, opcionalmente, credenciais de API. Tem `objects` + `on_site`. |
| `SocialPost` | Publicação salva no banco (manual ou sincronizada). Único por `(platform, external_id)`; índices em `platform`, `published_at`, `is_visible`. |

`SiteExtension` ganhou: `tiktok_url`, `social_section_enabled`, `social_show_instagram`,
`social_show_tiktok`, `social_section_title` (+ `_en`) e `social_section_subtitle` (+ `_en`).
Os três toggles (`social_section_enabled`, `social_show_instagram`, `social_show_tiktok`)
são editados no topo de **Posts de Redes Sociais** (não na tela de Configuração do Site).

A miniatura do card segue a ordem: **imagem enviada** (`thumbnail_image`, otimizada via
o validador único do projeto) → **URL** (`thumbnail_url`) → **placeholder** (a home
nunca quebra com miniatura vazia).

---

## Como configurar (admin)

1. **Contas de Redes Sociais → Adicionar:** escolha o site e a plataforma, dê um nome
   de exibição, informe o usuário e o link público do perfil. Deixe a conta **ativa**.
2. **Ligar/desligar (toggles):** no **topo de "Posts de Redes Sociais"** há 3 switches —
   *Exibir a seção de redes na home* (liga/desliga tudo), *Exibir Instagram* (botão + posts)
   e *Exibir TikTok* (posts) — e o botão **Salvar exibição**. Desligado, o site fica sem
   aquela parte. O **título/subtítulo** da seção ficam em *Configuração do Site → "Seção de
   redes na home — textos"*. Em *Analytics e Redes Sociais*, preencha o **Instagram**
   (alimenta o botão). O `tiktok_url` permanece no backend, mas **não há botão do TikTok na home**.
3. **Posts de Redes Sociais → Adicionar** (uso manual): escolha a conta (a plataforma é
   automática), cole o link público do post, a data de publicação, a legenda e **envie
   uma imagem** de miniatura (ou cole a URL). Mantenha *Visível no site* marcado.

A home mostra **até 6 posts** visíveis de contas ativas, do mais recente para o mais
antigo, misturando Instagram e TikTok — grade 3×2 no desktop e os **3 primeiros no
celular** (os demais ficam ocultos em telas pequenas).

---

## Sincronização automática

### Credenciais (tokens)

- **Passo a passo completo de como obter as credenciais:** veja
  [REDES_SOCIAIS_CREDENCIAIS.md](REDES_SOCIAIS_CREDENCIAIS.md).
- Os tokens ficam em `SocialAccount` (campos *password-like*: nunca são reexibidos no
  admin; deixar em branco mantém o valor atual). O segredo do app TikTok
  (`TIKTOK_CLIENT_KEY`/`TIKTOK_CLIENT_SECRET`) vem do `.env`.
- **Nunca** versione tokens. Prefira injetá-los por variável de ambiente no servidor e
  registrá-los uma única vez no admin, em conexão segura (HTTPS).
- Sem credenciais, a sincronização **não quebra**: registra um erro amigável em *Erro da
  última sincronização* e segue para a próxima conta.
- **Renovação automática:** o comando renova o token antes de expirar — Instagram quando
  faltam ≤ 7 dias (token de 60 dias), TikTok quando falta ≤ 1 hora (usando o
  `refresh_token` + segredo do app). Mantenha `token_expires_at` preenchido ao conectar.

### Comando

```bash
python manage.py sync_social_posts
```

| Argumento | Efeito |
|-----------|--------|
| `--platform instagram\|tiktok` | Sincroniza só uma plataforma. |
| `--account-id <ID>` | Sincroniza só uma conta. |
| `--limit <n>` | Posts buscados por conta (padrão: 6). |
| `--dry-run` | Não grava nada; só mostra o que faria. |
| `--verbose` | Loga cada post processado. |

Comportamento: sincroniza todas as contas ativas; faz **upsert** por
`(platform, external_id)`; **preserva** `is_visible`/`is_manual` de posts já existentes
(não desfaz uma escolha do admin); **nunca apaga** posts antigos; uma falha em uma conta
**não impede** as demais; atualiza `last_sync_at`, `last_sync_status` e
`last_sync_error` na conta.

### Cron (produção)

A primeira versão **não** usa Celery/Redis — `cron` + comando bastam. Exemplo a cada
30 minutos (dentro do container `web`):

```cron
*/30 * * * * docker compose exec -T web python manage.py sync_social_posts >> /var/log/social_sync.log 2>&1
```

---

## Segurança

- **Sem scraping.** Apenas endpoints oficiais (Instagram Graph API, TikTok Display API).
- **Tokens** nunca vão para template, JS ou repositório. Campos password-like no admin.
- **Toda chamada HTTP tem timeout** (`apps/social/services/base.py`) e converte qualquer
  falha (timeout, erro HTTP, 429, JSON inválido, token ausente) em mensagem amigável.
- Links externos abrem com `target="_blank"` e `rel="noopener noreferrer"`.
- A home funciona com a API fora do ar — usa só os dados já salvos.

---

## Limitação conhecida

As URLs de miniatura do Instagram (`thumbnail_url`/`media_url`) são links de CDN
**temporários e expiram**. O cron de 30 min as renova periodicamente; para durabilidade
total seria preciso baixar e re-hospedar a imagem (melhoria futura). Como alternativa
imediata, posts manuais podem usar o **upload** de imagem (`thumbnail_image`), que é
otimizado e fica no volume de mídia.
