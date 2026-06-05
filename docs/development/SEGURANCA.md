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
| Mailbomb no reset de senha | Rate limit por IP+e-mail (15 min) | `CustomPasswordResetView` |
| Host header poisoning | Domínio forçado pelo banco no reset | `CustomPasswordResetView` |
| Token de reset longo | Expiração reduzida para 1 hora | `PASSWORD_RESET_TIMEOUT` |
| Enumeração de usuários | Mensagens genéricas em cadastro/reset/candidatura | Views e forms |
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

### Recuperação de senha — `CustomPasswordResetView`
Em [`apps/accounts/views.py`](../../apps/accounts/views.py), três camadas:

1. **Rate limit anti-mailbomb:** chave de cache `pwd_reset_limit_{ip}_{email}` bloqueia novos pedidos por **15 minutos**. Se já houver pedido recente, o sistema **finge sucesso** e descarta o envio — não dá pista ao atacante.
2. **Anti host-header poisoning:** o link do e-mail usa `domain_override = site.domain` (domínio do banco), **ignorando** o header `Host` da request, que é forjável.
3. **Token de curta duração:** `PASSWORD_RESET_TIMEOUT = 3600` (1 hora, contra 24h padrão do Django) reduz a janela de ataque.

### Anti-enumeração de usuários
A política é **nunca revelar** se um e-mail/usuário existe:
- **Cadastro** ([`apps/accounts/forms.py`](../../apps/accounts/forms.py)): e-mail duplicado retorna mensagem genérica — *"Não foi possível criar a conta. Verifique os dados e tente novamente."*
- **Reset de senha:** mesmo comportamento visível independentemente de o e-mail existir.
- **Candidatura duplicada** (`hiring`): mesma mensagem de sucesso, sem revelar que aquele e-mail já se candidatou.

### E-mail como identidade
`CustomUser.email` é `unique=True` **no banco** — constraint real, não só validação de formulário.

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
- `object-src` bloqueado (`none`); `base-uri` e `form-action` restritos à origem.

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

**Sentry** é habilitado apenas se `SENTRY_DSN` existir, com `send_default_pii=False` (não envia dados pessoais).

---

## 7. Infraestrutura

- **Rate limiting (nginx):** `limit_req_zone ... rate=10r/s` com `burst=20 nodelay` — segura floods e scrapers.
- **Limite de upload:** `client_max_body_size 10M` (alinhado com `DATA_UPLOAD_MAX_MEMORY_SIZE` do Django).
- **Locations internas:** `/protected/` e `/media/hiring/resumes/` são `internal` — só acessíveis via `X-Accel-Redirect`.
- **Container não-root:** o processo roda como `appuser` (UID 1000), reduzindo impacto de um comprometimento.
- **TLS:** preparado para Certbot/Let's Encrypt (bloco `:443` comentado, pronto para o go-live).

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

_Última atualização: 2026-06-03 — gerado a partir de leitura direta do código (`sanitization.py`, `accounts/views.py` e `forms.py`, `hiring/forms.py` e `views.py`, `production.py`, `nginx.conf`, `news/admin.py`)._
