"""Contagem de leituras: dedup no cache, sem sessão no banco e com o IP real atrás do proxy."""

import pytest

from apps.news.testing import make_article, make_site

# ── view_count: dedup sem inchar django_session ─────────────────────────────


@pytest.mark.django_db
def test_view_count_conta_uma_vez_e_nao_cria_sessao(client):
    """Duas leituras seguidas contam uma vez, e sem gravar linha em django_session.

    O marcador de "ja vi este artigo" ficava na sessao. Com sessao em banco e
    SESSION_SAVE_EVERY_REQUEST=True, era o unico motivo de trafego anonimo tocar
    django_session — cada crawler criava uma linha por artigo lido. Hoje o dedup
    vive no cache, com expiracao propria.
    """
    from django.contrib.sessions.models import Session

    site = make_site()
    art = make_article(site, slug='contagem-de-leitura')

    client.get(art.get_absolute_url())
    client.get(art.get_absolute_url())

    art.refresh_from_db()
    assert art.view_count == 1
    assert Session.objects.count() == 0


@pytest.mark.django_db
def test_view_count_volta_a_contar_quando_a_chave_de_dedup_expira(client):
    """Leitores distintos (ou a mesma pessoa depois da janela) contam de novo."""
    from django.core.cache import cache

    site = make_site()
    art = make_article(site, slug='contagem-expira')

    client.get(art.get_absolute_url())
    cache.clear()
    client.get(art.get_absolute_url())

    art.refresh_from_db()
    assert art.view_count == 2


@pytest.mark.django_db
def test_view_count_distingue_leitores_atras_do_mesmo_proxy(client):
    """Dois visitantes anônimos distintos contam duas vezes, não uma.

    Regressão real: o gunicorn preenche REMOTE_ADDR com o peer da conexão, que
    atrás do nginx é sempre o container do proxy. Deduplicar por REMOTE_ADDR
    colapsava todo visitante anônimo numa chave só — o contador subiria no
    máximo uma vez a cada 30 min por artigo, no site inteiro. O IP real chega em
    X-Forwarded-For, que o nginx substitui (não anexa).
    """
    site = make_site()
    art = make_article(site, slug='atras-do-proxy')
    url = art.get_absolute_url()

    # Mesmo REMOTE_ADDR (o proxy), leitores diferentes no X-Forwarded-For.
    client.get(url, REMOTE_ADDR='172.18.0.5', HTTP_X_FORWARDED_FOR='203.0.113.10')
    client.get(url, REMOTE_ADDR='172.18.0.5', HTTP_X_FORWARDED_FOR='203.0.113.20')

    art.refresh_from_db()
    assert art.view_count == 2


@pytest.mark.django_db
def test_view_count_ainda_deduplica_o_mesmo_leitor(client):
    """O mesmo IP real, repetido, continua contando uma vez só."""
    site = make_site()
    art = make_article(site, slug='mesmo-leitor')
    url = art.get_absolute_url()

    client.get(url, REMOTE_ADDR='172.18.0.5', HTTP_X_FORWARDED_FOR='203.0.113.10')
    client.get(url, REMOTE_ADDR='172.18.0.5', HTTP_X_FORWARDED_FOR='203.0.113.10')

    art.refresh_from_db()
    assert art.view_count == 1
