# VPS Optimization Runbook

Runbook para controlar crescimento de disco e CPU na VPS Hostinger em
producao. Execute comandos como `root`/`sudo` e nunca use `docker volume prune`,
`docker compose down -v` ou remocao manual em `/var/lib/docker/volumes`.

## Diagnostico

```bash
cd /opt/kelly_sys

df -hT
sudo du -xhd1 / | sort -h
sudo du -xhd1 /var | sort -h
sudo du -xhd1 /var/lib/docker | sort -h
sudo du -sh /opt/kelly_sys/backups /var/log 2>/dev/null || true

docker system df -v
docker compose -p kellysys -f docker/docker-compose.prod.yml ps
docker stats --no-stream

sudo find /var/lib/docker/containers -name '*-json.log' -printf '%s %p\n' | sort -nr | head -20
sudo journalctl --disk-usage

docker compose -p kellysys -f docker/docker-compose.prod.yml exec -T db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT relname, n_live_tup, n_dead_tup, pg_size_pretty(pg_total_relation_size(relid)) AS total FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 20;"'
```

## Aplicacao

```bash
cd /opt/kelly_sys
git pull --ff-only origin master

sudo install -o root -g root -m 0755 scripts/deploy/kellysys-deploy /usr/local/sbin/kellysys-deploy
sudo install -o root -g root -m 0755 scripts/deploy/kellysys-deploy-approved /usr/local/sbin/kellysys-deploy-approved
sudo install -o root -g root -m 0755 scripts/deploy/kellysys-maintenance /usr/local/sbin/kellysys-maintenance

sudo /usr/local/sbin/kellysys-deploy
sudo /usr/local/sbin/kellysys-maintenance

# Opcional, em janela curta: aplica a nova politica de log tambem ao Postgres.
sudo docker compose -p kellysys -f docker/docker-compose.prod.yml up -d --no-deps --force-recreate db
```

## Timer de manutencao

```bash
sudo tee /etc/systemd/system/kellysys-maintenance.service >/dev/null <<'EOF'
[Unit]
Description=KellySys safe daily maintenance
Wants=docker.service
After=docker.service

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/kellysys-maintenance
EOF

sudo tee /etc/systemd/system/kellysys-maintenance.timer >/dev/null <<'EOF'
[Unit]
Description=Run KellySys safe daily maintenance

[Timer]
OnCalendar=*-*-* 03:20:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now kellysys-maintenance.timer
sudo systemctl start kellysys-maintenance.service
```

## Validacao

```bash
cd /opt/kelly_sys
docker compose -p kellysys -f docker/docker-compose.prod.yml ps
docker stats --no-stream
docker system df
df -hT
systemctl status kellysys-maintenance.timer --no-pager
journalctl -u kellysys-maintenance.service -n 80 --no-pager
curl -sI https://komuniki.com.br/ | head
curl -sI https://kellyfarias.com.br/news/ | head
```
