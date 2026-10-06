# Secure Deploy GitHub Actions -> VPS

Este deploy foi desenhado para repositorio publico. Ele evita deploy automatico
em push, nao usa secrets em pull requests e evita SSH inbound vindo do GitHub.
O GitHub apenas marca o commit aprovado com a tag `production-approved`; a VPS
busca essa tag por HTTPS e executa o deploy localmente.

## 1. GitHub

Crie um environment chamado `production`:

- Required reviewers: habilitado.
- Deployment branches: apenas `master`.

Proteja a branch `master` (configuracao atual):

- Require status checks before merging: o check `test` do workflow
  Django CI/CD, com a branch em dia com o `master` (strict).
- Do not allow bypassing: a regra vale tambem para administradores.
- Revisao obrigatoria e "Require review from Code Owners" ficam desligadas
  enquanto o projeto tiver um mantenedor so, porque o GitHub nao deixa
  aprovar o proprio PR. O `.github/CODEOWNERS` ja marca os caminhos
  sensiveis (`.github/workflows/**`, `scripts/deploy/**`, `docker/**` e
  `config/settings/**`) e passa a exigir revisao assim que as duas opcoes
  forem ligadas, quando houver um segundo revisor.

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
OnBootSec=2min
OnUnitActiveSec=10min
AccuracySec=2min
RandomizedDelaySec=60
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now kellysys-approved-deploy.timer
systemctl start kellysys-approved-deploy.service
```

Crie tambem o timer de manutencao diaria. Ele limpa sessoes expiradas e codigos
de verificacao vencidos, purga revisoes do Wagtail com mais de 30 dias, roda
`VACUUM (ANALYZE)` em `django_session`, `django_cache` e `wagtailcore_revision`,
remove backups antigos, remove containers/imagens/build cache nao usados e limita
o journal. Ele nunca executa `docker volume prune`.

`wagtailcore_revision` merece atencao: `Article` usa `RevisionMixin`, entao cada
save grava um snapshot JSON inteiro. Sem a purga a tabela so cresce, e ela puxa
junto o tempo do `pg_dump` e o working set do Postgres. O `purge_revisions`
preserva `latest_revision`, publicacao agendada e revisao em workflow — rascunho
nao se perde.

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

## 2.1 Deploy que falha nao reentra em loop

O `kellysys-deploy-approved` grava `/var/lib/kellysys-deploy/last-approved-sha`
somente depois de o deploy inteiro passar, e o `kellysys-deploy` termina em oito
healthchecks HTTP/HTTPS. Sem trava, uma falha ali fazia o timer repetir o deploy
completo (`pg_dump`, `docker build`, `migrate`, `collectstatic`, recriacao de
containers) a cada tick, indefinidamente — a causa raiz do crescimento de disco e
CPU tratado em [vps-optimization.md](vps-optimization.md).

Hoje o SHA tentado e gravado em `last-approved-sha.attempt` **antes** do deploy
comecar. Se o mesmo SHA voltar a ser oferecido, o script aborta com erro em vez de
tentar de novo:

```bash
systemctl --failed
journalctl -u kellysys-approved-deploy.service -n 40 --no-pager
ls -la /var/lib/kellysys-deploy/
```

- `last-approved-sha` presente e `.attempt` ausente: ultimo deploy passou.
- `.attempt` presente: aquele commit falhou. Corrija a causa e rode o deploy a mao:

```bash
sudo /usr/local/sbin/kellysys-deploy
```

Retentar o mesmo commit pelo timer e uma decisao deliberada — remova o arquivo:

```bash
sudo rm -f /var/lib/kellysys-deploy/last-approved-sha.attempt
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
- `/var/backups/kellysys/` recebe um dump PostgreSQL gzipado.
- O timer `kellysys-maintenance.timer` esta ativo e a ultima execucao termina sem erro.
- `docker compose -p kellysys -f docker/docker-compose.prod.yml ps` mostra
  `db`, `web` e `nginx` saudaveis.
- `komuniki.com.br/healthz/` retorna 200.
- `kellyfarias.com.br/news/` retorna 200 ou redirect HTTPS.
- `kellyfarias.com.br/` redireciona para `/news/`.
