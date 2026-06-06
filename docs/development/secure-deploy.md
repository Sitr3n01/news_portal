# Secure Deploy GitHub Actions -> VPS

Este deploy foi desenhado para repositorio publico. Ele evita deploy automatico
em push, nao usa secrets em pull requests e evita SSH inbound vindo do GitHub.
O GitHub apenas marca o commit aprovado com a tag `production-approved`; a VPS
busca essa tag por HTTPS e executa o deploy localmente.

## 1. GitHub

Crie um environment chamado `production`:

- Required reviewers: habilitado.
- Deployment branches: apenas `master`.

Proteja a branch `master`:

- Require status checks before merging.
- Require review from Code Owners.
- Require pull request before merging.
- Restrinja alteracoes em `.github/workflows/**`, `scripts/deploy/**`,
  `docker/**` e `config/settings/**` a revisao humana.

Nao use `pull_request_target` para deploy.

O workflow `Deploy Production`:

- roda lint, collectstatic e testes;
- aguarda aprovacao do environment `production`;
- move a tag `production-approved` para o commit aprovado.

## 2. VPS

Instale os scripts root-owned:

```bash
cd /opt/kelly_sys
git pull --ff-only origin master
install -o root -g root -m 0755 scripts/deploy/kellysys-deploy /usr/local/sbin/kellysys-deploy
install -o root -g root -m 0755 scripts/deploy/kellysys-deploy-approved /usr/local/sbin/kellysys-deploy-approved
install -o root -g root -m 0755 scripts/deploy/kellysys-maintenance /usr/local/sbin/kellysys-maintenance
```

Crie um timer para a VPS procurar commits aprovados:

```bash
cat >/etc/systemd/system/kellysys-approved-deploy.service <<'EOF'
[Unit]
Description=Deploy latest GitHub-approved KellySys commit
Wants=network-online.target docker.service
After=network-online.target docker.service

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/kellysys-deploy-approved
EOF

cat >/etc/systemd/system/kellysys-approved-deploy.timer <<'EOF'
[Unit]
Description=Poll GitHub-approved KellySys deploy tag

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min
AccuracySec=15s
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now kellysys-approved-deploy.timer
systemctl start kellysys-approved-deploy.service
```

Crie tambem o timer de manutencao diaria. Ele limpa sessoes expiradas,
atualiza estatisticas da tabela `django_session`, remove backups antigos,
remove containers/imagens/build cache nao usados e limita o journal. Ele nunca
executa `docker volume prune`.

```bash
cat >/etc/systemd/system/kellysys-maintenance.service <<'EOF'
[Unit]
Description=KellySys safe daily maintenance
Wants=docker.service
After=docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/env bash /usr/local/sbin/kellysys-maintenance
EOF

cat >/etc/systemd/system/kellysys-maintenance.timer <<'EOF'
[Unit]
Description=Run KellySys safe daily maintenance

[Timer]
OnCalendar=*-*-* 03:20:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now kellysys-maintenance.timer
systemctl start kellysys-maintenance.service
```

## 3. Validacao

Antes de rodar pelo GitHub:

```bash
sudo /usr/local/sbin/kellysys-deploy
```

Depois rode o workflow `Deploy Production` manualmente em `master`.

Resultados esperados:

- CI passa antes do deploy.
- GitHub pede aprovacao do environment `production`.
- A tag `production-approved` passa a apontar para o commit aprovado.
- O timer da VPS detecta a tag e executa `/usr/local/sbin/kellysys-deploy-approved`.
- `/opt/kelly_sys/backups/` recebe um dump PostgreSQL gzipado.
- O timer `kellysys-maintenance.timer` esta ativo e a ultima execucao termina sem erro.
- `docker compose -p kellysys -f docker/docker-compose.prod.yml ps` mostra
  `db`, `web` e `nginx` saudaveis.
- `komuniki.com.br/healthz/` retorna 200.
- `kellyfarias.com.br/news/` retorna 200 ou redirect HTTPS.
- `kellyfarias.com.br/` redireciona para `/news/`.
