# Guia de Deploy — news_portal

Guia operacional para produção. Antes de executar, passe pelo [checklist de go-live](go-live-checklist.md).

## Premissas

- VPS Linux com Docker Engine e Docker Compose.
- Repositório em `/opt/kelly_sys`.
- Docker Compose project `kellysys`.
- Branch de produção: `master`.
- Deploy aprovado por tag `production-approved`.
- Domínios públicos:
  - `komuniki.com.br`
  - `www.komuniki.com.br`
  - `kellyfarias.com.br`
  - `www.kellyfarias.com.br`

---

## 1. Clonar ou Atualizar o Repositório

```bash
git clone https://github.com/Sitr3n01/news_portal.git /opt/kelly_sys
cd /opt/kelly_sys
git checkout master
git pull --ff-only origin master
```

Na VPS de produção, o deploy automatizado exige working tree limpo. Não edite arquivos rastreados diretamente no servidor.

---

## 2. Configurar `.env.prod`

```bash
cd /opt/kelly_sys
cp .env.prod.example .env.prod
nano .env.prod
chmod 600 .env.prod
```

Valores críticos:

```env
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
SECRET_KEY=gere_uma_chave_forte_e_unica
ALLOWED_HOSTS=komuniki.com.br,www.komuniki.com.br,kellyfarias.com.br,www.kellyfarias.com.br
CSRF_TRUSTED_ORIGINS=https://komuniki.com.br,https://www.komuniki.com.br,https://kellyfarias.com.br,https://www.kellyfarias.com.br
SECURE_SSL_REDIRECT=True

POSTGRES_DB=news_portal
POSTGRES_USER=news_portal_user
POSTGRES_PASSWORD=senha_forte
DB_NAME=news_portal
DB_USER=news_portal_user
DB_PASSWORD=senha_forte
DB_HOST=db
DB_PORT=5432
```

SMTP:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.seuprovedor.com
EMAIL_PORT=587
EMAIL_HOST_USER=usuario@seudominio.com
EMAIL_HOST_PASSWORD=senha_smtp
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Blog da Kelly <noticias@kellyfarias.com.br>
```

Turnstile é obrigatório em produção para formulários públicos:

```env
CLOUDFLARE_TURNSTILE_SITE_KEY=...
CLOUDFLARE_TURNSTILE_SECRET_KEY=...
```

Segredos como `SECRET_KEY`, banco, SMTP e Turnstile nunca são gravados no admin nem commitados.

---

## 3. Bootstrap Inicial

Suba os serviços:

```bash
docker compose -p kellysys -f docker/docker-compose.prod.yml build
docker compose -p kellysys -f docker/docker-compose.prod.yml up -d db web
```

Rode a configuração inicial:

```bash
docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py migrate --noinput
docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py collectstatic --clear --noinput
docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py createsuperuser
docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py set_site_domain
```

> A tabela do cache (`django_cache`) é criada pela migration `common.0009`, junto
> com o `migrate` acima — não há passo manual. Se precisar recriá-la à mão, o
> comando é `python manage.py createcachetable` (idempotente). Sem essa tabela,
> a recuperação de senha falha: o rate limit depende do cache.

> **E-mail é obrigatório em produção.** Sem SMTP configurado, o "Esqueci minha
> senha" não entrega nada e a equipe fica sem como recuperar acesso. Confira o
> bloco de e-mail em `.env.prod.example`, em especial `EMAIL_TIMEOUT` (sem ele um
> servidor SMTP travado pendura um worker) e que `EMAIL_USE_TLS` e
> `EMAIL_USE_SSL` não estejam ambos como `True` — são mutuamente exclusivos.

Configure no admin:

- **Sistema → Sites**: domínio público correto. O link dos e-mails de recuperação
  de senha sai daqui, não do header `Host` da requisição.
- **Sistema → Configurações dos sites**: identidade, contato, remetente de newsletter, analytics e links sociais.
- **Sistema → Usuários**: confira o **Cargo** de cada conta. Para liberar a
  Administração do sistema, marque também **Acesso administrativo** (`is_staff`)
  — o cargo sozinho não abre essa área.

### Acesso da equipe

Depois do deploy, a equipe entra por **`/entrar/`** — porta única de Publicação
de matérias e Administração do sistema. `/admin/login/` e `/cms/login/`
redirecionam para lá, preservando o destino original.

Para voltar às telas de login nativas sem deploy de código, defina
`UNIFIED_LOGIN_ENABLED=False` no `.env` e reinicie o `web`.

---

## 4. TLS com Let's Encrypt

O `nginx.conf` versionado espera certificados em `/etc/letsencrypt/live/komuniki.com.br/`. Em VPS nova, emita o primeiro certificado antes de subir o Nginx final.

Opção mais simples para primeiro certificado, usando standalone na porta 80:

```bash
docker run --rm -p 80:80 \
  -v kellysys_certbot_conf:/etc/letsencrypt \
  certbot/certbot:latest certonly --standalone \
  --email seu-email@dominio.com --agree-tos --no-eff-email \
  -d komuniki.com.br -d www.komuniki.com.br \
  -d kellyfarias.com.br -d www.kellyfarias.com.br
