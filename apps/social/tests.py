from datetime import timedelta
from io import StringIO

import pytest
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

from apps.common.models import SiteExtension
from apps.social.management.commands import sync_social_posts as cmd
from apps.social.models import Platform, SocialAccount, SocialPost, SyncStatus
from apps.social.services import instagram, tiktok
from apps.social.services.base import TokenMissingError, token_expiring_soon


@pytest.fixture
def current_site(settings):
    site, _ = Site.objects.update_or_create(
        pk=settings.SITE_ID,
        defaults={'domain': 'testserver', 'name': 'Komuniki Teste'},
    )
    Site.objects.clear_cache()
    return site


def _account(site, **kwargs):
    defaults = {
        'platform': Platform.INSTAGRAM,
        'display_name': 'Komuniki IG',
        'username': 'komuniki',
        'is_active': True,
    }
    defaults.update(kwargs)
    return SocialAccount.objects.create(site=site, **defaults)


def _post(account, **kwargs):
    defaults = {
        'permalink': 'https://www.instagram.com/p/abc/',
        'published_at': timezone.now(),
        'is_visible': True,
    }
    defaults.update(kwargs)
    return SocialPost.objects.create(account=account, **defaults)


# ── Models ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_social_post_ordering_is_newest_first(current_site):
    account = _account(current_site)
    older = _post(account, caption='antigo', published_at=timezone.now() - timedelta(days=2))
    newer = _post(account, caption='novo', published_at=timezone.now())

    posts = list(SocialPost.objects.all())

    assert posts == [newer, older]


@pytest.mark.django_db
def test_manual_post_gets_generated_external_id(current_site):
    account = _account(current_site)
    post = _post(account, is_manual=True, external_id='')

    assert post.external_id.startswith('manual-')


@pytest.mark.django_db
def test_post_platform_follows_account(current_site):
    account = _account(current_site, platform=Platform.TIKTOK, username='tk')
    post = _post(account, permalink='https://tiktok.com/@tk/video/1')

    assert post.platform == Platform.TIKTOK


@pytest.mark.django_db
def test_unique_constraint_platform_external_id(current_site):
    account = _account(current_site)
    _post(account, is_manual=False, external_id='dup-1')

    with pytest.raises(IntegrityError):
        SocialPost.objects.create(
            account=account, platform=Platform.INSTAGRAM, external_id='dup-1',
            permalink='https://x', published_at=timezone.now(),
        )


@pytest.mark.django_db
def test_home_query_filters_active_account_and_visible_posts(current_site):
    active = _account(current_site, username='active', is_active=True)
    inactive = _account(current_site, username='inactive', is_active=False)
    visible = _post(active, caption='visivel', is_visible=True, is_manual=True, external_id='')
    _post(active, caption='oculto', is_visible=False, is_manual=True, external_id='')
    _post(inactive, caption='conta inativa', is_visible=True, is_manual=True, external_id='')

    qs = SocialPost.objects.filter(
        account__site=current_site, account__is_active=True, is_visible=True,
    )

    assert list(qs) == [visible]


@pytest.mark.django_db
def test_thumbnail_prefers_url_when_no_upload(current_site):
    account = _account(current_site)
    post = _post(account, thumbnail_url='https://cdn.example/thumb.jpg', is_manual=True, external_id='')

    assert post.thumbnail == 'https://cdn.example/thumb.jpg'


# ── Normalização (puro, sem rede) ──────────────────────────────────────────────

