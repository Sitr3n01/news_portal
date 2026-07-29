# Camada de Segurança — news_portal

> As proteções ativas do sistema, organizadas por ameaça. Auditado em duas rodadas (Fase 8.6). Este documento descreve **o que protege o quê e onde**.
>
> Documentos relacionados: [ARQUITETURA_E_MODELOS.md](ARQUITETURA_E_MODELOS.md) · [APP_HIRING.md](APP_HIRING.md) · [FLUXO_NEWSLETTER.md](FLUXO_NEWSLETTER.md)

---

## 1. Visão geral — defesa em profundidade

| Ameaça | Proteção | Onde |
|--------|----------|------|
| XSS em conteúdo | Sanitização com `bleach` no `save()` dos modelos | `apps/common/sanitization.py` |
| XSS em template | Filtro `sanitize_html`; proibição do filtro de escape-off | Templates + `templatetags/sanitize.py` |
| CSRF | Middleware CSRF + `{% csrf_token %}` | Middleware + formulários |
| SQL Injection | ORM parametrizado (sem SQL cru) | Toda a camada de dados |
| Força bruta no login | `django-axes` (5 tentativas → 30 min de bloqueio) | `AxesMiddleware` |
| Mailbomb no reset de senha | Turnstile + rate limit por IP e por identidade (15 min) | `apps/accounts/code_views.py` + `verification.py` |
| Host header poisoning no reset | Não se aplica: o e-mail de código não carrega URL nenhuma | `templates/emails/` |
| Código de verificação longo demais | TTL de 10 min, uso único, teto de 5 tentativas | `apps/accounts/verification.py` |
| Força bruta em código de 6 dígitos | Teto por código + rate limit de validação por IP | `apps/accounts/verification.py` |
| Código vazado no banco | Só HMAC-SHA256 com `SECRET_KEY` como pepper; texto puro nunca é persistido | `apps/accounts/verification.py` |
| Login-CSRF no OAuth | `state` na sessão do servidor, conferido com `compare_digest` | `apps/accounts/oauth_views.py` |
| Replay de ID token | `nonce` conferido à mão + fluxo de uso único (`session.pop`) | `apps/accounts/oauth_google.py` |
| Código de autorização interceptado | PKCE S256 (`code_verifier` nunca sai do servidor) | `apps/accounts/oauth_google.py` |
| Redirect URI forjado pelo Host | `GOOGLE_OAUTH_REDIRECT_URI` fixado por variável de ambiente | `config/settings/base.py` |
| Escalada por login social | O Google só autentica; cargo/grupo/`is_staff` vêm do banco e nunca são escritos no fluxo | `apps/accounts/oauth_views.py` |
| Sequestro por e-mail no OAuth | Casamento por e-mail exige `email_verified` do Google; identidade chaveada pelo `sub` imutável | `apps/accounts/oauth_google.py` |
| Conta duplicada por capitalização | E-mail normalizado na gravação + busca `__iexact` | `apps/accounts/forms.py` + migration `0009` |
| Enumeração de usuários | Mensagens e redirecionamentos idênticos em cadastro/reset/candidatura | Views e forms |
| E-mail sumindo em silêncio | System check `accounts.E001` barra backend fake fora de DEBUG, no deploy | `apps/accounts/checks.py` |
| Clickjacking | `X-Frame-Options: DENY` | Middleware + nginx |
| Upload malicioso | Extensão + MIME + **magic bytes** (5 MB) | `hiring/forms.py` |
| Vazamento de currículo | Nome UUID + download autenticado via `X-Accel-Redirect` | `hiring` + nginx |
| iframe hostil | Whitelist apenas YouTube | `sanitization.py` |
| Scripts externos | CSP (Django + nginx espelhado) | `base.py` + `nginx.conf` |
| Sessão sequestrada | Cookies `HttpOnly` + `Secure` (prod) | `production.py` |
| Downgrade HTTPS | HSTS (1 ano, preload) + redirect SSL | `production.py` |
| CSV/fórmula injection | Prefixo de neutralização na exportação | `news/admin.py` |
| Flood/scrapers | Rate limit no nginx (10 req/s, burst 20) | `nginx.conf` |
| Container comprometido | Processo como usuário não-root | `Dockerfile` |
| Vazamento entre portais | Manager `on_site` em views/feeds/sitemaps | Toda a camada pública |
| Bots/spam em formulários | Cloudflare Turnstile (widget + siteverify) | `apps/common/turnstile.py` + forms |
| Bots/scraping na borda | Cloudflare proxy + Bot Fight Mode + firewall só-CF | Cloudflare + `cloudflare-firewall.sh` |
| IP real atrás do proxy | `realip` lendo `CF-Connecting-IP` | `nginx.conf` + `cloudflare-realip.conf` |

