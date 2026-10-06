"""Corpo da notícia em blocos (StreamField): renderização, embed, imagem, CSP dos embeds e comentários de template."""

import pytest
from django.urls import reverse

from apps.media_library.models import MediaFile
from apps.news.models import Article
from apps.news.testing import make_article, make_image_upload, make_site

# ── Blocos de conteúdo do artigo ─────────────────────────────────────────────

def make_image_media(name='inline.jpg'):
    return MediaFile.objects.create(
        title='Inline',
        file=make_image_upload(name, size=(800, 600), fmt='JPEG'),
        file_type='image',
        alt_text='alt',
    )


# ── Fase 10: renderização unificada (StreamField) ─────────────────────────

@pytest.mark.django_db
def test_article_detail_renders_body(client, settings, tmp_path):
    """Artigo com body populado → renderiza via StreamField."""
    settings.MEDIA_ROOT = str(tmp_path)
    site = make_site(pk=settings.SITE_ID, domain='testserver')
    art = make_article(site, slug='has-body', status=Article.Status.PUBLISHED)

    from apps.news.blocks import ArticleStreamBlock

    block = ArticleStreamBlock()
    value = block.to_python([
        {'type': 'texto', 'value': '<p>Renderizado via StreamField.</p>'},
    ])
    art.body = block.get_prep_value(value)
    art.save()

    response = client.get(reverse('news:article_detail', args=['has-body']))
    html = response.content.decode()

    assert response.status_code == 200
    assert 'Renderizado via StreamField' in html