@pytest.mark.django_db
def test_normalize_instagram_post_maps_fields(current_site):
    account = _account(current_site)
    raw = {
        'id': '17895695668004550',
        'caption': 'Bastidores do evento',
        'media_type': 'VIDEO',
        'media_url': 'https://cdn.example/v.mp4',
        'thumbnail_url': 'https://cdn.example/v.jpg',
        'permalink': 'https://www.instagram.com/p/Cabc/',
        'timestamp': '2026-01-15T12:30:00+0000',
    }

    data = instagram.normalize_instagram_post(raw, account)

    assert data['platform'] == Platform.INSTAGRAM
    assert data['external_id'] == '17895695668004550'
    assert data['caption'] == 'Bastidores do evento'
    assert data['media_type'] == 'video'
    assert data['thumbnail_url'] == 'https://cdn.example/v.jpg'
    assert data['permalink'] == 'https://www.instagram.com/p/Cabc/'
    assert data['published_at'] is not None
    assert data['published_at'].year == 2026


@pytest.mark.django_db
def test_normalize_instagram_image_falls_back_to_media_url(current_site):
    account = _account(current_site)
    raw = {'id': '1', 'media_type': 'IMAGE', 'media_url': 'https://cdn.example/i.jpg', 'permalink': 'https://x', 'timestamp': '2026-01-01T00:00:00+0000'}

    data = instagram.normalize_instagram_post(raw, account)

    assert data['media_type'] == 'image'
    assert data['thumbnail_url'] == 'https://cdn.example/i.jpg'


@pytest.mark.django_db
def test_normalize_tiktok_video_maps_fields(current_site):
    account = _account(current_site, platform=Platform.TIKTOK, username='tk')
    raw = {
        'id': '7301234567890',
        'title': 'Novo vídeo',
        'video_description': 'descrição',
        'cover_image_url': 'https://cdn.tiktok/cover.jpg',
        'share_url': 'https://www.tiktok.com/@komuniki/video/7301234567890',
        'create_time': 1768400000,
    }

    data = tiktok.normalize_tiktok_video(raw, account)

    assert data['platform'] == Platform.TIKTOK
    assert data['external_id'] == '7301234567890'
    assert data['caption'] == 'Novo vídeo'
    assert data['media_type'] == 'video'
    assert data['thumbnail_url'] == 'https://cdn.tiktok/cover.jpg'
    assert data['permalink'].endswith('/video/7301234567890')
    assert data['published_at'] is not None


# ── Management command ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_sync_dry_run_without_tokens_does_not_crash(current_site):
    account = _account(current_site, is_active=True)  # sem access_token
    out = StringIO()

    call_command('sync_social_posts', '--dry-run', stdout=out, stderr=StringIO())

    account.refresh_from_db()
    # dry-run não grava: status permanece "nunca" e nada foi salvo.
    assert account.last_sync_status == SyncStatus.NEVER
    assert SocialPost.objects.count() == 0


@pytest.mark.django_db
def test_sync_marks_failed_without_tokens(current_site):
    account = _account(current_site, is_active=True)
    out = StringIO()

    call_command('sync_social_posts', stdout=out, stderr=StringIO())

    account.refresh_from_db()
    assert account.last_sync_status == SyncStatus.FAILED
    assert account.last_sync_error  # mensagem amigável registrada


@pytest.mark.django_db
def test_sync_creates_posts_and_preserves_admin_visibility(monkeypatch, current_site):
    _account(current_site, access_token='token', external_user_id='123', is_active=True)
    raw_items = [
        {'id': '1', 'caption': 'Primeiro', 'media_type': 'IMAGE', 'media_url': 'https://cdn/1.jpg',
         'permalink': 'https://ig/p/1', 'timestamp': '2026-01-01T10:00:00+0000'},
        {'id': '2', 'caption': 'Segundo', 'media_type': 'VIDEO', 'media_url': 'https://cdn/2.mp4',
         'thumbnail_url': 'https://cdn/2.jpg', 'permalink': 'https://ig/p/2', 'timestamp': '2026-01-02T10:00:00+0000'},
    ]
    monkeypatch.setitem(
        cmd.SERVICES, Platform.INSTAGRAM,
        (lambda acc, limit=6: raw_items, instagram.normalize_instagram_post),
    )

    call_command('sync_social_posts', stdout=StringIO(), stderr=StringIO())

    assert SocialPost.objects.count() == 2
    first = SocialPost.objects.get(external_id='1')
    assert first.is_manual is False
    assert first.is_visible is True

    # Admin oculta um post; a nova sincronização não pode reexibi-lo nem duplicar.
    SocialPost.objects.filter(external_id='1').update(is_visible=False)
    call_command('sync_social_posts', stdout=StringIO(), stderr=StringIO())

    first.refresh_from_db()
    assert first.is_visible is False
    assert SocialPost.objects.count() == 2