```

Depois que o Nginx estiver no ar, renovações podem usar webroot pelo compose:

```bash
docker compose -p kellysys -f docker/docker-compose.prod.yml \
  --profile tools run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  --email seu-email@dominio.com --agree-tos --no-eff-email \
  -d komuniki.com.br -d www.komuniki.com.br \
  -d kellyfarias.com.br -d www.kellyfarias.com.br
```

Depois valide e suba o Nginx:

```bash
docker compose -p kellysys -f docker/docker-compose.prod.yml up -d nginx
docker compose -p kellysys -f docker/docker-compose.prod.yml exec -T nginx nginx -t
```

---

## 5. Instalar Deploy Aprovado na VPS

Instale os scripts root-owned:

```bash
cd /opt/kelly_sys
sudo install -o root -g root -m 0755 scripts/deploy/kellysys-deploy /usr/local/sbin/kellysys-deploy
sudo install -o root -g root -m 0755 scripts/deploy/kellysys-deploy-approved /usr/local/sbin/kellysys-deploy-approved
sudo install -o root -g root -m 0755 scripts/deploy/kellysys-maintenance /usr/local/sbin/kellysys-maintenance
```

Configure os timers conforme [secure-deploy.md](secure-deploy.md):

- `kellysys-approved-deploy.timer`: procura a tag `production-approved` e roda deploy.
- `kellysys-maintenance.timer`: limpa sessões, estatísticas, imagens/containers antigos e journal.

Teste manual:

```bash
sudo /usr/local/sbin/kellysys-deploy
```

---

## 6. Fluxo Normal de Deploy

> ### ⚠️ ANTES do primeiro deploy do CMS Wagtail: migração única de conteúdo
>
> **Só para o deploy que estreia o Wagtail. Depois dele, ignore esta caixa.**
>
> O deploy automatizado roda `migrate` sozinho (ver a lista logo abaixo). Neste
> release, o `migrate` inclui a migration `news.0021`, que **apaga a tabela
> `news_articleblock` de forma irreversível** depois de converter o conteúdo dela
> para o novo campo `Article.body`. A conversão só consegue montar os blocos de
> imagem se as `cms_media.Image` correspondentes já existirem — e é isso que os
> dois comandos abaixo fazem.
>
> **Rodar o deploy sem estes passos faz toda imagem e todo vídeo/post embutido
> nas matérias existentes virar apenas a legenda em texto.** O texto das matérias
> sobrevive de qualquer forma (o campo `content` é a rede de segurança), mas
> imagem e embed não voltam.
>
> **O `migrate` precisa rodar em DUAS etapas**, e a ordem não é opcional. Os dois
> comandos de ponte leem `Article` e criam `cms_media.Image`, então dependem do
> schema novo (`news.0015`–`0020` e `cms_media.0001`) já existir. Mas a `0021`, que
> apaga a tabela, vem no mesmo `migrate`. Daí a parada no meio: `migrate news 0020`
> aplica tudo de que os comandos precisam e **para antes** da `0021` — verificado no
> grafo de migrations, ela não entra nesse plano.
>
> Com o código novo já buildado:
>
> ```bash
> # ETAPA 1 — schema novo, SEM apagar a tabela de blocos ainda.
> docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py migrate news 0020 --noinput
> ```
>
> ```bash
> # 2. Capas dos artigos -> cms_media.Image  (dry-run primeiro, sem --apply)
> docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py migrate_featured_images
> ```
>
> ```bash
> docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py migrate_featured_images --apply
> ```
>
> ```bash
> # 3. Imagens usadas nos blocos de conteúdo -> cms_media.Image (dry-run primeiro)
> docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py migrate_block_media
> ```
>
> ```bash
> docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py migrate_block_media --apply
> ```
>
> ```bash
> # 4. Portão: prevê exatamente o que a 0021 fará. Somente leitura.
> docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py audit_article_blocks --detalhado
> ```
>
> ```bash
> # ETAPA 2 — só depois do portão aprovar: converte os blocos e apaga a tabela.
> docker compose -p kellysys -f docker/docker-compose.prod.yml run --rm web python manage.py migrate --noinput
> ```
>
> Os passos 2 e 3 são **idempotentes** (o que já foi convertido é ignorado) e sem
> `--apply` **não gravam nada, nem no banco nem no disco** — pode repetir à
> vontade. O passo 4 é o que decide se pode seguir:
>
> - **"Cobertura de 100%"** → siga para o passo 4.
> - **"NÃO RODE O MIGRATE"** → há blocos que se perderiam. Volte ao passo 2 e
>   resolva os erros que ele reportou (o caso comum é arquivo referenciado no
>   banco mas ausente do disco).
> - **"N bloco(s) serão rebaixados"** → nenhum texto se perde, mas aquelas
>   imagens/embeds viram parágrafo de legenda. Decisão sua se é aceitável.
>
> Antes de qualquer coisa, tenha **dois** backups em mão: o dump do PostgreSQL e uma
> cópia do diretório `media/`. O dump sozinho não recupera nada se os arquivos de
> imagem se perderem — a `cms_media.Image` aponta para arquivo em disco. O deploy
> aprovado já cria o dump em `/opt/kelly_sys/backups/`, mas neste release confira à
> mão que ele existe e não está vazio.

1. Abra/mergeie mudança em `master`.
2. Rode o workflow manual **Deploy Production** em `master`.
3. Aguarde lint, `collectstatic` e testes.
4. Aprove o environment `production`.
5. O workflow move a tag `production-approved`.
6. A VPS detecta a tag e executa `/usr/local/sbin/kellysys-deploy-approved`.

O deploy local faz:

- valida working tree limpo;
- busca commit aprovado;
- cria backup PostgreSQL gzipado em `/opt/kelly_sys/backups/`;
- builda imagem web;
- roda migrations;
- roda `collectstatic --clear`;
- recria `web`;
- valida e recria `nginx`;
- executa healthchecks HTTP/HTTPS.

---

## 7. Rotinas Operacionais

Newsletter pendente:

```cron
*/5 * * * * docker compose -p kellysys -f /opt/kelly_sys/docker/docker-compose.prod.yml exec -T web python manage.py send_pending_newsletters --batch-size 100
```

Publicação agendada (Wagtail — artigos com go_live_at):

```cron
*/5 * * * * docker compose -p kellysys -f /opt/kelly_sys/docker/docker-compose.prod.yml exec -T web python manage.py publish_scheduled
```

Manutenção diária preferencial:

```bash
sudo systemctl status kellysys-maintenance.timer --no-pager
sudo journalctl -u kellysys-maintenance.service -n 80 --no-pager
```

Não execute `docker volume prune` em produção.

---

## 8. Smoke Tests

```bash
curl -I https://komuniki.com.br/healthz/
curl -I https://www.komuniki.com.br/healthz/
curl -I https://komuniki.com.br/
curl -I https://kellyfarias.com.br/news/
curl -I https://kellyfarias.com.br/
```

Esperado:

- healthchecks retornam 200;
- Komuniki carrega na raiz;
- Blog carrega em `/news/`;
- raiz de `kellyfarias.com.br` redireciona para `/news/`;
- `/admin/` abre por HTTPS.

---

## 9. Referência

| Serviço | Função |
|---------|--------|
| `web` | Django/Gunicorn, 3 workers, 2 threads |
| `db` | PostgreSQL 16 |
| `nginx` | TLS, proxy reverso, estáticos, mídia, `/protected/` |
| `certbot` | Emissão/renovação de certificado |

Documentos relacionados:

- [go-live-checklist.md](go-live-checklist.md)
- [secure-deploy.md](secure-deploy.md)
- [cloudflare-bots.md](cloudflare-bots.md)
- [vps-optimization.md](vps-optimization.md)
