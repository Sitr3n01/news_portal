# Guia de Deploy - news_portal

Este guia detalha os passos necessários para colocar o sistema em produção usando Docker Compose e Nginx.

## Requisitos no Servidor
- Servidor Linux (Ubuntu 22.04 LTS ou superior recomendado)
- Mínimo de 1GB de RAM (2GB recomendado)
- Docker Engine e Docker Compose instalados
- Git instalado
- Domínios apontados para o IP da máquina (ex: `escola.seudominio.com.br` e `news.seudominio.com.br`)

## 1. Preparando o Ambiente

Clone o repositório na máquina de produção:
```bash
git clone https://github.com/Sitr3n01/news_portal.git /opt/news_portal
cd /opt/news_portal
```

## 2. Configurando Variáveis de Produção

Crie o arquivo de ambiente para produção:
```bash
cp .env.example .env.prod
nano .env.prod
```

Edite as seguintes variáveis críticas:
```env
DEBUG=False
SECRET_KEY=sua_chave_cripografica_gigante_e_segura
ALLOWED_HOSTS=escola.seudominio.com.br,news.seudominio.com.br,localhost

DB_NAME=news_portal_prod_db
DB_USER=news_portal_prod_user
DB_PASSWORD=senha_segura_do_banco
DB_HOST=db
```

Configure também o SMTP transacional usado pela newsletter automática:
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.seuprovedor.com
EMAIL_PORT=587
EMAIL_HOST_USER=usuario_smtp
EMAIL_HOST_PASSWORD=senha_smtp
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=News Portal <noticias@seudominio.com.br>
```

O painel administrativo não grava segredos de produção como `SECRET_KEY`,
credenciais do banco ou `EMAIL_HOST_PASSWORD`. Ele mostra a saúde dessas
variáveis na dashboard e permite ao cliente gerenciar as configurações públicas
por site em **Sistema > Configurações do Site**, como logo, contatos, analytics
e o remetente visível da newsletter.

## 3. Subindo os Containers

Rode o compose de produção e aguarde o build do projeto:
```bash
docker compose -f docker/docker-compose.prod.yml build
docker compose -f docker/docker-compose.prod.yml up -d
```

## 4. Configuração Inicial (Migrations e Static)

Acesse o container da web para rodar as configurações iniciais de banco de dados e arquivos estáticos:
```bash
docker compose -f docker/docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker/docker-compose.prod.yml exec web python manage.py collectstatic --noinput
docker compose -f docker/docker-compose.prod.yml exec web python manage.py createsuperuser
```

## 5. Certificado SSL Gratuito (Let's Encrypt)

Você precisará emitir o certificado digital rodando o Certbot em um container que fará o desafio com os arquivos do Nginx:
```bash
docker run -it --rm \
  -v $(pwd)/docker/certbot_conf:/etc/letsencrypt \
  -v $(pwd)/docker/certbot_www:/var/www/certbot \
  certbot/certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  -d escola.seudominio.com.br -d news.seudominio.com.br
```

Após isto, basta descomentar as diretivas relativas ao SSL no seu arquivo `docker/nginx/nginx.conf` e dar reload no Nginx:
```bash
docker compose -f docker/docker-compose.prod.yml restart nginx
```

## 6. Rotinas e Backups Diários

O CI/CD via **GitHub Actions** já está testando a aplicação automaticamente a cada Push na branch `main`.
Para automatizar o dump do banco de Postgres localmente, insira na Crontab do Host:
```bash
@daily docker exec news_portal-db-1 pg_dump -U news_portal_prod_user news_portal_prod_db > /backups/news_portal_$(date +%Y%m%d).sql
```

Para automatizar o envio de newsletters pendentes do portal de notícias:
```bash
*/5 * * * * docker compose -f /opt/news_portal/docker/docker-compose.prod.yml exec -T web python manage.py send_pending_newsletters --batch-size 100
```

Para expurgar sessões expiradas (a tabela `django_session` cresce a cada visitante, inclusive anônimo; sem limpeza ela incha e pressiona CPU/memória do Postgres ao longo do tempo):
```bash
@daily docker compose -p kellysys -f /opt/kelly_sys/docker/docker-compose.prod.yml exec -T web python manage.py clearsessions
```

> **Caminhos canônicos:** os scripts em `scripts/deploy/` usam `/opt/kelly_sys` e o projeto compose `-p kellysys` — são a fonte da verdade. Onde este guia ainda mostra `/opt/news_portal`, prefira os valores dos scripts. Faça uma limpeza única agora executando o comando de `clearsessions` uma vez e, em seguida, rode `ANALYZE django_session;` no Postgres para atualizar as estatísticas do planejador.