---

## 2. Sanitização de HTML (anti-XSS)

Toda entrada HTML de usuário passa por um único lugar: [`apps/common/sanitization.py`](../../apps/common/sanitization.py). **Nunca** se duplica lista de tags em outro app.

- **`sanitize_content(value)`** usa `bleach.clean(..., strip=True)` — tags não permitidas são **removidas**, não escapadas.
- **Tags permitidas:** formatação editorial (`p`, `strong`, `em`, listas, cabeçalhos `h2`–`h6`, `blockquote`, `pre`/`code`, tabelas, `figure`, `img`, `iframe`…).
- **iframe restrito a YouTube:** o callback `_validate_iframe_attr` só aceita `src` cujo host esteja em `ALLOWED_IFRAME_HOSTS` (`youtube.com`, `youtube-nocookie.com`). Qualquer outro embed é descartado.
- **CSS inline filtrado:** `CSS_SANITIZER` libera só propriedades visuais seguras (cor, fonte, margem, padding, borda…). Propriedades perigosas como `position` ou `background-image` são bloqueadas.

**Onde é aplicado:** no `save()` de `Article` ([`apps/news/models.py`](../../apps/news/models.py)) e de `Page` ([`apps/school/models.py`](../../apps/school/models.py)) — a sanitização acontece **antes de gravar**, então o banco nunca guarda HTML perigoso.

### Regra de template
O projeto **proíbe** o filtro que desliga o escape automático do Django. Em vez dele, usa-se `{{ conteudo|sanitize_html }}` (em [`templatetags/sanitize.py`](../../apps/common/templatetags/sanitize.py)), que sanitiza o HTML e então o marca como seguro para renderização — evitando tanto XSS quanto escape duplo. A auditoria confirmou **zero** usos do filtro de escape-off nos templates.

---

## 3. Autenticação e contas

### Força bruta — `django-axes`
Em `base.py`:
- `AXES_FAILURE_LIMIT = 5` — 5 tentativas falhas;
- `AXES_COOLOFF_TIME = 0.5` — 30 minutos de bloqueio;
- `AXES_LOCKOUT_PARAMETERS = ['ip_address', 'username']` — bloqueia por IP **e** por usuário;
- `AXES_RESET_ON_SUCCESS = True` — login válido zera o contador.

O `AxesMiddleware` intercepta o login; as views de autenticação não precisam de lógica própria de bloqueio. (Para desbloquear manualmente: `python manage.py axes_reset_username --username ...`.)

### Códigos de verificação — `apps/accounts/verification.py`
Uma camada só atende **confirmação de e-mail** e **recuperação de senha** (`VerificationCode.Purpose`), para as duas não divergirem sobre prazo, teto ou rate limit:

1. **Geração:** `secrets.choice` (CSPRNG), 6 dígitos.
2. **Armazenamento:** só o HMAC-SHA256 (`salted_hmac`, com `SECRET_KEY` como *pepper* fora do banco, e `key_salt` incluindo propósito e id do usuário). O texto puro existe apenas no retorno de `issue_code` e no corpo do e-mail.
3. **Prazo e uso:** `VERIFICATION_CODE_TTL` (10 min), uso único (`used_at`), teto de `VERIFICATION_CODE_MAX_ATTEMPTS` (5) por código — estourou, o código é queimado.
4. **Reemissão invalida a anterior:** só o último código vale, para não haver dois segredos válidos ao mesmo tempo.
5. **Rate limit:** 3 emissões por (usuário, propósito), 10 por IP e 20 validações por IP, em janela de 15 minutos, com chaves hasheadas no `DatabaseCache`.
6. **Comparação:** `secrets.compare_digest` sobre os hashes — nunca `==`.

### Recuperação de senha — `apps/accounts/code_views.py`
Fluxo por **código**, não por link: informar e-mail → receber código → digitar → definir senha nova.

- **Anti-enumeração:** exista ou não a conta, a resposta, a mensagem e o próximo passo são idênticos. Conta com `is_active=False` também não recebe código, sem que isso apareça na tela.
- **Anti-mailbomb:** Turnstile no formulário + rate limit por IP no nível da view (o balde de `issue_code` só conta quando a conta existe).
- **Estado na sessão do servidor**, com estágio (`code` → `password`) e prazo próprio de 15 min: pular direto para a tela de senha nova não abre.
- **Reenvio lê o e-mail da SESSÃO**, nunca do corpo do POST — senão seria um disparador de e-mail para endereço arbitrário.
- **Ao concluir:** todos os códigos pendentes são invalidados, o e-mail passa a confirmado (posse da caixa comprovada) e as demais sessões caem sozinhas, porque trocar a senha muda `get_session_auth_hash()`.
- As rotas antigas `password_reset_confirm`/`password_reset_complete` seguem roteadas apenas para que links já enviados não caiam em 404; nada mais gera esses links.

### Login com Google — `apps/accounts/oauth_google.py` e `oauth_views.py`
Authorization Code + PKCE, implementação própria (sem `allauth`/`social-auth`, que colidiriam com o login unificado).

- **`state`** na sessão do servidor, conferido com `compare_digest` — defesa de login-CSRF. Fluxo de uso único (`session.pop`).
- **`nonce`** conferido explicitamente: `google-auth` valida assinatura, `iss`, `aud` e `exp`, mas **não** o nonce.
- **PKCE S256:** o `code_verifier` nunca chega ao navegador.
- **`redirect_uri`** vem de variável de ambiente, nunca de `build_absolute_uri()` (Host é influenciável atrás do proxy).
- **`email_verified` do Google é obrigatório** para casar por e-mail; a identidade é chaveada pelo `sub` (imutável), nunca pelo endereço.
- **Autenticação ≠ autorização:** nenhum caminho do fluxo escreve `role`, `groups`, `is_staff` ou `is_superuser`, e `sync_user_role_group` não é chamada. Conta nova nasce `reader`, sem grupo, sem staff, com senha inutilizável. O destino sai de `panels.post_login_target`, a mesma função do login por senha.
- Conta desativada é recusada **antes** do `login()`; conta em cooloff do `axes` também, para o Google não ser porta lateral do bloqueio.

### Anti-enumeração de usuários
A política é **nunca revelar** se um e-mail/usuário existe:
- **Cadastro** ([`apps/accounts/forms.py`](../../apps/accounts/forms.py)): e-mail duplicado retorna mensagem genérica — *"Não foi possível criar a conta. Verifique os dados e tente novamente."*
- **Reset de senha:** resposta, mensagem e próxima tela idênticas, exista ou não a conta.
- **Candidatura duplicada** (`hiring`): mesma mensagem de sucesso, sem revelar que aquele e-mail já se candidatou.

### E-mail como identidade
`CustomUser.email` é `unique=True` **no banco** — constraint real, não só validação de formulário. A comparação é **case-insensitive** na aplicação: o cadastro grava em minúsculas e as buscas de identidade usam `__iexact`. Antes disso, `Fulano@x.com` e `FULANO@X.COM` viravam duas contas para a mesma caixa (corrigido na migration `0009`; `manage.py find_duplicate_emails` relata colisões remanescentes, sem nunca fundir contas por conta própria).