# ── Renovação de token ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_token_expiring_soon(current_site):
    account = _account(current_site)
    account.token_expires_at = None
    assert token_expiring_soon(account, timedelta(days=7)) is False
    account.token_expires_at = timezone.now() + timedelta(days=30)
    assert token_expiring_soon(account, timedelta(days=7)) is False
    account.token_expires_at = timezone.now() + timedelta(hours=1)
    assert token_expiring_soon(account, timedelta(days=7)) is True
    account.token_expires_at = timezone.now() - timedelta(minutes=5)
    assert token_expiring_soon(account, timedelta(days=7)) is True


@pytest.mark.django_db
def test_refresh_instagram_token_updates_account(monkeypatch, current_site):
    account = _account(current_site, access_token='old-token', external_user_id='1')
    monkeypatch.setattr(
        instagram, 'request_json',
        lambda *a, **k: {'access_token': 'new-token', 'expires_in': 5184000},
    )

    result = instagram.refresh_instagram_token(account)

    account.refresh_from_db()
    assert result == 'new-token'
    assert account.access_token == 'new-token'
    assert account.token_expires_at is not None


@pytest.mark.django_db
def test_refresh_instagram_without_token_raises(current_site):
    account = _account(current_site, access_token='')
    with pytest.raises(TokenMissingError):
        instagram.refresh_instagram_token(account)


@pytest.mark.django_db
def test_refresh_tiktok_token_updates_account(monkeypatch, settings, current_site):
    settings.TIKTOK_CLIENT_KEY = 'ck'
    settings.TIKTOK_CLIENT_SECRET = 'cs'
    account = _account(
        current_site, platform=Platform.TIKTOK, username='tk', access_token='old', refresh_token='r1',
    )
    monkeypatch.setattr(
        tiktok, 'request_json',
        lambda *a, **k: {'access_token': 'tk-new', 'refresh_token': 'r2', 'expires_in': 86400},
    )

    result = tiktok.refresh_tiktok_token(account)

    account.refresh_from_db()
    assert result == 'tk-new'
    assert account.access_token == 'tk-new'
    assert account.refresh_token == 'r2'
    assert account.token_expires_at is not None


@pytest.mark.django_db
def test_refresh_tiktok_without_creds_raises(settings, current_site):
    settings.TIKTOK_CLIENT_KEY = ''
    settings.TIKTOK_CLIENT_SECRET = ''
    account = _account(current_site, platform=Platform.TIKTOK, username='tk', refresh_token='r1')
    with pytest.raises(TokenMissingError):
        tiktok.refresh_tiktok_token(account)


@pytest.mark.django_db
def test_sync_refreshes_expiring_token(monkeypatch, current_site):
    account = _account(current_site, access_token='tok', external_user_id='1', is_active=True)
    account.token_expires_at = timezone.now() + timedelta(hours=1)  # dentro da janela do Instagram
    account.save()
    calls = {'n': 0}

    def fake_refresh(acc):
        calls['n'] += 1
        return 'new'

    monkeypatch.setitem(cmd.REFRESHERS, Platform.INSTAGRAM, (fake_refresh, timedelta(days=7)))
    monkeypatch.setitem(
        cmd.SERVICES, Platform.INSTAGRAM,
        (lambda acc, limit=6: [], instagram.normalize_instagram_post),
    )

    call_command('sync_social_posts', stdout=StringIO(), stderr=StringIO())

    assert calls['n'] == 1


