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
