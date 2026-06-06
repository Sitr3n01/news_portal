# Secure Deploy GitHub Actions -> VPS

Este deploy foi desenhado para repositorio publico. Ele evita deploy automatico
em push, nao usa secrets em pull requests e limita o GitHub a chamar um unico
script root-owned na VPS.

## 1. GitHub

Crie um environment chamado `production`:

- Required reviewers: habilitado.
- Deployment branches: apenas `master`.
- Environment variables:
  - `VPS_HOST=2.25.178.16`
  - `VPS_PORT=22`
  - `VPS_USER=deploy`
- Environment secrets:
  - `VPS_SSH_PRIVATE_KEY`
  - `VPS_HOST_KEY`

Proteja a branch `master`:

- Require status checks before merging.
- Require review from Code Owners.
- Require pull request before merging.
- Restrinja alteracoes em `.github/workflows/**`, `scripts/deploy/**`,
  `docker/**` e `config/settings/**` a revisao humana.

Nao use `pull_request_target` para deploy.

## 2. VPS

Crie o usuario de deploy e instale o script root-owned:

```bash
adduser --disabled-password --gecos "" deploy
install -d -m 0700 -o deploy -g deploy /home/deploy/.ssh

cd /opt/kelly_sys
git pull --ff-only origin master
install -o root -g root -m 0755 scripts/deploy/kellysys-deploy /usr/local/sbin/kellysys-deploy

cat >/etc/sudoers.d/kellysys-deploy <<'EOF'
deploy ALL=(root) NOPASSWD: /usr/local/sbin/kellysys-deploy
EOF
chmod 0440 /etc/sudoers.d/kellysys-deploy
visudo -cf /etc/sudoers.d/kellysys-deploy
```

Nao adicione o usuario `deploy` ao grupo `docker`. A permissao de deploy deve
passar apenas pelo comando permitido no sudoers.

Gere uma chave SSH exclusiva para o GitHub Actions em uma maquina local segura:

```bash
ssh-keygen -t ed25519 -C "github-actions-kellysys-production" -f ./kellysys_deploy_ed25519
```

Instale a chave publica no usuario `deploy`:

```bash
cat >>/home/deploy/.ssh/authorized_keys <<'EOF'
restrict ssh-ed25519 COLE_A_CHAVE_PUBLICA_AQUI github-actions-kellysys-production
EOF
chown deploy:deploy /home/deploy/.ssh/authorized_keys
chmod 0600 /home/deploy/.ssh/authorized_keys
```

Opcao mais restritiva: substitua `restrict` por um forced command:

```text
restrict,command="/usr/bin/sudo /usr/local/sbin/kellysys-deploy" ssh-ed25519 COLE_A_CHAVE_PUBLICA_AQUI github-actions-kellysys-production
```

Nesse modo, a chave so executa o deploy, mesmo que alguem tente abrir shell.

## 3. Host key

Nunca use `StrictHostKeyChecking=no`. Coloque a host key real da VPS no secret
`VPS_HOST_KEY`.

Na VPS, confira a fingerprint:

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
cat /etc/ssh/ssh_host_ed25519_key.pub
```

Em uma maquina local, colete e compare:

```bash
ssh-keyscan -p 22 2.25.178.16
```

O secret `VPS_HOST_KEY` deve conter uma ou mais linhas `ssh-keyscan` validas,
por exemplo:

```text
2.25.178.16 ssh-ed25519 AAAA...
```

## 4. Validacao

Antes de rodar pelo GitHub:

```bash
sudo /usr/local/sbin/kellysys-deploy
```

Depois rode o workflow `Deploy Production` manualmente em `master`.

Resultados esperados:

- CI passa antes do deploy.
- GitHub pede aprovacao do environment `production`.
- `/opt/kelly_sys/backups/` recebe um dump PostgreSQL gzipado.
- `docker compose -p kellysys -f docker/docker-compose.prod.yml ps` mostra
  `db`, `web` e `nginx` saudaveis.
- `komuniki.com.br/healthz/` retorna 200.
- `kellyfarias.com.br/news/` retorna 200 ou redirect HTTPS.
- `kellyfarias.com.br/` redireciona para `/news/`.
