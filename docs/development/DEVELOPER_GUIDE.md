# Developer Guide — news_portal

> Guia de onboarding para novos desenvolvedores. Assume familiaridade com Django e Python.

---

## O Que É Este Projeto

news_portal é um sistema multi-portal construído em Django 5.1+. Ele serve dois portais a partir do mesmo codebase:

| Portal | URL Base | Propósito |
|--------|----------|-----------|
| Escola | `/` | Site institucional da escola |
| Notícias | `/news/` | Portal de notícias com newsletter |

Ambos compartilham o mesmo banco de dados, admin, e sistema de usuários — mas são isolados logicamente via **Django Sites Framework** (`django.contrib.sites`). Cada portal tem seu próprio `Site` com `SITE_ID` diferente.

---

## Setup Rápido

### Pré-requisitos

- Docker + Docker Compose
- Python 3.12+ (se rodar sem Docker)

### Rodando com Docker (recomendado)

```bash
# Copiar .env de exemplo
cp .env.example .env   # editar conforme necessário

# Subir serviços (Django + PostgreSQL + Mailpit)
docker compose up

# Em outro terminal — criar tabelas e superuser
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Acesse:
- **App:** http://localhost:8000
- **Admin:** http://localhost:8000/admin
- **Email (Mailpit):** http://localhost:8025

### Rodando sem Docker

```bash
# Criar e ativar virtualenv
python -m venv .venv
source .venv/bin/activate

# Instalar dependências de desenvolvimento
pip install -r requirements/development.txt

# Configurar variáveis de ambiente
cp .env.example .env   # editar DB_* para apontar pro seu PostgreSQL

# Ou usar SQLite local (sem PostgreSQL)
export DJANGO_SETTINGS_MODULE=config.settings.local_sqlite

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## Estrutura de Diretórios

```
news_portal/
├── apps/                   # Apps Django custom
│   ├── accounts/           # Autenticação e usuários
│   ├── common/             # Utilitários compartilhados (models abstratos, sanitização)
│   ├── contact/            # Formulários de contato
│   ├── hiring/             # Vagas e candidaturas
│   ├── media_library/      # Biblioteca de mídia
│   ├── news/               # Portal de notícias (artigos, newsletter, comentários)
│   └── school/             # Site da escola (páginas, equipe, depoimentos)
├── config/
│   ├── settings/           # Configurações por ambiente
│   │   ├── base.py         # Base comum a todos
│   │   ├── development.py  # Dev (SQLite, debug toolbar)
│   │   ├── production.py   # Prod (PostgreSQL, HTTPS, HSTS)
│   │   ├── test.py         # Testes (in-memory, MD5 hasher)
│   │   └── local_sqlite.py # Dev alternativo com SQLite
│   ├── urls.py             # Roteamento raiz
│   ├── wsgi.py
│   └── asgi.py
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml      # Desenvolvimento
│   ├── docker-compose.prod.yml # Produção
│   └── nginx/nginx.conf
├── templates/              # Templates HTML (organizados por app)
├── static/                 # CSS, JS, imagens estáticas
├── media/                  # Uploads de usuários (não versionar)
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
└── manage.py
```

---

## Apps — O Que Cada Um Faz

### `apps/common` — Base de tudo

Contém os models abstratos que todos os outros herdam:

- **`TimeStampedModel`** — adiciona `created_at` e `updated_at` automaticamente. Herde sempre que o model precisar de timestamps.
- **`SEOModel`** — adiciona `meta_title`, `meta_description`, `meta_keywords`. Use em modelos com páginas públicas.
- **`SiteExtension`** — configurações por site (logo, favicon, emails, redes sociais).

Também contém:
- `apps/common/sanitization.py` — **toda** sanitização HTML passa por aqui. Nunca use `bleach` diretamente em outro app.
- `apps/common/templatetags/sanitize.py` — filtro de template `{{ content|sanitize_html }}`.
- `apps/common/context_processors.py` — injeta `current_site` e `site_settings` em todos os templates.
- `apps/common/dashboard.py` — callback do dashboard do admin.

### `apps/accounts` — Usuários

`CustomUser` estende `AbstractUser` com `role` (enum), `avatar` e `bio`. Autenticação usa email único.

Funcionalidades:
- Login/logout/registro
- Recuperação de senha (com rate limiting para anti-mailbomb)
- Deleção de conta com confirmação de senha
- Toggle de newsletter (subscribe/unsubscribe)

### `apps/school` — Portal da Escola

