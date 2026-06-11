# AI Agent Reference — news_portal

Fonte de verdade rápida para agentes que precisam ler, depurar ou alterar este projeto. Se este documento e uma inferência sua divergirem, confirme no código antes de agir.

---

## 1. Topologia

Sistema Django 5.1+ monolítico. Um banco PostgreSQL 16 em produção. Dois portais públicos separados por rota e domínio, não por dois `Site` ativos.

| Superfície | URL/prefixo | App principal |
|------------|-------------|---------------|
| Komuniki | `/` em `komuniki.com.br` | `apps.school` |
| Blog da Kelly | `/news/` em `kellyfarias.com.br` | `apps.news` |
| Admin | `/admin/` | Django Unfold |

**Crítico:** `SITE_ID = 1` em `config/settings/base.py`. O `django.contrib.sites` está instalado e muitos models têm `CurrentSiteManager` (`on_site`), mas o isolamento multi-site real está dormente. Use `on_site` em views públicas para preservar a segurança futura.

---

## 2. Stack Fixo

| Camada | Tecnologia | Regra |
|--------|------------|-------|
| Backend | Python 3.12+ / Django 5.1+ | FBV exclusivamente |
| Banco | PostgreSQL 16 em prod; SQLite opcional local | Não assuma outro banco em prod |
| Admin | Django Unfold (`django-unfold>=0.40`) | Importar `ModelAdmin` de `unfold.admin` |
| Frontend | Django templates + HTMX + Alpine.js | Sem SPA |
| CSS público | CSS próprio versionado | Não adicionar Tailwind CDN público |
| Sanitização | `apps.common.sanitization` | Não usar `bleach` espalhado |
| Deploy | Docker Compose + Nginx + GitHub tag aprovada | Ver `docs/technical/secure-deploy.md` |

`requirements/base.txt` não pina a versão menor do Unfold. Ao atualizar dependências, valide o admin e o `DASHBOARD_CALLBACK`.

---

## 3. Roteamento

Ordem em `config/urls.py`:

1. `healthz/`
2. `i18n/`
3. `admin/guias/*`
4. `admin/`
5. `sitemap.xml`
6. `hiring/`
7. `contact/`
8. `news/`
9. `accounts/`
10. `''` → escola (`apps.school`)

`/news/` precisa vir antes da raiz. A escola é catch-all.

---

## 4. Middleware

Ordem real em `config/settings/base.py`:

1. `SecurityMiddleware`
2. `WhiteNoiseMiddleware`
3. `SessionMiddleware`
4. `LocaleMiddleware`
5. `CommonMiddleware`
6. `CsrfViewMiddleware`
7. `AuthenticationMiddleware`
8. `MessageMiddleware`
9. `XFrameOptionsMiddleware`
10. `CurrentSiteMiddleware`
11. `HtmxMiddleware`
12. `AxesMiddleware`
13. `CSPMiddleware`

Context processors:

- `site_context`: injeta `current_site` e `site_settings`.
- `news_nav_context`: injeta categorias apenas em URLs sob `/news/`.

---

## 5. Apps e Modelos

### `apps.common`

- `TimeStampedModel`: `created_at`, `updated_at`.
- `SEOModel`: campos SEO comuns.
- `SiteExtension`: configuração pública do site: logo, favicon, contato, Google Analytics, redes sociais, remetente da newsletter e textos/toggles da seção social.
- `sanitization.py`: único ponto de sanitização HTML.
- `embeds.py`: resolve URLs de YouTube, Instagram e TikTok para embeds seguros.

### `apps.accounts`

- `CustomUser(AbstractUser)`: `role`, `avatar`, `bio`.
- Roles: `super_admin`, `school_admin`, `news_editor`, `hiring_manager`.
- `admin_roles.py`: cria/sincroniza grupos e permissões.

### `apps.news`

- `Article`: `draft/published/archived`, `is_featured`, `view_count`, `newsletter_sent_at`.
- `ArticleBlock`: corpo do artigo por blocos ordenados (`rich_text`, `image`, `embed`). O campo `Article.content` é cache gerado a partir dos blocos.
- `Category`, `Tag`.
- `NewsletterSubscription`, `NewsletterDelivery`.
- `Comment`, `ArticleLike`, `ArticleBookmark`.

### `apps.school`

- `SchoolHomeConfig`: textos da home, com variantes EN e fallbacks em `views.py`.
- `SchoolFeature`: cards da home; não tem campo de ícone.
- `Page`, `TeamMember`, `Testimonial`.

### `apps.hiring`

- `Department`, `JobPosting`, `Application`.
- Currículos usam nome UUID e download protegido por `X-Accel-Redirect`.

### `apps.contact`

- `ContactInquiry`: mensagens do formulário público.

### `apps.social`

- `SocialAccount`: conta Instagram/TikTok por site, links públicos, credenciais opcionais e status de sync.
- `SocialPost`: post manual ou sincronizado, com miniatura por upload/URL.
- `sync_social_posts`: comando resiliente para APIs oficiais, com `--dry-run`, `--platform`, `--account-id`, `--limit`.

---

## 6. Regras Absolutas

```python
# Views públicas: use on_site
article = get_object_or_404(Article.on_site, slug=slug, status=Article.Status.PUBLISHED)

# Contadores: update atômico
Article.on_site.filter(pk=article.pk).update(view_count=F("view_count") + 1)

# HTML de usuário: sanitize no save/model/service centralizado
from apps.common.sanitization import sanitize_content
```

```django
{# Correto #}
{{ article.content|sanitize_html }}

{# Proibido #}
{{ article.content|safe }}
```

- Não introduza CBV.
- Não adicione CDN público.
- Não exponha se e-mail/usuário existe em mensagens de erro.
- Não sirva currículo direto de `/media/hiring/resumes/`.
- Não documente recurso como existente sem confirmar em fonte `.py` versionada.

---

## 7. Newsletter

1. Artigo salvo como `published` pela primeira vez.
2. Signal registra que há newsletter pendente; não envia e-mail na request.
3. Envio real roda por `python manage.py send_pending_newsletters` ou ação do admin.
4. Cada destinatário vira `NewsletterDelivery`.
5. O artigo recebe `newsletter_sent_at` quando não resta entrega aberta.

Documento canônico: `docs/technical/FLUXO_NEWSLETTER.md`.

---

## 8. Produção

- VPS path: `/opt/kelly_sys`
- Compose project: `kellysys`
- DB container: `kellysys-db-1`
- Gunicorn: 3 workers, 2 threads, limite de memória 1500 MB
- PostgreSQL: 1024 MB
- Nginx: TLS, estáticos, mídia, rate limit e `/protected/`
- CI/CD: workflow manual `Deploy Production` → environment `production` → tag `production-approved` → timer da VPS executa deploy

Guias: `docs/technical/go-live-checklist.md`, `docs/technical/DEPLOY.md`, `docs/technical/secure-deploy.md`.