@pytest.mark.django_db
def test_article_detail_falls_back_to_content_when_body_empty(client, settings):
    """Artigo com body vazio mas content populado → fallback para content."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')
    art = make_article(site, slug='body-empty', status=Article.Status.PUBLISHED)
    art.body = None
    art.content = 'Conteúdo de fallback para renderização.'
    art.save()

    response = client.get(reverse('news:article_detail', args=['body-empty']))
    html = response.content.decode()

    assert response.status_code == 200
    assert 'Conteúdo de fallback para renderização.' in html


@pytest.mark.django_db
def test_article_detail_empty_body_and_content_renders_gracefully(client, settings):
    """Artigo sem body e sem content → renderiza sem erro (área vazia, não 500)."""
    site = make_site(pk=settings.SITE_ID, domain='testserver')
    art = make_article(site, slug='both-empty', status=Article.Status.PUBLISHED)
    art.body = None
    art.content = ''
    art.save()

    response = client.get(reverse('news:article_detail', args=['both-empty']))
    assert response.status_code == 200
    # Não deve conter fallback nenhum, mas também não deve ser 500



@pytest.mark.django_db
def test_csp_allows_instagram_and_tiktok_frames(client):
    response = client.get(reverse('news:list'))
    csp = response.headers.get('Content-Security-Policy', '')

    assert 'https://www.instagram.com' in csp
    assert 'https://www.tiktok.com' in csp
    assert 'https://www.youtube-nocookie.com' in csp  # YouTube segue permitido


# ── Fase 4: Article como Snippet + StreamField ──────────────────────────────


@pytest.mark.django_db
def test_article_streamfield_body_save_and_retrieve():
    """body StreamField aceita blocos e os recupera após save."""
    site = make_site()
    article = make_article(site, slug='stream-body')

    from apps.news.blocks import ArticleStreamBlock

    block = ArticleStreamBlock()
    value = block.to_python([
        {'type': 'titulo', 'value': {'texto': 'Título do bloco', 'nivel': 'h2'}},
        {'type': 'texto', 'value': '<p>Parágrafo de teste.</p>'},
    ])
    article.body = block.get_prep_value(value)
    article.save()

    article.refresh_from_db()
    assert article.body is not None
    assert len(article.body) == 2
    assert article.body[0].block_type == 'titulo'
    assert article.body[0].value['texto'] == 'Título do bloco'


@pytest.mark.django_db
def test_article_blocks_import_and_instantiate():
    """ArticleStreamBlock e todos os sub-blocos importam e instanciam sem erro."""
    from apps.news.blocks import (
        ArticleStreamBlock,
        CalloutBlock,
        EmbedBlock,
        HeadingBlock,
        ImageBlock,
        QuoteBlock,
        SeparatorBlock,
        SourceBlock,
    )

    # Instanciação individual
    HeadingBlock()
    ImageBlock()
    EmbedBlock()
    QuoteBlock()
    SeparatorBlock()
    CalloutBlock()
    SourceBlock()

    # Composição
    stream = ArticleStreamBlock()
    child_keys = set(stream.child_blocks.keys())
    expected = {'texto', 'titulo', 'citacao', 'separador', 'imagem', 'embed',
                'documento', 'destaque', 'tabela', 'fonte'}
    assert child_keys == expected


@pytest.mark.django_db
def test_embed_block_renders_without_leaking_comment():
    """O facade do embed renderiza sem vazar comentário de template."""
    from apps.news.blocks import EmbedBlock

    block = EmbedBlock()
    value = block.to_python({
        'embed_url': 'https://youtu.be/dQw4w9WgXcQ',
        'legenda': 'Vídeo oficial',
    })
    html = block.render(value)

    assert 'embed-facade' in html
    assert 'youtube-nocookie.com/embed/dQw4w9WgXcQ' in html
    # Comentário {# #} do Django é de UMA linha só: escrito em duas, vaza como
    # texto visível na matéria. Já aconteceu aqui e no password_reset_complete.
    assert '{#' not in html
    assert 'StreamField' not in html


def test_templates_have_no_multiline_hash_comments():
    """Nenhum {# #} multilinha nos templates — o lexer não os reconhece.

    A regex do Django é `{#.*?#}` sem re.DOTALL: um comentário quebrado em
    duas linhas não é removido e vaza renderizado para o leitor. Para textos
    longos, use {% comment %}. Guarda a árvore inteira porque o bug já
    apareceu duas vezes em templates diferentes.
    """
    import re
    from pathlib import Path

    from django.conf import settings

    # Mesma regex do lexer (django.template.base), sem re.DOTALL de propósito:
    # o que ela não casar é exatamente o que vaza renderizado.
    comment_re = re.compile(r'{#.*?#}')

    template_root = Path(settings.BASE_DIR) / 'templates'
    offenders = []
    for path in template_root.rglob('*.html'):
        text = path.read_text(encoding='utf-8')
        stripped = [m.span() for m in comment_re.finditer(text)]
        for opener in re.finditer(r'{#', text):
            if any(start <= opener.start() < end for start, end in stripped):
                continue
            lineno = text.count('\n', 0, opener.start()) + 1
            offenders.append(f'{path.relative_to(template_root)}:{lineno}')

    assert not offenders, (
        'Comentários {# #} multilinha (use {% comment %}): ' + ', '.join(offenders)
    )


# ── Bug D: bloco de imagem StreamField ─────────────────────────────────────


@pytest.mark.django_db
def test_image_block_renders_non_empty_img_src(settings, tmp_path):
    """templates/news/blocks/image.html renderiza <img src> preenchido com uma imagem real."""
    settings.MEDIA_ROOT = str(tmp_path)
    from io import BytesIO

    from django.core.files.base import ContentFile
    from django.template import Context, Template
    from wagtail.images import get_image_model

    image_model = get_image_model()
    from PIL import Image as PILImage
    buf = BytesIO()
    PILImage.new('RGB', (200, 150), (30, 90, 180)).save(buf, format='PNG')
    buf.seek(0)
    img = image_model.objects.create(
        title='Inline Block Image',
        file=ContentFile(buf.read(), name='inline.png'),
        width=200,
        height=150,
        file_size=buf.tell(),
    )

    template = Template(
        '{% load wagtailimages_tags %}'
        '{% include "news/blocks/image.html" with value=value %}'
    )

    html = template.render(Context({
        'value': {
            'imagem': img,
            'legenda': 'Crédito da foto',
        },
    }))

    assert 'src="' in html
    assert 'src=""' not in html
    assert 'Crédito da foto' in html


@pytest.mark.django_db
def test_image_block_renders_nothing_when_no_image():
    """Bloco de imagem não renderiza nada quando value.imagem é None/vazio."""
    from django.template import Context, Template

    template = Template(
        '{% load wagtailimages_tags %}'
        '{% include "news/blocks/image.html" with value=value %}'
    )

    html = template.render(Context({
        'value': {
            'imagem': None,
            'legenda': '',
        },
    }))

    assert 'src="' not in html or html.strip() == ''