# ── Home (renderização da seção) ───────────────────────────────────────────────

@pytest.mark.django_db
def test_home_renders_social_section_with_manual_post(client, current_site):
    SiteExtension.objects.update_or_create(
        site=current_site,
        defaults={
            'social_section_enabled': True,
            'social_section_title': 'Acompanhe a Komuniki nas redes',
            'instagram_url': 'https://www.instagram.com/komunikiescola/',
        },
    )
    account = _account(current_site, is_active=True)
    _post(account, caption='Post manual visível', permalink='https://www.instagram.com/p/MANUAL/', is_manual=True, external_id='')

    response = client.get(reverse('school:home'))

    content = response.content.decode()
    assert response.status_code == 200
    assert 'Acompanhe a Komuniki nas redes' in content
    assert 'Post manual visível' in content
    assert 'https://www.instagram.com/p/MANUAL/' in content


@pytest.mark.django_db
def test_home_social_section_falls_back_to_buttons_without_posts(client, current_site):
    SiteExtension.objects.update_or_create(
        site=current_site,
        defaults={
            'social_section_enabled': True,
            'instagram_url': 'https://www.instagram.com/komunikiescola/',
            'tiktok_url': 'https://www.tiktok.com/@komuniki',
        },
    )

    response = client.get(reverse('school:home'))

    content = response.content.decode()
    assert response.status_code == 200
    # Sem posts: ainda mostra o botão do Instagram, sem quebrar.
    assert 'https://www.instagram.com/komunikiescola/' in content
    # O botão do TikTok foi removido (o backend do TikTok permanece no sistema).
    assert 'https://www.tiktok.com/@komuniki' not in content


@pytest.mark.django_db
def test_home_hides_social_section_when_disabled(client, current_site):
    SiteExtension.objects.update_or_create(
        site=current_site,
        defaults={'social_section_enabled': False, 'instagram_url': 'https://www.instagram.com/komunikiescola/'},
    )
    account = _account(current_site, is_active=True)
    _post(account, caption='Nao deve aparecer', is_manual=True, external_id='')

    response = client.get(reverse('school:home'))

    content = response.content.decode()
    assert response.status_code == 200
    assert 'Nao deve aparecer' not in content
    assert 'social-section-title' not in content


@pytest.mark.django_db
def test_home_social_grid_shows_six_on_desktop_three_on_mobile(client, current_site):
    SiteExtension.objects.update_or_create(
        site=current_site, defaults={'social_section_enabled': True},
    )
    account = _account(current_site, is_active=True)
    for i in range(7):  # 7 posts: confirma que só 6 entram (limite da view)
        _post(
            account, caption=f'PostNum{i}', permalink=f'https://ig/p/{i}',
            is_manual=True, external_id='', published_at=timezone.now() - timedelta(hours=i),
        )

    response = client.get(reverse('school:home'))

    content = response.content.decode()
    assert response.status_code == 200
    assert 'lg:grid-cols-3' in content           # desktop: grade 3x2 = 6
    assert content.count('hidden sm:flex') == 3   # 4º-6º ficam ocultos no mobile
    assert 'PostNum5' in content                  # 6 mais recentes entram
    assert 'PostNum6' not in content              # 7º (mais antigo) fica de fora


@pytest.mark.django_db
def test_home_hides_tiktok_cards_when_show_tiktok_off(client, current_site):
    SiteExtension.objects.update_or_create(
        site=current_site,
        defaults={'social_section_enabled': True, 'social_show_instagram': True, 'social_show_tiktok': False},
    )
    ig = _account(current_site, username='ig', is_active=True)
    tk = _account(current_site, platform=Platform.TIKTOK, username='tk', is_active=True)
    _post(ig, caption='Post do Instagram', is_manual=True, external_id='')
    _post(tk, caption='Post do TikTok', is_manual=True, external_id='')

    content = client.get(reverse('school:home')).content.decode()

    assert 'Post do Instagram' in content
    assert 'Post do TikTok' not in content


