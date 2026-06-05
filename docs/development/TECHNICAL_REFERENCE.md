# Technical Reference — news_portal

> Documentação exaustiva para debugging sensível e mudanças estruturais. Assume conhecimento profundo de Django.

---

## Índice

1. [Arquitetura Geral](#1-arquitetura-geral)
2. [Middleware Chain](#2-middleware-chain)
3. [Settings por Ambiente](#3-settings-por-ambiente)
4. [Apps — Referência Completa](#4-apps--referência-completa)
   - [common](#41-common)
   - [accounts](#42-accounts)
   - [school](#43-school)
   - [hiring](#44-hiring)
   - [contact](#45-contact)
   - [news](#46-news)
   - [media_library](#47-media_library)
5. [URL Routing](#5-url-routing)
6. [Template Engine](#6-template-engine)
7. [Banco de Dados](#7-banco-de-dados)
8. [Segurança](#8-segurança)
9. [Sistema de Email](#9-sistema-de-email)
10. [Infraestrutura Docker/Nginx](#10-infraestrutura-dockernginx)
11. [Dependências Externas](#11-dependências-externas)
12. [Sinais e Efeitos Colaterais](#12-sinais-e-efeitos-colaterais)
13. [Context Processors](#13-context-processors)
14. [Diagnóstico e Debugging](#14-diagnóstico-e-debugging)

---

## 1. Arquitetura Geral

```
Request
  │
  ▼
Nginx (porta 80/443)
  │  Rate limiting (10 req/s, burst 20)
  │  Security headers
  │  Serve static/media diretamente
  │
  ▼
Gunicorn (porta 8000, 4 workers, 2 threads)
  │
  ▼
Django WSGI Application
  │
  ▼
Middleware Chain (13 camadas — ver seção 2)
  │
  ▼
URL Router (config/urls.py)
  │
  ├─► /admin/         → Unfold Admin
  ├─► /news/          → apps.news.urls
  ├─► /hiring/        → apps.hiring.urls
  ├─► /contact/       → apps.contact.urls
  ├─► /accounts/      → apps.accounts.urls
  └─► /              → apps.school.urls (catch-all)
  │
  ▼
FBV (Function-Based View)
  │
  ▼
Response
```

**Multi-site:** Django Sites Framework com `SITE_ID`. Cada portal é um `Site` diferente no banco. `CurrentSiteManager` filtra queries por `request.site` automaticamente. O middleware `CurrentSiteMiddleware` popula `request.site` em cada request.

---

## 2. Middleware Chain

Ordem exata definida em `config/settings/base.py`. A ordem importa — cada middleware envolve o próximo.

| Posição | Classe | Pacote | Função |
|---------|--------|--------|--------|
| 1 | `SecurityMiddleware` | django | HTTPS redirect, HSTS, XSS filter headers |
| 2 | `WhiteNoiseMiddleware` | whitenoise | Intercepta requests de static files antes de chegar ao Django |
| 3 | `SessionMiddleware` | django | Habilita `request.session` |
| 4 | `LocaleMiddleware` | django | Detecta idioma do usuário (pt-br) |
| 5 | `CommonMiddleware` | django | APPEND_SLASH, PREPEND_WWW |
| 6 | `CsrfViewMiddleware` | django | Valida CSRF token em POST/PUT/PATCH/DELETE |
| 7 | `AuthenticationMiddleware` | django | Popula `request.user` |
| 8 | `MessageMiddleware` | django | Habilita `request.messages` |
| 9 | `XFrameOptionsMiddleware` | django | Header `X-Frame-Options: DENY` |
| 10 | `CurrentSiteMiddleware` | django.contrib.sites | Popula `request.site` |
| 11 | `HtmxMiddleware` | django_htmx | Popula `request.htmx` (bool + headers HTMX) |
| 12 | `AxesMiddleware` | axes | Intercepta logins — aplica lockout se limite atingido |
| 13 | `CSPMiddleware` | django_csp | Adiciona header `Content-Security-Policy` |

**Debugging de middleware:** Para isolar um problema de middleware, comente temporariamente em ordem reversa (13→1) até o comportamento mudar.

**Atenção:** `AxesMiddleware` deve estar depois de `AuthenticationMiddleware` e antes de qualquer view de autenticação. Mudar sua posição quebra o lockout.

---

## 3. Settings por Ambiente

### Hierarquia de arquivos

```
config/settings/
├── base.py           # Configuração base — sempre carregado
├── development.py    # extends base — dev local com Docker
├── production.py     # extends base — produção
├── test.py           # extends base — pytest
└── local_sqlite.py   # extends base — dev sem PostgreSQL
```

O arquivo de settings é selecionado via `DJANGO_SETTINGS_MODULE` environment variable.

### base.py — Configurações críticas

```python
# Autenticação
AUTH_USER_MODEL = 'accounts.CustomUser'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Sites framework
SITE_ID = 1

# Internacionalização
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# Sessões
SESSION_COOKIE_AGE = 43200          # 12 horas
SESSION_SAVE_EVERY_REQUEST = True   # Renova sessão em cada request

# Axes (brute-force)
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.5             # 30 minutos
AXES_LOCKOUT_PARAMETERS = ['ip_address', 'username']
AXES_RESET_ON_SUCCESS = True

# Password reset
PASSWORD_RESET_TIMEOUT = 3600       # 1 hora (default Django é 24h)
```

### production.py — Configurações de segurança

```python
DEBUG = False
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
```

### CSP — Content Security Policy

Configurada em `base.py` via `django-csp`:

```python
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
        "style-src": ["'self'", "'unsafe-inline'"],
        "img-src": ["'self'", "data:", "https:"],
        "frame-src": ["https://www.youtube.com", "https://youtube.com"],
        "font-src": ["'self'"],
        "connect-src": ["'self'"],
    }
}
```

`unsafe-inline` e `unsafe-eval` em `script-src` são necessários para HTMX e Alpine.js. Mitigados por isolamento de iframe e sanitização de conteúdo.

A mesma CSP é espelhada no `nginx.conf` como defesa em profundidade.

---

## 4. Apps — Referência Completa

### 4.1 common

**Localização:** `apps/common/`

#### Models

##### TimeStampedModel (abstract)

```python
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
```

##### SEOModel (abstract)

```python
class SEOModel(models.Model):
    meta_title       = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    meta_keywords    = models.CharField(max_length=255, blank=True)
    
    class Meta:
        abstract = True
```

##### SiteExtension

One-to-one com `django.contrib.sites.Site`. Uma instância por site.

| Campo | Tipo | Null/Blank | Descrição |
|-------|------|-----------|-----------|
| `site` | OneToOneField(Site) | — | PK lógico |
| `tagline` | CharField(200) | blank=True | Subtítulo do site |
| `logo` | ImageField | blank=True | Logo principal |
| `favicon` | ImageField | blank=True | Favicon |
| `primary_email` | EmailField | blank=True | Email de contato público |
| `phone_number` | CharField(20) | blank=True | Telefone público |
| `address` | TextField | blank=True | Endereço físico |
| `newsletter_from_email` | EmailField | blank=True | Remetente da newsletter |
| `newsletter_from_name` | CharField(100) | blank=True | Nome do remetente |
| `google_analytics_id` | CharField(20) | blank=True | GA ID (ex: G-XXXXXXXX) |
| `facebook_url` | URLField | blank=True | URL Facebook |
| `instagram_url` | URLField | blank=True | URL Instagram |
| `youtube_url` | URLField | blank=True | URL YouTube |

**Nota:** Sem `on_delete` explícito — é `OneToOneField`, cascade automático se o Site for deletado.

#### Sanitização (`apps/common/sanitization.py`)

Usa `bleach` para sanitização HTML. **Todo HTML de usuário deve passar por aqui.**

```python
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'b', 'em', 'i', 'u',
    'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li',
    'a', 'img', 'iframe',           # iframe restrito a YouTube
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'blockquote', 'code', 'pre',
    'div', 'span',
]

ALLOWED_ATTRIBUTES = {
    'a':       ['href', 'title', 'target', 'rel', 'class'],
    'img':     ['src', 'alt', 'width', 'height', 'class', 'style', 'loading'],
    'iframe':  ['src', 'width', 'height', 'frameborder', 'allowfullscreen', 'allow'],
    'td':      ['colspan', 'rowspan', 'class'],
    'th':      ['colspan', 'rowspan', 'class'],
    '*':       ['class', 'id', 'style'],
}
```

Iframes são filtrados por `_validate_iframe_attr()` — só aceita `src` de `youtube.com` ou `youtu.be`.

CSS inline é filtrado por `CSS_SANITIZER` (whitelist de propriedades seguras: color, margin, padding, font-weight, text-align, etc.).

**Função principal:**
```python
def sanitize_content(value: str) -> str:
    return bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        css_sanitizer=CSS_SANITIZER,
        strip=True,              # Remove tags não permitidas (não escapa)
    )
```

#### Context Processors (`apps/common/context_processors.py`)

##### `site_context(request)`

Sempre injetado. Retorna:
```python
{
    'current_site': Site.objects.get_current(request),
    'site_settings': SiteExtension.objects.get_or_create(site=current_site)[0],
}
```

**Atenção:** `get_or_create` cria um `SiteExtension` vazio se não existir — não lança exceção.

##### `news_nav_context(request)`

Só injetado em paths começando com `/news/`. Retorna:
```python
{
    'nav_categories': Category.objects.filter(parent=None).order_by('order')[:8],
}
```

#### Template Tags (`apps/common/templatetags/sanitize.py`)

```python
@register.filter(name='sanitize_html')
def sanitize_html_filter(value):
    return mark_safe(sanitize_content(value))
```

Uso: `{{ article.content|sanitize_html }}`

#### Dashboard (`apps/common/dashboard.py`)

Função `dashboard_callback(request, context)` chamada por `UNFOLD['DASHBOARD_CALLBACK']`.

Injeta no context do admin:
- `open_jobs`, `pending_applications`, `unread_messages`
- `published_articles`, `draft_articles`, `newsletter_subscribers`, `pending_comments`
- `articles_this_month`, `articles_last_month`, `new_newsletter_today`
- `recent_articles`, `recent_applications`, `recent_messages`

**Ponto de atenção:** Se uma das queries falhar (ex: app não migrado), o dashboard inteiro quebra. Queries devem ser defensivas.

---

### 4.2 accounts

**Localização:** `apps/accounts/`

#### Model: CustomUser

Herda de `AbstractUser`. Campos adicionais:

| Campo | Tipo | Null/Blank | Descrição |
|-------|------|-----------|-----------|
| `email` | EmailField | unique=True | Obrigatório, único — usado como identidade |
| `role` | CharField(20, choices=Role) | blank=True | Enum: SUPER_ADMIN, SCHOOL_ADMIN, NEWS_EDITOR, HIRING_MANAGER |
| `avatar` | ImageField(upload_to='avatars/') | blank=True | Foto de perfil |
| `bio` | TextField | blank=True | Biografia |

`AbstractUser` herda: `username`, `first_name`, `last_name`, `is_active`, `is_staff`, `is_superuser`, `last_login`, `date_joined`, `groups`, `user_permissions`.

**Campo `email` é `unique=True` no banco** (migration 0003). Constraint real, não só validação de form.

#### Views

##### `CustomLoginView`

Estende `django.contrib.auth.views.LoginView`. Template: `accounts/login.html`.

O `AxesMiddleware` intercepta automaticamente após 5 falhas — a view não precisa de lógica de lockout.

##### `CustomPasswordResetView`

Estende `PasswordResetView`. Proteções adicionais:

1. **Rate limiting:** `cache.get(f"pwd_reset_{ip}_{email}")` — bloqueia novo pedido por 15 minutos.
2. **Host header poisoning:** `domain_override=Site.objects.get_current().domain` — usa domínio do banco, não o header `Host` da request (que pode ser forjado).

##### `register_view`

FBV. Usa `CustomUserCreationForm`. Se `subscribe_newsletter=True` no form:
```python
NewsletterSubscription.objects.get_or_create(
    email=user.email,
    site=get_current_site(request),
    defaults={'is_active': True}
)
```

Mensagem de erro de email duplicado é propositalmente genérica (anti-enumeration).

##### `delete_account`

`@login_required`, método POST. Valida senha antes de deletar — `request.user.check_password(password)`.

##### `toggle_newsletter`

`@login_required`, método POST. Faz upsert em `NewsletterSubscription` e inverte `is_active`.

#### Form: CustomUserCreationForm

Campos: `username`, `email`, `password1`, `password2`, `subscribe_newsletter`.

`clean_email()` verifica duplicata. Mensagem de erro: `"Este endereço de email já está em uso."` — genérico intencionalmente (não confirma se o email existe em outros contextos).

#### Migrations

| # | Arquivo | Mudança |
|---|---------|---------|
| 0001 | initial | CustomUser (role, avatar, bio) |
| 0002 | add_avatar_bio | Ajuste de campos |
| 0003 | email_unique | `unique=True` no email |

**Atenção em mudanças:** Adicionar campos ao `CustomUser` requer migration. Remover campos que outros apps usam via `AUTH_USER_MODEL` pode quebrar FK implícitas (ex: `Article.author`).

---

### 4.3 school

**Localização:** `apps/school/`

#### Models

##### Page

| Campo | Tipo | Null/Blank | Índice |
|-------|------|-----------|--------|
| `site` | ForeignKey(Site, CASCADE) | — | db_index padrão |
| `title` | CharField(200) | — | — |
| `slug` | SlugField(200) | — | unique_together com site |
| `content` | TextField | blank=True | — |
| `featured_image` | ImageField(upload_to='school/pages/') | blank=True | — |
| `is_published` | BooleanField | default=True | — |
| `order` | PositiveIntegerField | default=0 | — |
| `meta_title` | CharField(70) | blank=True | — |
| `meta_description` | CharField(160) | blank=True | — |
| `meta_keywords` | CharField(255) | blank=True | — |

Managers: `objects = Manager()`, `on_site = CurrentSiteManager()`.

`save()` chama `sanitize_content(self.content)` antes de chamar `super().save()`.

##### TeamMember

| Campo | Tipo | Null/Blank |
|-------|------|-----------|
| `name` | CharField(200) | — |
| `title` | CharField(200) | blank=True |
| `photo` | ImageField(upload_to='school/team/') | blank=True |
| `bio` | TextField | blank=True |
| `email` | EmailField | blank=True |
| `is_active` | BooleanField | default=True |
| `order` | PositiveIntegerField | default=0 |

Ordering: `[order, name]`. Sem ForeignKey(Site) — dados globais compartilhados entre portais.

##### Testimonial

| Campo | Tipo | Null/Blank |
|-------|------|-----------|
| `name` | CharField(200) | — |
| `relationship` | CharField(200) | blank=True |
| `quote` | TextField | — |
| `photo` | ImageField(upload_to='school/testimonials/') | blank=True |
| `is_featured` | BooleanField | default=False |

Ordering: `[-created_at]`.

#### Views

| View | URL | Query |
|------|-----|-------|
| `home` | `/` | `Testimonial.objects.filter(is_featured=True)` |
| `page_detail` | `/<slug>/` | `Page.on_site.get(slug=slug, is_published=True)` |
| `team_list` | `/team/` | `TeamMember.objects.filter(is_active=True).order_by('order', 'name')` |
| `about` | `/sobre/` | Template estático |
| `privacy` | `/privacidade/` | Template estático |

#### Sitemap

`PageSitemap` retorna `Page.on_site.filter(is_published=True)`. `changefreq='monthly'`, `priority=0.5`.

---

### 4.4 hiring

**Localização:** `apps/hiring/`

#### Models

##### Department

| Campo | Tipo |
|-------|------|
| `name` | CharField(200) |
| `slug` | SlugField(200, unique=True) |

##### JobPosting

| Campo | Tipo | Null/Blank |
|-------|------|-----------|
| `department` | ForeignKey(Department, CASCADE) | — |
| `title` | CharField(200) | — |
| `slug` | SlugField(200, unique=True) | — |
| `description` | TextField | — |
| `requirements` | TextField | blank=True |
| `employment_type` | CharField(20, choices=EmploymentType) | — |
| `location` | CharField(200) | blank=True |
| `salary_range` | CharField(100) | blank=True |
| `status` | CharField(10, choices=Status) | default=DRAFT |
| `published_at` | DateTimeField | null=True, blank=True |
| `deadline` | DateTimeField | null=True, blank=True |
| `meta_description` | CharField(160) | blank=True |

Enums:
- `EmploymentType`: FULL_TIME, PART_TIME, CONTRACT, INTERNSHIP
- `Status`: DRAFT, OPEN, CLOSED

##### Application

| Campo | Tipo | Null/Blank |
|-------|------|-----------|
| `job` | ForeignKey(JobPosting, CASCADE) | — |
| `first_name` | CharField(100) | — |
| `last_name` | CharField(100) | — |
| `email` | EmailField | — |
| `phone` | CharField(20) | blank=True |
| `cover_letter` | TextField | blank=True |
| `resume` | FileField(upload_to='hiring/resumes/') | blank=True |
| `status` | CharField(15, choices=Status) | default=RECEIVED |
| `notes` | TextField | blank=True |

Enums para `status`:
- `RECEIVED` → `REVIEWING` → `SHORTLISTED` → `INTERVIEW` → `REJECTED` / `ACCEPTED`

**`Department` e `JobPosting` têm `ForeignKey(Site)` + `on_site`** (isolados por site, migration `0006_site_isolation`). `Application` não tem `Site` próprio — herda da vaga via `job.site`. Currículos usam nome UUID (`resume_upload_path`). Detalhes em [APP_HIRING.md](APP_HIRING.md).

#### Form: ApplicationForm

`clean_resume()`:
```python
ALLOWED_EXTENSIONS = ['.pdf', '.docx']
MAX_SIZE = 5 * 1024 * 1024  # 5 MB

# Valida extensão do nome + tipo MIME real do arquivo
# Rejeita se extensão não permitida ou arquivo > 5MB
```

**Atualização:** `clean_resume` valida em três camadas — tipo MIME, extensão **e magic bytes** (`%PDF-`, `PK\x03\x04`, `\xd0\xcf\x11\xe0`). Os magic bytes são a defesa real, pois MIME e extensão são falsificáveis. Limite de 5 MB. Ver [APP_HIRING.md](APP_HIRING.md) e [SEGURANCA.md](SEGURANCA.md).

#### Views

##### `job_detail`

Antes de salvar candidatura, verifica duplicata por email+vaga:
```python
if Application.objects.filter(job=job, email=form.cleaned_data['email']).exists():
    messages.warning(request, "Você já se candidatou a esta vaga.")
    # Não revela se o email existe em outros contextos — mensagem é para o próprio usuário
```

---

### 4.5 contact

**Localização:** `apps/contact/`

#### Model: ContactInquiry

| Campo | Tipo | Null/Blank |
|-------|------|-----------|
| `site` | ForeignKey(Site, CASCADE) | — |
| `name` | CharField(200) | — |
| `email` | EmailField | — |
| `phone` | CharField(20) | blank=True |
| `subject` | CharField(20, choices=Subject) | default=GENERAL |
| `message` | TextField | — |
| `status` | CharField(10, choices=Status) | default=NEW |

`Subject`: GENERAL, ADMISSIONS, SUPPORT, OTHER  
`Status`: NEW, READ, REPLIED, ARCHIVED

**Sem manager `on_site`** — o site é passado explicitamente na view ao salvar:
```python
inquiry = form.save(commit=False)
inquiry.site = get_current_site(request)
inquiry.save()
```

---

### 4.6 news

**Localização:** `apps/news/`

O app mais complexo do projeto. Contém 7 models, ~20 views, signals, newsletter, feeds, sitemaps.

#### Models

##### Category

| Campo | Tipo | Null/Blank |
|-------|------|-----------|
| `name` | CharField(200) | — |
| `slug` | SlugField(200, unique=True) | — |
| `description` | TextField | blank=True |
| `parent` | ForeignKey('self', SET_NULL) | null=True, blank=True |
| `order` | PositiveIntegerField | default=0 |

Hierarquia de dois níveis. `parent=None` = categoria raiz (aparece na navbar). `parent!=None` = subcategoria.

**Cuidado com queries:** `Category.objects.filter(parent=None)` para navbar. `Category.objects.filter(parent=categoria)` para subcategorias. Sem `select_related('parent')` pode gerar N+1.

##### Tag

| Campo | Tipo |
|-------|------|
| `name` | CharField(200) |
| `slug` | SlugField(200, unique=True) |

##### Article

| Campo | Tipo | Null/Blank |
|-------|------|-----------|
| `title` | CharField(200) | — |
| `slug` | SlugField(200) | unique_together com site |
| `excerpt` | TextField | blank=True |
| `content` | TextField | blank=True |
| `featured_image` | ImageField(upload_to='news/articles/') | blank=True |
| `featured_image_caption` | CharField(200) | blank=True |
| `category` | ForeignKey(Category, SET_NULL) | null=True, blank=True |
| `tags` | ManyToManyField(Tag) | blank=True |
| `author` | ForeignKey(settings.AUTH_USER_MODEL, SET_NULL) | null=True, blank=True |
| `site` | ForeignKey(Site, CASCADE) | — |
| `status` | CharField(10, choices=Status) | default=DRAFT |
| `published_at` | DateTimeField | null=True, blank=True |
| `is_featured` | BooleanField | default=False |
| `view_count` | PositiveIntegerField | default=0 |
| `newsletter_sent_at` | DateTimeField | null=True, blank=True |
| `meta_title` | CharField(70) | blank=True |
| `meta_description` | CharField(160) | blank=True |
| `meta_keywords` | CharField(255) | blank=True |

`Status`: DRAFT, PUBLISHED, ARCHIVED

Managers: `objects = Manager()`, `on_site = CurrentSiteManager()`

**Propriedades calculadas:**
```python
@property
def reading_time(self) -> int:
    # word_count / 200 — tempo em minutos
```

**`save()` lifecycle:**
1. `self.content = sanitize_content(self.content)`
2. Se `status=PUBLISHED` e `published_at is None`: `self.published_at = timezone.now()`
3. `super().save()`
4. Signal `post_save` dispara → newsletter (se primeira publicação)

**Atenção:** Chamar `article.save()` em código após mudança de status para PUBLISHED dispara o signal de newsletter. Para evitar, use `Article.objects.filter(pk=article.pk).update(field=value)`.

##### NewsletterSubscription

| Campo | Tipo |
|-------|------|
| `email` | EmailField |
| `is_active` | BooleanField |
| `site` | ForeignKey(Site, CASCADE) |

`unique_together = [['email', 'site']]` — o mesmo email pode assinar portais diferentes.

##### ArticleLike

| Campo | Tipo | Null/Blank |
|-------|------|-----------|
| `article` | ForeignKey(Article, CASCADE) | — |
| `user` | ForeignKey(User, CASCADE) | null=True |
| `ip_address` | GenericIPAddressField | null=True |
| `session_key` | CharField(40) | null=True |

`unique_together = [['article', 'ip_address', 'session_key', 'user']]` — previne dupla curtida.

##### Comment

| Campo | Tipo | Null/Blank |
|-------|------|-----------|
| `article` | ForeignKey(Article, CASCADE) | — |
| `user` | ForeignKey(User, CASCADE) | — |
| `content` | TextField | — |
| `is_active` | BooleanField | default=True |

Ordering: `[-created_at]`. Comentários inativos não são exibidos mas persistem no banco.

##### ArticleBookmark

| Campo | Tipo |
|-------|------|
| `article` | ForeignKey(Article, CASCADE) |
| `user` | ForeignKey(User, CASCADE) |

`unique_together = [['article', 'user']]`

#### Views — Mapa Completo

| View | Método | URL | Auth | HTMX |
|------|--------|-----|------|------|
| `article_list` | GET | `/news/` | — | — |
| `article_detail` | GET | `/news/<slug>/` | — | — |
| `category_detail` | GET | `/news/category/<slug>/` | — | — |
| `tag_detail` | GET | `/news/tag/<slug>/` | — | — |
| `author_detail` | GET | `/news/author/<username>/` | — | — |
| `article_search` | GET | `/news/search/` | — | — |
| `article_archive` | GET | `/news/archive/<year>/[<month>/]` | — | — |
| `article_list_page` | GET | `/news/htmx/articles/` | — | ✓ |
| `newsletter_subscribe` | POST | `/news/newsletter/subscribe/` | — | — |
| `user_dashboard` | GET | `/news/account/` | ✓ | — |
| `toggle_bookmark` | POST | `/news/toggle-bookmark/<id>/` | ✓ | ✓ |
| `toggle_like` | POST | `/news/toggle-like/<id>/` | ✓ | ✓ |
| `add_comment` | POST | `/news/comment/<id>/` | ✓ | ✓ |
| `delete_comment` | POST | `/news/delete-comment/<id>/` | ✓ | ✓ |
| `newsletter_preview` | GET | `/news/newsletter/preview/<id>/` | staff | — |

**`article_detail` — lógica de view_count:**
```python
session_key = f'viewed_article_{article.pk}'
if not request.session.get(session_key):
    Article.objects.filter(pk=article.pk).update(view_count=F('view_count') + 1)
    request.session[session_key] = True
```

Usa `F()` para update atômico (thread-safe). Usa sessão para não incrementar em reload.

**`article_search` — campos pesquisados:**
```python
Q(title__icontains=q) |
Q(excerpt__icontains=q) |
Q(content__icontains=q) |
Q(tags__name__icontains=q) |
Q(category__name__icontains=q) |
Q(author__username__icontains=q)
```

Não usa full-text search do PostgreSQL — usa LIKE. Para volumes maiores, migrar para `SearchVector`/`SearchRank` do Django.

#### Newsletter (`apps/news/newsletter.py`)

> ⚠️ **Modelo atual = fila de entregas (`NewsletterDelivery`), não envio síncrono.** Documento canônico: **[FLUXO_NEWSLETTER.md](FLUXO_NEWSLETTER.md)**.

Funções principais (todas em `apps/news/newsletter.py`):

- **`process_pending_newsletters(...)`** — ponto de entrada. Enfileira entregas pendentes para artigos publicados ainda não concluídos, envia até `batch_size`, e marca artigos completos. Aceita `site_id`, `article_id`, `retry_failed`, `dry_run`, `include_marked_sent`.
- **`enqueue_article_newsletter(article)`** — cria `NewsletterDelivery` PENDING (via `get_or_create`) para cada inscrito ativo do site do artigo.
- **`send_newsletter_delivery(delivery)`** — envia uma entrega (`EmailMultiAlternatives` HTML+texto); isola falhas por destinatário (`SENT`/`FAILED`/`SKIPPED`).
- **`_mark_article_if_complete(article_id)`** — carimba `newsletter_sent_at` só quando não há entrega `pending`/`failed` em aberto.
- **`send_article_newsletter(article)`** — wrapper de compatibilidade; retorna a contagem de enviados.

**`get_newsletter_context(article, site=None, request=None, subscription=None)`** — determina `base_url`:
- Com `request` (preview do admin): `request.get_host()` (links navegáveis no browser).
- Sem `request` (envio real): `f"{protocol}://{site.domain}"` — depende do `domain` correto no banco.

**Ponto crítico:** Se o `domain` do `Site` estiver incorreto (ex: `example.com`), os links do e-mail quebram. Verificar em `admin → Sites`.

#### Signals (`apps/news/signals.py`)

> ⚠️ O signal **não envia e-mail**. Ele apenas registra que há newsletter pendente. O envio é feito depois, pela fila (ver [FLUXO_NEWSLETTER.md](FLUXO_NEWSLETTER.md)).

```python
@receiver(post_save, sender=Article)
def mark_newsletter_pending_on_publish(sender, instance, **kwargs):
    if instance.status != Article.Status.PUBLISHED:
        return
    if instance.newsletter_sent_at is not None:
        return
    logger.info('Newsletter pendente para artigo pk=%s ... Rode send_pending_newsletters para processar.', ...)
```

**Por que não envia no signal:** publicar não deve bloquear a request do admin enviando e-mails. O signal só sinaliza "pendente"; o disparo real é o comando `send_pending_newsletters` (cron) ou a ação do admin, ambos processando a fila `NewsletterDelivery` em lote, com isolamento de falha por destinatário.

#### Feeds (`apps/news/feeds.py`)

- `LatestArticlesFeed` — `/news/feed/` — últimos 20 artigos publicados
- `CategoryFeed` — `/news/category/<slug>/feed/` — artigos da categoria

Ambos usam `Article.on_site` para filtrar por site atual.

#### Utilitários (`apps/news/utils.py`)

`get_sidebar_context()`:
```python
{
    'popular_articles': Article.on_site.filter(status=PUBLISHED).order_by('-view_count')[:5],
    'top_categories': Category.objects.annotate(count=Count('article')).order_by('-count')[:10],
    'top_tags': Tag.objects.annotate(count=Count('article')).order_by('-count')[:20],
}
```

**Atenção:** `top_categories` e `top_tags` não filtram por site — contam artigos de todos os sites.

#### Sitemap

`ArticleSitemap` retorna `Article.on_site.filter(status=PUBLISHED)`. `changefreq='weekly'`, `priority=0.8`.

#### Admin — Funcionalidades Especiais

**`ArticleAdmin.send_newsletter` action:**
- Chama `send_article_newsletter(article)` para cada artigo selecionado
- Não verifica `newsletter_sent_at` — permite re-envio manual
- Diferente do signal automático que verifica

**`NewsletterSubscriptionAdmin.export_emails` action:**
- Só disponível para superuser (`if not request.user.is_superuser: return`)
- Gera CSV com todos os emails ativos
- Content-Disposition: attachment — força download

---

### 4.7 media_library

**Localização:** `apps/media_library/`

#### Models

##### MediaFolder

| Campo | Tipo | Null/Blank |
|-------|------|-----------|
| `name` | CharField(200) | — |
| `parent` | ForeignKey('self', SET_NULL) | null=True, blank=True |

Hierarquia de pastas. Sem limite de profundidade.

##### MediaFile

| Campo | Tipo | Null/Blank |
|-------|------|-----------|
| `title` | CharField(255) | — |
| `file` | FileField(upload_to='media_library/files/') | — |
| `file_type` | CharField(10, choices=FileType) | — |
| `alt_text` | CharField(255) | blank=True |
| `folder` | ForeignKey(MediaFolder, SET_NULL) | null=True, blank=True |
| `uploaded_by` | ForeignKey(User, SET_NULL) | null=True, blank=True |
| `file_size` | PositiveIntegerField | default=0 |

`FileType`: IMAGE, DOCUMENT, VIDEO, AUDIO, OTHER

**`file_size` não é populado automaticamente** — precisa ser definido antes de salvar. O admin não faz isso automaticamente (campo manual ou precisa de signal/override de save).

---

## 5. URL Routing

### Roteamento Raiz (`config/urls.py`)

```python
urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': {'articles': ArticleSitemap, 'pages': PageSitemap}}),
    path('hiring/', include('apps.hiring.urls', namespace='hiring')),
    path('contact/', include('apps.contact.urls', namespace='contact')),
    path('news/', include('apps.news.urls', namespace='news')),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('', include('apps.school.urls', namespace='school')),  # catch-all
]
```

**Ordem importa:** `school` é o último — captura tudo que não bater nos anteriores. Qualquer novo app deve ser adicionado **antes** da linha `school`.

**Colisão de URLs:** O padrão `<slug:slug>/` em `school/urls.py` pode colidir com prefixos de outros apps se eles não forem declarados antes. Debug: `python manage.py show_urls`.

### Namespaces por App

| App | Namespace | Exemplo de reverse |
|-----|-----------|-------------------|
| school | `school` | `{% url 'school:home' %}` |
| news | `news` | `{% url 'news:article_detail' article.slug %}` |
| hiring | `hiring` | `{% url 'hiring:job_list' %}` |
| contact | `contact` | `{% url 'contact:contact_page' %}` |
| accounts | `accounts` | `{% url 'accounts:login' %}` |

---

## 6. Template Engine

### Hierarquia de Herança

```
base.html
├── base_news.html        (portal de notícias)
│   ├── article_list.html
│   ├── article_detail.html
│   └── ...
└── base_school.html      (portal da escola)
    ├── home.html
    ├── page_detail.html
    └── ...
```

### Diretório de Templates

Django resolve templates com `APP_DIRS=True` + `DIRS=['templates']`. Busca em:
1. `templates/` (raiz do projeto)
2. `apps/<app>/templates/` (se `APP_DIRS=True`)

Todos os templates estão na raiz `templates/` — não em `apps/<app>/templates/`.

### Componentes Reutilizáveis

```
templates/
├── components/
│   ├── navbar.html
│   ├── navbar_news.html
│   ├── navbar_school.html
│   ├── footer.html
│   ├── footer_news.html
│   └── footer_school.html
└── news/
    └── partials/
        ├── article_card.html       # Card individual de artigo
        ├── article_list.html       # Grid de artigos (HTMX load-more)
        ├── comment_form.html       # Form de comentário
        ├── like_button.html        # Botão de curtida
        ├── bookmark_button.html    # Botão de bookmark
        ├── newsletter_form.html    # Form de newsletter
        └── search_results.html     # Resultados de busca
```

Partials são retornados por views quando `request.htmx` é True.

### Filtros de Template Disponíveis

Além dos built-ins Django:
- `{{ content|sanitize_html }}` — sanitiza HTML (de `apps/common/templatetags/sanitize`)

**Nunca use `|safe`** — todo HTML de usuário deve passar por `|sanitize_html`.

---

## 7. Banco de Dados

### Configuração

**Desenvolvimento:** PostgreSQL 16-alpine via Docker Compose.

**Produção:** PostgreSQL 16-alpine via Docker Compose (separado). Dados persistidos em volume nomeado.

**Testes:** SQLite in-memory (`:memory:`). Sem migrations reais — usa `--no-migrations` implícito do pytest-django? Não — usa migrations normais mas em SQLite.

### Constraints Críticas no Schema

| Tabela | Constraint | Tipo |
|--------|-----------|------|
| `accounts_customuser` | `email` | UNIQUE |
| `news_article` | `(slug, site_id)` | unique_together |
| `news_newslettersubscription` | `(email, site_id)` | unique_together |
| `news_articlelike` | `(article_id, ip_address, session_key, user_id)` | unique_together |
| `news_articlebookmark` | `(article_id, user_id)` | unique_together |

### Migrações — Contagem por App

| App | Total | Última |
|-----|-------|--------|
| accounts | 3 | email_unique |
| common | 4 | newsletter_fields |
| school | 4 | on_site_manager |
| hiring | 4 | meta_description |
| contact | 3 | meta_options |
| news | 10 | newsletter_sent_at |
| media_library | 1 | initial |

**Total de migrations custom:** 29

### Índices Implícitos

Django cria índices automáticos para:
- Toda `ForeignKey` (db_index=True por padrão)
- Todo campo com `unique=True`
- Todo `SlugField` (db_index=True por padrão)

Para análise de queries lentas: `EXPLAIN ANALYZE` no PostgreSQL ou `django-debug-toolbar` em dev.

---

## 8. Segurança

### Camadas de Proteção

| Ameaça | Proteção | Onde |
|--------|---------|------|
| XSS | bleach sanitization | `apps/common/sanitization.py` → `save()` de models |
| XSS em templates | `sanitize_html` filter, nunca `\|safe` | Templates |
| CSRF | `CsrfViewMiddleware` + `{% csrf_token %}` | Middleware + templates |
| SQL Injection | Django ORM parametrizado | ORM (não usa raw SQL) |
| Brute-force login | `django-axes` (5 tentativas, 30min lockout) | `AxesMiddleware` |
| Password reset mailbomb | Rate limiting por IP+email (15min) | `CustomPasswordResetView` |
| Host header poisoning | `domain_override` no reset de senha | `CustomPasswordResetView` |
| Clickjacking | `XFrameOptionsMiddleware` (DENY) + nginx | Middleware + nginx |
| User enumeration | Mensagens genéricas em auth, registro, vagas | Views |
| Session hijacking | HTTPONLY + SECURE cookies (prod) | `production.py` |
| HTTPS downgrade | HSTS (1 ano, preload) + SECURE_SSL_REDIRECT | `production.py` |
| File upload malicioso | Validação extensão + MIME (hiring) | `ApplicationForm.clean_resume` |
| Iframe injection | Whitelist YouTube em bleach | `sanitization.py` |
| CSP bypass | CSP headers (Django + nginx) | `base.py` + `nginx.conf` |
| Scrapers/bots | Rate limiting no nginx (10 req/s) | `nginx.conf` |
| Container root | Non-root user (appuser:1000) | `Dockerfile` |

### Mensagens de Erro — Política

**Nunca revelar** se email/username existe. Exemplos aplicados:

```python
# Em CustomPasswordResetView — mesmo comportamento se email existe ou não
# Django padrão já faz isso

# Em register_view — mensagem de email duplicado
"Este endereço de email já está em uso."  # Genérico — não confirma existência

# Em job_detail — duplicata de candidatura
"Você já se candidatou a esta vaga."  # OK — o usuário está logado, não é enumeration
```

### Upload de Arquivos

`hiring/resumes/` — aceita PDF e DOCX, máximo 5MB. Validação em `ApplicationForm.clean_resume()`.

**Localização no servidor:** `MEDIA_ROOT/hiring/resumes/`. Servido por nginx com cache de 7 dias.

**Atenção:** Não há antivirus scan. Para produção em ambiente sensível, considerar ClamAV ou serviço externo.

---

## 9. Sistema de Email

### Backends por Ambiente

| Ambiente | Backend | Destino |
|----------|---------|---------|
| development | `ConsoleEmailBackend` | Terminal |
| dev com Docker | `SMTPEmailBackend` | Mailpit (localhost:1025) |
| production | `SMTPEmailBackend` | Servidor SMTP real |
| test | `LocMemEmailBackend` | `django.test.utils.get_connection` |

### Fluxos de Email

1. **Newsletter de artigo** — fila (`NewsletterDelivery`) processada pelo comando `send_pending_newsletters` (cron) ou pela ação do admin. Publicar apenas marca como pendente. Ver [FLUXO_NEWSLETTER.md](FLUXO_NEWSLETTER.md)
2. **Password reset** — link com token de 1 hora
3. **Notificações admin** — não implementadas ainda

### Remetente da Newsletter

Lógica em `apps/news/newsletter.py`:
```python
def get_from_email(site_settings):
    name = site_settings.newsletter_from_name or site_settings.site.name
    email = site_settings.newsletter_from_email or settings.DEFAULT_FROM_EMAIL
    return f'"{name}" <{email}>'
```

Se `SiteExtension` não tiver campos de newsletter preenchidos, cai para `DEFAULT_FROM_EMAIL`.

---

## 10. Infraestrutura Docker/Nginx

### Dockerfile

```dockerfile
FROM python:3.12-slim
# Sistema: libpq-dev, gcc (para psycopg3 compilado)
# Cria usuário não-root: appuser (UID 1000)
# WORKDIR /app
# Instala requirements/development.txt (não production.txt — build único)
```

**Atenção:** O Dockerfile instala `requirements/development.txt`. Para produção, o `DJANGO_SETTINGS_MODULE` é sobrescrito no `docker-compose.prod.yml`, mas as dependências de dev (debug-toolbar, etc.) ficam instaladas. Não é um problema de segurança — `DEBUG=False` desativa o toolbar — mas aumenta o tamanho da imagem.

### Docker Compose — Desenvolvimento

```yaml
services:
  web:
    build: .
    ports: ["8000:8000"]
    volumes: [".:/app"]      # Hot reload via volume mount
    command: python manage.py runserver 0.0.0.0:8000
    
  db:
    image: postgres:16-alpine
    healthcheck: pg_isready -U news_portal_user
    
  mailpit:
    image: axllent/mailpit
    ports: ["8025:8025", "1025:1025"]
```

### Docker Compose — Produção

```yaml
services:
  web:
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 2
    volumes: [static_volume, media_volume]   # Sem volume mount de código
    
  nginx:
    ports: ["80:80", "443:443"]
    volumes: [nginx.conf, static_volume, media_volume, certbot_certs]
```

**Workers Gunicorn:** 4 workers × 2 threads = 8 requisições simultâneas. Para mais carga, aumentar `--workers` (regra: 2×CPU+1).

### Nginx — Configuração Crítica

```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
limit_req zone=general burst=20 nodelay;

# Upload limit
client_max_body_size 10M;

# Static files — serve direto, sem passar pelo Gunicorn
location /static/ {
    alias /app/staticfiles/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}

# Media files
location /media/ {
    alias /app/media/;
    expires 7d;
}
```

**`server_name _`** — catch-all até domínio real ser configurado. Em produção, substituir por domínio real.

**TLS/HTTPS:** Configurado para Certbot/Let's Encrypt. Certificados em `certbot/conf/` (volume). Renovação automática via `/.well-known/acme-challenge/`.

---

## 11. Dependências Externas

### Críticas (quebram o sistema se removidas)

| Pacote | Versão mínima | Função |
|--------|--------------|--------|
| Django | 5.1 | Framework base |
| psycopg | 3.1 | Driver PostgreSQL |
| django-unfold | 0.40 | Admin UI — ImportError se ausente |
| bleach | 6.0 | Sanitização HTML — risco XSS se ausente |
| django-axes | 6.0 | Brute-force protection |
| django-csp | 4.0 | CSP headers |
| Pillow | 10.0 | Processamento de imagens (ImageField) |
| whitenoise | 6.5 | Serve arquivos estáticos |
| django-environ | 0.11 | Leitura de .env |

### Notas de Compatibilidade

**django-unfold >= 0.40:** A configuração do dashboard usa `DASHBOARD_CALLBACK` (não `INDEX_DASHBOARD`). Versões antigas do Unfold usavam chave diferente. Verificar changelog em atualizações.

**bleach:** Versão 6.x mudou a API de `css_sanitizer`. Não atualizar sem testar sanitização.

**django-axes:** Integração com middleware — posição na chain crítica (ver seção 2).

---

## 12. Sinais e Efeitos Colaterais

### post_save em Article

**Arquivo:** `apps/news/signals.py`  
**Registrado em:** `apps/news/apps.py` via `ready()` (assumido — padrão Django)

```
Article.save() com status=PUBLISHED e newsletter_sent_at=None
    └─► post_save signal
        └─► mark_newsletter_pending_on_publish()
            └─► logger.info("Newsletter pendente...")   # SÓ registra; NÃO envia

Envio real (separado): comando send_pending_newsletters OU ação do admin
    └─► process_pending_newsletters() → fila NewsletterDelivery → SMTP em lote
```

**Efeitos colaterais ao salvar um artigo:**
1. `content` é sanitizado (no `save()` do model)
2. `published_at` é setado se primeira publicação
3. Newsletter é apenas **marcada como pendente** (via signal) — o envio é uma etapa separada (fila)

**Para pular o signal ao publicar** (ex: em testes, migrações):
```python
# Opção 1: usar .update() em vez de .save()
Article.objects.filter(pk=pk).update(status='PUBLISHED', published_at=now())

# Opção 2: setar newsletter_sent_at antes
article.newsletter_sent_at = timezone.now()
article.status = 'PUBLISHED'
article.save()  # Signal verifica newsletter_sent_at e pula
```

---

## 13. Context Processors

Registrados em `TEMPLATES[0]['OPTIONS']['context_processors']` de `base.py`:

```python
'apps.common.context_processors.site_context',
'apps.common.context_processors.news_nav_context',
```

Variáveis disponíveis em **todos** os templates:
- `current_site` — `django.contrib.sites.Site` instance
- `site_settings` — `SiteExtension` instance (criado automaticamente se não existir)

Variáveis disponíveis **apenas em `/news/**`**:
- `nav_categories` — QuerySet de categorias pai

**Debug de context:** Em dev com `django-debug-toolbar`, a tab "Templates" mostra o context completo de cada template.

---

## 14. Diagnóstico e Debugging

### Checklist para Bug Reports

1. **Qual ambiente?** Dev (Docker), dev (local), prod?
2. **Settings ativo?** `python -c "import django; print(django.conf.settings.DATABASES)"`
3. **Migrações pendentes?** `python manage.py showmigrations | grep '\[ \]'`
4. **Qual Site está ativo?** `python manage.py shell -c "from django.contrib.sites.models import Site; print(Site.objects.get_current())"`

### Problemas Comuns

#### Newsletter não enviada ao publicar artigo

1. Verificar `Article.newsletter_sent_at` — se preenchido, já foi enviado
2. Verificar se signal está registrado: `apps/news/apps.py` deve ter `ready()` com `import apps.news.signals`
3. Verificar configuração de email no settings ativo
4. Verificar logs: `logging.getLogger('apps.news.signals')` e `apps.news.newsletter`

#### Dashboard admin vazio/erro 500

1. Verificar `apps/common/dashboard.py` — queries podem falhar se models não migrados
2. Verificar `UNFOLD['DASHBOARD_CALLBACK']` em settings — deve apontar para `apps.common.dashboard.dashboard_callback`
3. **Não usar** `INDEX_DASHBOARD` — chave errada do Unfold

#### Artigo aparece em portal errado

1. Verificar `Article.site` — deve ser o site correto
2. Verificar se view usa `Article.on_site` e não `Article.objects`
3. Verificar `SITE_ID` no settings ativo
4. Verificar `request.site` no shell: `from django.contrib.sites.shortcuts import get_current_site`

#### CSS do admin quebrado / Tailwind não carregando

1. Unfold compila Tailwind internamente — sem CDN externo
2. Se override de CSS não funciona: verificar `static/admin/css/overrides.css` foi collectado
3. **Nunca adicionar CDN externo** em templates admin — viola CSP e padrão do projeto

#### Login bloqueado por Axes

```python
# Para desbloquear um usuário/IP no shell
from axes.models import AccessAttempt
AccessAttempt.objects.filter(username='user@email.com').delete()

# Ou via management command
python manage.py axes_reset_username --username user@email.com
python manage.py axes_reset_ip --ip 192.168.1.1
```

#### Uploads de arquivo falhando

1. `MEDIA_ROOT` existe e tem permissão de escrita?
2. `client_max_body_size` no nginx (10MB limite)
3. Django `DATA_UPLOAD_MAX_MEMORY_SIZE` (padrão 2.5MB)

#### View retornando dados de múltiplos sites

Query usando `Article.objects` em vez de `Article.on_site`. Buscar no código por `Article.objects.filter` ou `Article.objects.get` em views.

### Ferramentas de Debug em Desenvolvimento

```bash
# Inspecionar queries de uma view
# Via debug-toolbar: barra lateral no browser

# Via shell
from django.test.utils import override_settings
from django.db import connection
# ... executar código ...
print(connection.queries)

# Ver todas as URLs
python manage.py show_urls

# Shell com models auto-importados
python manage.py shell_plus

# Inspecionar migrations
python manage.py sqlmigrate news 0010
python manage.py showmigrations
```

### Logs

Em produção, configurar `LOGGING` em `production.py` para escrever em arquivo ou enviar para Sentry (dependência já instalada em `requirements/production.txt`).

Em desenvolvimento, logs vão para stdout (console do Docker ou terminal).

Loggers usados pelo projeto:
- `apps.news.signals` — envio automático de newsletter
- `apps.news.newsletter` — detalhes de envio (sucesso/falha por email)
- `apps.accounts` — eventos de autenticação (se configurado)