Gerencia páginas dinâmicas, time, e depoimentos. Conteúdo filtrado por site via `CurrentSiteManager`.

### `apps/news` — Portal de Notícias

O app mais complexo. Contém:
- Artigos com categorias hierárquicas, tags, autores
- Sistema de newsletter (envio manual via admin ou automático ao publicar)
- Comentários, curtidas, bookmarks (HTMX)
- Feed RSS por categoria
- Sitemap
- Dashboard do usuário (artigos salvos, curtidos, comentados)

### `apps/hiring` — Vagas

Vagas por departamento com pipeline de candidaturas (RECEIVED → REVIEWING → SHORTLISTED → INTERVIEW → REJECTED/ACCEPTED).

### `apps/contact` — Contato

Formulário de contato multi-site com status (NEW → READ → REPLIED → ARCHIVED).

### `apps/media_library` — Mídia

Biblioteca centralizada de arquivos com pastas. Integrada ao admin.

---

## Padrões do Projeto

### Models

```python
# Sempre herde de TimeStampedModel e SEOModel quando aplicável
class Article(TimeStampedModel, SEOModel):
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    
    # Models com ForeignKey(Site) precisam de CurrentSiteManager
    objects = models.Manager()
    on_site = CurrentSiteManager()
```

**Regra:** `on_site` é o manager padrão em views/feeds/sitemaps. `objects` é só para admin ou migrations.

### Views

Todas as views são **Function-Based Views (FBV)**. Não migre para CBV — é decisão arquitetural permanente.

```python
def article_detail(request, slug):
    article = get_object_or_404(
        Article.on_site.select_related('author', 'category'),
        slug=slug,
        status=Article.Status.PUBLISHED
    )
    
    # HTMX: cheque antes de renderizar
    if request.htmx:
        return render(request, 'news/partials/article_card.html', context)
    
    return render(request, 'news/article_detail.html', context)
```

**Regras:**
- `get_object_or_404()` para objetos públicos
- `select_related()` / `prefetch_related()` em qualquer query com FK/M2M
- `F()` para updates atômicos (ex: `view_count`)
- Paginação padrão: 12 itens

### Templates

```html
<!-- Estenda a base correta para o portal -->
{% extends "base_news.html" %}   {# notícias #}
{% extends "base_school.html" %} {# escola #}

<!-- Nunca use |safe — use o filtro customizado -->
{{ article.content|sanitize_html }}

<!-- Imagens com lazy loading (exceto hero/above the fold) -->
<img src="{{ article.image.url }}" loading="lazy" alt="{{ article.title }}">

<!-- Sempre use {% url %} — nunca hardcode links -->
<a href="{% url 'news:article_detail' article.slug %}">{{ article.title }}</a>
```

### Admin

```python
# Sempre importe de unfold.admin — nunca de django.contrib.admin
from unfold.admin import ModelAdmin

@admin.register(Article)
class ArticleAdmin(ModelAdmin):
    list_display = ['title', 'status', 'published_at']
    list_filter = ['status', 'category']
    search_fields = ['title', 'excerpt']
    prepopulated_fields = {'slug': ('title',)}
    
    # Fieldsets SEMPRE em PT-BR
    fieldsets = (
        ('Conteúdo', {'fields': ('title', 'slug', 'content')}),
        ('SEO', {'classes': ('collapse',), 'fields': ('meta_title', 'meta_description')}),
    )
```

### Sanitização HTML

```python
# No save() do model — sempre sanitize conteúdo HTML do usuário
from apps.common.sanitization import sanitize_content

class Article(TimeStampedModel):
    def save(self, *args, **kwargs):
        self.content = sanitize_content(self.content)
        super().save(*args, **kwargs)
```

### Segurança — Regras Críticas

1. **Nunca revele existência de email/usuário** em mensagens de erro. Use mensagens genéricas.
2. **Nunca use `|safe`** nos templates. Use `|sanitize_html`.
3. **Nunca use `Article.objects`** em views públicas — use `Article.on_site`.
4. **Sempre valide** extensão + MIME em uploads de arquivo.

---

## Adicionando um Novo App

```bash
# 1. Criar estrutura
mkdir -p apps/meuapp
touch apps/meuapp/{__init__,models,views,admin,urls,apps,tests}.py
mkdir -p apps/meuapp/migrations
touch apps/meuapp/migrations/__init__.py
```

```python
# 2. apps/meuapp/apps.py
from django.apps import AppConfig

class MeuappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.meuapp'
    verbose_name = 'Meu App'
```

