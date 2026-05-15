# news_portal

> Portal de notícias e site institucional multi-site, construído em Django 5 com PostgreSQL, HTMX e Django Unfold.

![Python](https://img.shields.io/badge/python-3.12+-blue)
![Django](https://img.shields.io/badge/django-5.x-green)
![PostgreSQL](https://img.shields.io/badge/postgres-16-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Status

Sistema de produção desenvolvido para um cliente real (portal escolar + portal de notícias). Em desenvolvimento ativo — funcionalidades core operacionais, escopo restante em construção.

---

## Visão Geral

Sistema web unificado que serve dois portais independentes a partir do mesmo codebase:

| Portal | URL base | Propósito |
|--------|----------|-----------|
| Escola | `/` | Site institucional (páginas, equipe, depoimentos, contato, vagas) |
| Notícias | `/news/` | Portal público de notícias com newsletter, RSS e comentários |

Ambos compartilham banco, admin e usuários, mas são isolados logicamente via **Django Sites Framework** — cada portal tem seu próprio `Site` com `SITE_ID` diferente, e querysets de conteúdo público sempre passam por `CurrentSiteManager`.

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.12+ / Django 5.x |
| Banco | PostgreSQL 16 |
| Frontend | Django Templates + HTMX + Alpine.js (sem SPA) |
| Admin | Django Unfold |
| Static | WhiteNoise |
| Dev | Docker Compose (Django + PostgreSQL + Mailpit) |
| Deploy | Docker Compose prod + Nginx + Let's Encrypt |

---

## Estrutura de Apps

```
apps/
  common/        Models abstratos, sanitização HTML, context processors, SiteExtension
  accounts/      CustomUser (email único), autenticação, permissões via Groups
  school/        CMS de páginas, equipe e depoimentos
  hiring/        Vagas, departamentos, pipeline de candidaturas
  contact/       Formulário de contato multi-site
  news/          Artigos, categorias, tags, newsletter, RSS, comentários, bookmarks
  media_library/ Biblioteca de mídia compartilhada
```

---

## Pré-requisitos

- Docker + Docker Compose **ou** Python 3.12+ com PostgreSQL local
- Git

---

## Setup Rápido

### Com Docker (recomendado)

```bash
git clone https://github.com/Sitr3n01/news_portal.git
cd news_portal

cp .env.example .env

docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml exec web python manage.py migrate
docker compose -f docker/docker-compose.yml exec web python manage.py createsuperuser
```

Acesse:
- **App:** http://localhost:8000
- **Admin:** http://localhost:8000/admin
- **Mailpit (captura de emails em dev):** http://localhost:8025

### Sem Docker

```bash
git clone https://github.com/Sitr3n01/news_portal.git
cd news_portal

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements/development.txt

cp .env.example .env        # editar DB_* para apontar pro seu PostgreSQL
# alternativa rápida: SQLite local
export DJANGO_SETTINGS_MODULE=config.settings.local_sqlite

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## Variáveis de Ambiente

Configuração em `.env` (use `.env.example` como base).

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `SECRET_KEY` | sim | Chave secreta do Django |
| `DEBUG` | sim | `True` em dev, `False` em prod |
| `ALLOWED_HOSTS` | sim | Hosts separados por vírgula |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | sim | Credenciais PostgreSQL |
| `DB_HOST` / `DB_PORT` | sim | Host e porta do banco |
| `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | prod | SMTP de produção |
| `DEFAULT_FROM_EMAIL` | prod | Remetente padrão |
| `CSRF_TRUSTED_ORIGINS` | prod | Domínios confiáveis para CSRF |

---

## Padrões do Projeto

Resumo das convenções críticas (detalhe em [docs/development/ai-workflow.md](docs/development/ai-workflow.md) e [docs/development/DEVELOPER_GUIDE.md](docs/development/DEVELOPER_GUIDE.md)):

- **Views:** Function-Based Views (FBV) — decisão arquitetural permanente.
- **Models:** herdam de `TimeStampedModel` (e `SEOModel` para conteúdo público). Models com `ForeignKey(Site)` declaram `on_site = CurrentSiteManager()`.
- **Querysets multi-site:** SEMPRE usar `Article.on_site` / `Page.on_site` em views, feeds e sitemaps — nunca `.objects`.
- **Sanitização HTML:** sempre via `apps.common.sanitization` no `save()` do model. Nunca duplicar listas de tags/atributos.
- **Templates:** nunca usar `|safe` — sempre `|sanitize_html` ou `|striptags`. Imagens com `loading="lazy"` (exceto hero/above the fold). Links via `{% url %}`, nunca hardcoded.
- **Admin:** importar `ModelAdmin` de `unfold.admin`. Fieldsets, actions e `help_text` em PT-BR.
- **Segurança:** mensagens genéricas em autenticação e candidaturas (nunca revelar se email/username existe). Uploads validam extensão **e** MIME.
- **Performance:** `select_related` / `prefetch_related` em qualquer query com FK ou M2M. `F()` para updates atômicos. Paginação padrão de 12 itens.

---

## Testes

```bash
pytest
```

Configurações de teste em `config/settings/test.py` (banco em memória, hasher MD5 para performance). CI roda no GitHub Actions em todo push/PR para `main` e `master` — veja [`.github/workflows/django.yml`](.github/workflows/django.yml).

---

## Deploy

Deploy de produção usa Docker Compose + Nginx + Let's Encrypt. Roteiro completo em [docs/development/DEPLOY.md](docs/development/DEPLOY.md), incluindo:

- Configuração de `.env.prod`
- Build e subida dos containers de produção
- Emissão de certificado SSL via Certbot
- Backup diário do PostgreSQL via cron

---

## Documentação

| Documento | Conteúdo |
|-----------|----------|
| [docs/development/DEVELOPER_GUIDE.md](docs/development/DEVELOPER_GUIDE.md) | Onboarding para novos devs |
| [docs/development/TECHNICAL_REFERENCE.md](docs/development/TECHNICAL_REFERENCE.md) | Referência técnica exaustiva (middleware, settings, apps, segurança) |
| [docs/development/DEPLOY.md](docs/development/DEPLOY.md) | Guia de deploy em produção |
| [docs/development/roadmap.md](docs/development/roadmap.md) | Plano global e estado atual das fases |

---

## Licença

Distribuído sob licença MIT. Veja [LICENSE](LICENSE) para detalhes.