@pytest.mark.django_db
def test_home_hides_instagram_button_and_cards_when_show_instagram_off(client, current_site):
    # URL exclusiva da seção (o rodapé tem um link fixo de Instagram próprio).
    section_ig_url = 'https://www.instagram.com/komuniki_secao_teste/'
    SiteExtension.objects.update_or_create(
        site=current_site,
        defaults={
            'social_section_enabled': True,
            'social_show_instagram': False,
            'social_show_tiktok': True,
            'instagram_url': section_ig_url,
        },
    )
    ig = _account(current_site, username='ig', is_active=True)
    tk = _account(current_site, platform=Platform.TIKTOK, username='tk', is_active=True)
    _post(ig, caption='Post do Instagram', is_manual=True, external_id='')
    _post(tk, caption='Post do TikTok', is_manual=True, external_id='')

    content = client.get(reverse('school:home')).content.decode()

    assert section_ig_url not in content      # botão do Instagram da seção escondido
    assert 'Post do Instagram' not in content  # cards do Instagram escondidos
    assert 'Post do TikTok' in content         # TikTok continua aparecendo


@pytest.mark.django_db
def test_toggle_feed_view_updates_site_settings(client, current_site, django_user_model):
    admin = django_user_model.objects.create_superuser(
        username='admintoggle', email='admintoggle@example.com', password='pw-12345!',
    )
    client.force_login(admin)
    ext, _ = SiteExtension.objects.update_or_create(
        site=current_site,
        defaults={'social_section_enabled': True, 'social_show_instagram': True, 'social_show_tiktok': True},
    )

    # Envia só "enabled" e "show_instagram" marcados: TikTok deve desligar.
    client.post(reverse('admin:social_socialpost_toggle_feed'), {'enabled': 'on', 'show_instagram': 'on'})

    ext.refresh_from_db()
    assert ext.social_section_enabled is True
    assert ext.social_show_instagram is True
    assert ext.social_show_tiktok is False


@pytest.mark.django_db
def test_socialpost_changelist_renders_feed_toggles(client, current_site, django_user_model):
    admin = django_user_model.objects.create_superuser(
        username='adminlist', email='adminlist@example.com', password='pw-12345!',
    )
    client.force_login(admin)
    SiteExtension.objects.update_or_create(site=current_site, defaults={'social_section_enabled': True})

    content = client.get(reverse('admin:social_socialpost_changelist')).content.decode()

    assert 'Exibição na home' in content
    assert 'name="enabled"' in content
    assert 'name="show_instagram"' in content
    assert 'name="show_tiktok"' in content


@pytest.mark.django_db
def test_home_reflects_disabling_after_initial_render(client, current_site):
    # Regressão: o framework de Sites cacheia a SiteExtension no processo, então
    # desligar a seção não surtia efeito até reiniciar. O signal de clear_cache corrige.
    ext, _ = SiteExtension.objects.update_or_create(
        site=current_site, defaults={'social_section_enabled': True},
    )
    assert 'social-section-title' in client.get(reverse('school:home')).content.decode()

    ext.social_section_enabled = False
    ext.save()

    assert 'social-section-title' not in client.get(reverse('school:home')).content.decode()


@pytest.mark.django_db
def test_home_social_section_does_not_leak_other_site(client, current_site):
    SiteExtension.objects.update_or_create(
        site=current_site, defaults={'social_section_enabled': True},
    )
    other_site = Site.objects.create(domain='other.testserver', name='Outro')
    other_account = _account(other_site, username='outro', is_active=True)
    _post(other_account, caption='Conteudo de outro site', is_manual=True, external_id='')

    response = client.get(reverse('school:home'))

    content = response.content.decode()
    assert 'Conteudo de outro site' not in content