```python
# 3. Registrar em config/settings/base.py
INSTALLED_APPS = [
    ...
    'apps.meuapp',
]

# 4. Registrar URLs em config/urls.py
urlpatterns = [
    ...
    path('meuapp/', include('apps.meuapp.urls', namespace='meuapp')),
]
```

Checklist adicional:
- [ ] Se tiver conteúdo multi-site: `ForeignKey(Site)` + `CurrentSiteManager`
- [ ] Se tiver HTML do usuário: sanitizar no `save()` via `sanitize_content()`
- [ ] Admin em PT-BR com todas as convenções
- [ ] URLs com namespace

---

## Fluxo de Newsletter

1. Artigo é salvo com `status=PUBLISHED` pela primeira vez
2. Signal `post_save` em `apps/news/signals.py` detecta o publish
3. Chama `send_article_newsletter(article)` de `apps/news/newsletter.py`
4. Envia email para todos `NewsletterSubscription.objects.filter(site=article.site, is_active=True)`
5. Atualiza `newsletter_sent_at` com `.update()` (evita re-trigger do signal)

Para enviar manualmente: admin → Artigos → selecione → action "Enviar newsletter".

Para preview: `/news/newsletter/preview/<id>/` (requer staff).

---

## Deploy em Produção

```bash
# 1. Copiar e configurar .env.prod
cp .env.example .env.prod

# 2. Subir serviços
docker compose -f docker-compose.prod.yml up -d

# 3. Rodar migrations + collectstatic
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# 4. Criar superuser
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

O nginx serve arquivos estáticos e de mídia diretamente, com cache de 30 e 7 dias respectivamente.

---

## Variáveis de Ambiente (.env)

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `SECRET_KEY` | Sim | Django secret key |
| `DEBUG` | Sim | `True` em dev, `False` em prod |
| `ALLOWED_HOSTS` | Sim | Hosts separados por vírgula |
| `DB_NAME` | Sim | Nome do banco |
| `DB_USER` | Sim | Usuário do banco |
| `DB_PASSWORD` | Sim | Senha do banco |
| `DB_HOST` | Sim | Host do banco |
| `DB_PORT` | Sim | Porta do banco (padrão 5432) |
| `EMAIL_HOST` | Prod | Servidor SMTP |
| `EMAIL_HOST_USER` | Prod | Usuário SMTP |
| `EMAIL_HOST_PASSWORD` | Prod | Senha SMTP |
| `DEFAULT_FROM_EMAIL` | Prod | Email remetente padrão |
| `CSRF_TRUSTED_ORIGINS` | Prod | Domínios confiáveis para CSRF |

---

## Ferramentas de Desenvolvimento

| Ferramenta | Uso |
|------------|-----|
| `ruff` | Linter/formatter. Config em `pyproject.toml` |
| `pytest-django` | Testes. Rodar com `pytest` |
| `django-debug-toolbar` | Profiling de queries (só em dev) |
| `django-browser-reload` | Hot reload em dev |
| `django-extensions` | Comandos extras (`shell_plus`, `show_urls`) |
| `factory-boy` | Fixtures para testes |
| Mailpit | Captura emails em dev — acesse em localhost:8025 |

```bash
# Ver todas as URLs registradas
python manage.py show_urls

# Shell com auto-import dos models
python manage.py shell_plus

# Rodar linter
ruff check .

# Rodar testes
pytest
```

---

## FAQ

**Por que FBV e não CBV?**
Decisão arquitetural permanente para consistência. O codebase inteiro usa FBVs — não mude.

**Por que `bleach` em `common/sanitization.py` e não direto?**
Centralização intencional. A lista de tags/atributos permitidos precisa ser consistente em todo o projeto. Se precisar ajustar, muda em um lugar só.

**Por que `on_site` e não `objects` nas views?**
`CurrentSiteManager` filtra automaticamente pelo `SITE_ID` atual. Usar `objects` retornaria dados de todos os sites — grave em produção multi-site.

**Como adicionar uma nova categoria de navbar no portal de notícias?**
As categorias são carregadas dinamicamente por `news_nav_context` em `apps/common/context_processors.py`. Basta criar uma categoria parent no admin — ela aparece automaticamente.

**O dashboard admin não mostra meus dados novos?**
O dashboard é configurado em `apps/common/dashboard.py` via `DASHBOARD_CALLBACK`. Adicione suas métricas lá. Não use `INDEX_DASHBOARD` — chave errada do Unfold.