### Sessão
- `SESSION_COOKIE_HTTPONLY = True` e `SESSION_COOKIE_SECURE = True` (produção);
- `SESSION_COOKIE_AGE = 43200` (12h);
- `SESSION_SAVE_EVERY_REQUEST = True` — renova a sessão a cada request (evita logout de usuário ativo).

---

## 4. Upload e currículos (LGPD)

Detalhado em [APP_HIRING.md](APP_HIRING.md#5-currículos-o-ponto-mais-sensível). Resumo das três barreiras:

1. **Nome imprevisível:** `resume_upload_path` grava com `uuid4().hex` — nada de URL adivinhável.
2. **Validação real de conteúdo:** [`ApplicationForm.clean_resume`](../../apps/hiring/forms.py) confere tipo MIME, extensão **e magic bytes** (`%PDF-`, `PK\x03\x04`, `\xd0\xcf\x11\xe0`). Os magic bytes são a defesa que vale — MIME e extensão são falsificáveis. Limite de 5 MB.
3. **Entrega protegida:** `download_resume` exige `staff` + permissão `hiring.view_application`; em produção delega ao nginx via `X-Accel-Redirect` a partir de uma *location interna* (`/protected/`). O nginx **bloqueia** acesso público direto a `/media/hiring/resumes/`.

---

## 5. CSP e cabeçalhos de segurança

### Content Security Policy
Configurada em `base.py` via `django-csp` e **espelhada** no [`nginx.conf`](../../docker/nginx/nginx.conf) (defesa mesmo sem o proxy):

- `default-src` restrito à própria origem;
- `script-src` precisa liberar execução inline e avaliação dinâmica de JS — exigência do **HTMX** e do **Alpine.js** (os tokens exatos estão em `base.py`/`nginx.conf`);
- `style-src` permite estilos inline + Google Fonts;
- `img-src` permite `data:` e `https:`;
- `frame-src` permite apenas YouTube;
- `object-src` bloqueado (`none`); `base-uri` e `form-action` restritos à origem; `frame-ancestors 'none'` (anti-clickjacking moderno, complementa `X-Frame-Options`).

> O preço de `script-src` liberar inline/eval é mitigado por: sanitização do conteúdo, `frame-src` restrito e `object-src` bloqueado.

### Cabeçalhos (nginx, `always`)
`X-Content-Type-Options: nosniff` · `X-Frame-Options: DENY` · `Referrer-Policy: strict-origin-when-cross-origin` · `Permissions-Policy` (geolocation/microphone/camera vazios) · `Content-Security-Policy`.

---

## 6. Endurecimento de produção (`config/settings/production.py`)

| Configuração | Valor | Efeito |
|--------------|-------|--------|
| `DEBUG` | `False` | Sem stack trace ao usuário |
| `SECURE_HSTS_SECONDS` | `31536000` | HSTS de 1 ano |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` / `PRELOAD` | `True` | Cobre subdomínios + elegível a preload |
| `SECURE_SSL_REDIRECT` | `True` | Força HTTPS |
| `SECURE_PROXY_SSL_HEADER` | `X-Forwarded-Proto` | Reconhece HTTPS atrás do nginx |
| `SECURE_CONTENT_TYPE_NOSNIFF` | `True` | Sem MIME-sniffing |
| `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` | `True` | Cookies só sob HTTPS |
| `CSRF_COOKIE_HTTPONLY` | `True` | Cookie CSRF inacessível a JS |
| `CSRF_TRUSTED_ORIGINS` | via `.env` | Origens confiáveis |
| `SECURE_REDIRECT_EXEMPT` | `^healthz/$` | Healthcheck interno não recebe 301 |
| `X_FRAME_OPTIONS` | `DENY` | Anti-clickjacking |
| `SECURE_REFERRER_POLICY` | `strict-origin-when-cross-origin` | Paridade Django com o header do nginx |

**Sentry** é habilitado apenas se `SENTRY_DSN` existir, com `send_default_pii=False` (não envia dados pessoais).

---

## 7. Infraestrutura

- **Rate limiting (nginx):** `limit_req_zone ... rate=10r/s` com `burst=20 nodelay` — segura floods e scrapers.
- **Limite de upload:** `client_max_body_size 10M` (alinhado com `DATA_UPLOAD_MAX_MEMORY_SIZE` do Django).
- **Locations internas:** `/protected/` e `/media/hiring/resumes/` são `internal` — só acessíveis via `X-Accel-Redirect`.
- **Container não-root:** o processo roda como `appuser` (UID 1000), reduzindo impacto de um comprometimento.
- **TLS:** Certbot/Let's Encrypt no nginx (bloco `:443` ativo).
- **Proteção de bots (Cloudflare):** duas camadas — Turnstile nos formulários (app) e Bot Fight Mode + firewall só-Cloudflare na borda. Blocos de comando em [cloudflare-bots.md](cloudflare-bots.md).
- **IP real atrás do proxy:** o nginx usa `realip` com `CF-Connecting-IP` e encaminha `X-Forwarded-For $remote_addr` — `rate-limit`, `axes` e Turnstile veem o visitante real, não o Cloudflare.

---

## 8. Detalhes que passam batido

- **Exportação de assinantes (CSV):** a ação `export_emails` é **restrita a superusuário** e cada célula passa por `_csv_safe`, que neutraliza fórmulas (`=`, `+`, `-`, `@`) — previne **CSV/formula injection** ao abrir a planilha.
- **Unsubscribe assinado:** o cancelamento de newsletter usa token assinado (`signing`), não o ID — ver [FLUXO_NEWSLETTER.md](FLUXO_NEWSLETTER.md#5-cancelamento-de-inscrição-unsubscribe).
- **Contagem de views à prova de inflar:** `article_detail` grava flag na sessão e usa `F('view_count') + 1` (atômico) — sem corrida e sem incrementar a cada F5.
- **Comentário limitado:** o conteúdo é truncado em `[:5000]` na view (anti-DoS de payload gigante).
- **Redirect seguro:** `safe_referer_redirect` valida o `Referer` contra o domínio atual antes de redirecionar (anti open-redirect).
- **Isolamento por site é segurança:** usar `on_site` (e não `objects`) nas views públicas impede vazamento entre portais quando o multi-site for ativado.

---

## 9. Dívidas e limites conhecidos

| Item | Situação | Observação |
|------|----------|------------|
| Warnings do `django-axes` | Conhecidos | Dívida técnica separada; não bloqueiam |
| Antivírus em uploads | Ausente | Validação por magic bytes cobre o básico; para ambiente sensível, considerar ClamAV |
| Tipo MIME do upload | Secundário | É falsificável; a defesa real são os magic bytes |
| Páginas de erro 404/500/403 | Pendentes | Fase 10 (hardening de produção) |
| Domínio do `Site` no banco | Operacional | Se incorreto, quebra links de e-mail e do reset de senha |

---

## 10. Checklist ao alterar algo sensível

- [ ] Conteúdo HTML novo do usuário? Garanta sanitização no `save()` via `apps.common.sanitization`.
- [ ] View pública nova? Use `on_site`, nunca `objects`.
- [ ] Formulário novo? Tem `{% csrf_token %}`?
- [ ] Mensagem de erro de auth/candidatura? Mantenha genérica (não revele existência de dados).
- [ ] Upload novo? Valide conteúdo real (magic bytes), não só extensão/MIME.
- [ ] Template novo? Não use o filtro de escape-off; use `|sanitize_html`.
- [ ] Mudou middleware? Confira a ordem (axes depois de auth; CSP por último).

---

_Última atualização: 2026-06-06 — adicionada a camada Cloudflare (Turnstile + borda + real-IP) e os cabeçalhos `frame-ancestors`/`SECURE_REFERRER_POLICY`. Runbook em [cloudflare-bots.md](cloudflare-bots.md)._
