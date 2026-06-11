"""Sincroniza posts das contas de redes sociais ativas com as APIs oficiais.

Uso típico (cron a cada 30 min):
    python manage.py sync_social_posts

Sem credenciais reais, registra um erro amigável por conta e segue — nunca quebra,
nunca apaga posts antigos e preserva a visibilidade definida no admin.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.social.models import Platform, SocialAccount, SocialPost, SyncStatus
from apps.social.services import instagram, tiktok
from apps.social.services.base import SocialSyncError, token_expiring_soon

# Plataforma -> (função de busca, função de normalização).
SERVICES = {
    Platform.INSTAGRAM: (instagram.fetch_instagram_media, instagram.normalize_instagram_post),
    Platform.TIKTOK: (tiktok.fetch_tiktok_videos, tiktok.normalize_tiktok_video),
}

# Plataforma -> (função de renovação de token, janela para renovar antes de expirar).
# Instagram usa token de 60 dias (renova com folga); TikTok é curto (renova na hora).
REFRESHERS = {
    Platform.INSTAGRAM: (instagram.refresh_instagram_token, timedelta(days=7)),
    Platform.TIKTOK: (tiktok.refresh_tiktok_token, timedelta(hours=1)),
}


class Command(BaseCommand):
    help = 'Sincroniza posts das contas de redes sociais ativas (Instagram/TikTok).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--platform', choices=[p.value for p in Platform],
            help='Sincroniza apenas uma plataforma (instagram ou tiktok).',
        )
        parser.add_argument('--account-id', type=int, help='Sincroniza apenas a conta com este ID.')
        parser.add_argument('--limit', type=int, default=6, help='Posts buscados por conta (padrão: 6).')
        parser.add_argument('--dry-run', action='store_true', help='Não grava nada; apenas mostra o que faria.')
        parser.add_argument('--verbose', action='store_true', help='Loga cada post processado.')

    def handle(self, *args, **options):
        platform = options.get('platform')
        account_id = options.get('account_id')
        limit = options['limit']
        dry_run = options['dry_run']
        verbose = options['verbose']

        accounts = SocialAccount.objects.filter(is_active=True)
        if platform:
            accounts = accounts.filter(platform=platform)
        if account_id:
            accounts = accounts.filter(pk=account_id)
        accounts = list(accounts.order_by('platform', 'pk'))

        prefix = '[dry-run] ' if dry_run else ''
        if not accounts:
            self.stdout.write(self.style.WARNING(f'{prefix}Nenhuma conta ativa encontrada para sincronizar.'))
            return

        totals = {'created': 0, 'updated': 0, 'skipped': 0, 'accounts_ok': 0, 'accounts_failed': 0}

        for account in accounts:
            self.stdout.write(f'{prefix}Sincronizando {account} ...')
            try:
                result = self._sync_account(account, limit=limit, dry_run=dry_run, verbose=verbose)
            except SocialSyncError as exc:
                totals['accounts_failed'] += 1
                self._mark_failed(account, str(exc), dry_run=dry_run)
                self.stdout.write(self.style.ERROR(f'  {prefix}Falha: {exc}'))
                continue
            except Exception as exc:  # defensivo: uma conta nunca derruba as demais
                totals['accounts_failed'] += 1
                self._mark_failed(account, f'Erro inesperado: {exc}', dry_run=dry_run)
                self.stdout.write(self.style.ERROR(f'  {prefix}Erro inesperado: {exc}'))
                continue

            totals['created'] += result['created']
            totals['updated'] += result['updated']
            totals['skipped'] += result['skipped']
            totals['accounts_ok'] += 1
            self._mark_success(account, result, dry_run=dry_run)
            self.stdout.write(self.style.SUCCESS(
                f"  {prefix}OK: {result['created']} novo(s), {result['updated']} atualizado(s), "
                f"{result['skipped']} ignorado(s)."
            ))

        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Concluído: {totals['accounts_ok']} conta(s) OK, {totals['accounts_failed']} com falha · "
            f"{totals['created']} novo(s), {totals['updated']} atualizado(s), {totals['skipped']} ignorado(s)."
        ))

    def _sync_account(self, account, *, limit, dry_run, verbose):
        self._maybe_refresh(account, dry_run=dry_run, verbose=verbose)
        fetch, normalize = SERVICES[account.platform]
        raw_items = fetch(account, limit=limit)

        created = updated = skipped = 0
        for raw in raw_items:
            data = normalize(raw, account)
            if not data.get('external_id') or not data.get('published_at'):
                skipped += 1
                if verbose:
                    self.stdout.write(self.style.WARNING(
                        f'    ignorado (sem id/data): {data.get("external_id") or "?"}'
                    ))
                continue

            if dry_run:
                exists = SocialPost.objects.filter(
                    platform=data['platform'], external_id=data['external_id'],
                ).exists()
                updated += 1 if exists else 0
                created += 0 if exists else 1
                if verbose:
                    self.stdout.write(f'    {"atualizaria" if exists else "criaria"}: {data["external_id"]}')
                continue

            was_created = self._upsert_post(account, data)
            created += 1 if was_created else 0
            updated += 0 if was_created else 1
            if verbose:
                self.stdout.write(f'    {"criado" if was_created else "atualizado"}: {data["external_id"]}')

        return {'created': created, 'updated': updated, 'skipped': skipped, 'fetched': len(raw_items)}

    def _maybe_refresh(self, account, *, dry_run, verbose):
        """Renova o token da conta quando está perto de expirar (sem interromper o fluxo)."""
        entry = REFRESHERS.get(account.platform)
        if not entry:
            return
        refresher, window = entry
        if not token_expiring_soon(account, window):
            return
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'  [dry-run] token de {account} expira em {account.token_expires_at}; renovaria.'
            ))
            return
        try:
            refresher(account)
            self.stdout.write(self.style.SUCCESS(f'  Token de {account} renovado.'))
        except SocialSyncError as exc:
            # Não interrompe: o fetch tenta com o token atual e, se falhar, registra o erro.
            self.stdout.write(self.style.WARNING(f'  Não foi possível renovar o token: {exc}'))

    def _upsert_post(self, account, data):
        """Cria ou atualiza o post, preservando is_visible/is_manual de quem já existe."""
        content = {
            'account': account,
            'permalink': data['permalink'],
            'caption': data['caption'],
            'media_type': data['media_type'],
            'thumbnail_url': data['thumbnail_url'],
            'media_url': data['media_url'],
            'published_at': data['published_at'],
            'sync_payload': data['sync_payload'],
        }
        obj, created = SocialPost.objects.get_or_create(
            platform=data['platform'], external_id=data['external_id'],
            defaults={**content, 'is_visible': True, 'is_manual': False},
        )
        if not created:
            # Atualiza só o conteúdo; nunca sobrescreve is_visible/is_manual (escolha do admin).
            for field, value in content.items():
                setattr(obj, field, value)
            obj.save(update_fields=[*content.keys(), 'updated_at'])
        return created

    def _mark_success(self, account, result, *, dry_run):
        if dry_run:
            return
        account.last_sync_at = timezone.now()
        account.last_sync_status = SyncStatus.PARTIAL if result['skipped'] else SyncStatus.SUCCESS
        account.last_sync_error = ''
        account.save(update_fields=['last_sync_at', 'last_sync_status', 'last_sync_error', 'updated_at'])

    def _mark_failed(self, account, message, *, dry_run):
        if dry_run:
            return
        account.last_sync_at = timezone.now()
        account.last_sync_status = SyncStatus.FAILED
        account.last_sync_error = message[:2000]
        account.save(update_fields=['last_sync_at', 'last_sync_status', 'last_sync_error', 'updated_at'])
