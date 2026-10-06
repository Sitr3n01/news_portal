"""Conversão dos blocos legados para StreamField (migração news.0021)."""

# ── Conversão dos blocos legados (migration news.0021) ─────────────────────


def _legacy(block_type, *, rich_text='', media_id=None, caption='', embed_url=''):
    return {
        'block_type': block_type, 'rich_text': rich_text, 'media_id': media_id,
        'caption': caption, 'embed_url': embed_url,
    }


def test_legacy_conversion_maps_each_block_type():
    """rich_text -> texto, image -> imagem, embed -> embed, na ordem recebida."""
    from apps.news.legacy_blocks import build_stream_data

    stream = build_stream_data(
        [
            _legacy('rich_text', rich_text='<p>Corpo legado.</p>'),
            _legacy('image', media_id=7, caption='Legenda da foto'),
            _legacy('embed', embed_url='https://www.youtube.com/watch?v=abc', caption='Legenda do video'),
        ],
        image_pk_for=lambda media_id: 42 if media_id == 7 else None,
    )

    assert [item['type'] for item in stream] == ['texto', 'imagem', 'embed']
    assert stream[0]['value'] == '<p>Corpo legado.</p>'
    assert stream[1]['value'] == {'imagem': 42, 'legenda': 'Legenda da foto'}
    assert stream[2]['value'] == {
        'embed_url': 'https://www.youtube.com/watch?v=abc', 'legenda': 'Legenda do video',
    }
    # Cada bloco precisa de id próprio, ou o Wagtail trata como o mesmo bloco.
    assert len({item['id'] for item in stream}) == 3


def test_legacy_conversion_degrades_image_without_destination_to_caption():
    """Imagem sem cms_media.Image vira parágrafo com a legenda — não desaparece."""
    from apps.news.legacy_blocks import build_stream_data

    stream = build_stream_data(
        [_legacy('image', media_id=99, caption='Foto do <laboratório>')],
        image_pk_for=lambda media_id: None,
    )

    assert len(stream) == 1
    assert stream[0]['type'] == 'texto'
    # Legenda é dado de usuário e vai para dentro de HTML: tem de sair escapada.
    assert stream[0]['value'] == '<p>Foto do &lt;laboratório&gt;</p>'


def test_legacy_conversion_reports_outcome_counts():
    """O contador de desfechos alimenta o relatório de audit_article_blocks."""
    from collections import Counter

    from apps.news.legacy_blocks import build_stream_data

    outcomes = Counter()
    build_stream_data(
        [
            _legacy('rich_text', rich_text='<p>ok</p>'),
            _legacy('image', media_id=7, caption='tem destino'),
            _legacy('image', media_id=None, caption='sem destino'),
            _legacy('image', media_id=None),
            _legacy('embed'),
            _legacy('rich_text'),
        ],
        image_pk_for=lambda media_id: 42 if media_id == 7 else None,
        outcomes=outcomes,
    )

    assert outcomes['texto'] == 1
    assert outcomes['imagem'] == 1
    assert outcomes['imagem_sem_destino_com_legenda'] == 1
    assert outcomes['imagem_sem_destino_perdida'] == 1
    assert outcomes['embed_sem_url_perdido'] == 1
    assert outcomes['vazio_descartado'] == 1


def test_legacy_conversion_groups_by_article_preserving_order():
    from apps.news.legacy_blocks import group_by_article

    blocks = [
        {'article_id': 1, 'order': 0}, {'article_id': 1, 'order': 1},
        {'article_id': 2, 'order': 0},
    ]
    grouped = group_by_article(blocks)

    assert set(grouped) == {1, 2}
    assert [b['order'] for b in grouped[1]] == [0, 1]
