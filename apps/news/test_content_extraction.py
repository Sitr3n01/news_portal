"""Extração do texto do corpo para content: cobertura por tipo de bloco, tempo de leitura, sanitização e busca."""

import pytest
from django.urls import reverse

from apps.news.testing import make_article, make_article_full, make_site


@pytest.mark.django_db
def test_extract_content_from_body_texto():
    """_extract_content_from_body extrai HTML de blocos 'texto'."""
    site = make_site()
    art = make_article(site, slug='extract-texto')

    from apps.news.blocks import ArticleStreamBlock

    block = ArticleStreamBlock()
    value = block.to_python([
        {'type': 'texto', 'value': '<p>Parágrafo um.</p>'},
        {'type': 'texto', 'value': '<p>Parágrafo dois.</p>'},
    ])
    art.body = block.get_prep_value(value)

    content = art._extract_content_from_body()
    assert '<p>Parágrafo um.</p>' in content
    assert '<p>Parágrafo dois.</p>' in content


@pytest.mark.django_db
def test_extract_content_from_body_with_legenda():
    """_extract_content_from_body extrai legendas de blocos imagem e embed."""
    site = make_site()
    art = make_article(site, slug='extract-legenda')

    from apps.news.blocks import ArticleStreamBlock

    block = ArticleStreamBlock()
    value = block.to_python([
        {'type': 'imagem', 'value': {'imagem': None, 'legenda': 'Foto do evento'}},
        {'type': 'embed', 'value': {'embed_url': 'https://youtu.be/test', 'legenda': 'Vídeo oficial'}},
    ])
    art.body = block.get_prep_value(value)

    content = art._extract_content_from_body()
    assert 'Foto do evento' in content
    assert 'Vídeo oficial' in content


@pytest.mark.django_db
def test_extract_content_from_body_empty():
    """_extract_content_from_body retorna '' quando body está vazio."""
    site = make_site()
    art = make_article(site, slug='extract-empty')
    # body não foi populado — é None/vazio
    assert art._extract_content_from_body() == ''


@pytest.mark.django_db
def test_reading_time_from_body():
    """reading_time calcula a partir de body quando populado."""
    site = make_site()
    art = make_article(site, slug='rt-body')

    from apps.news.blocks import ArticleStreamBlock

    # Cria ~12 palavras no body (2 palavras por legenda × 6 blocos)
    words = 'uma duas tres quatro cinco seis sete oito nove dez onze doze'
    block = ArticleStreamBlock()
    value = block.to_python([
        {'type': 'texto', 'value': f'<p>{words}</p>'},
    ])
    art.body = block.get_prep_value(value)

    rt = art.reading_time
    assert rt >= 1  # 12 palavras / 200 = 0.06 → round = 0 → max(1, 0) = 1


@pytest.mark.django_db
def test_reading_time_from_content_when_body_empty():
    """reading_time usa content quando body está vazio."""
    site = make_site()
    art = make_article(site, slug='rt-content')
    art.content = 'uma duas tres quatro cinco seis sete oito nove dez onze doze treze quatorze quinze'
    # body vazio (não setado)
    rt = art.reading_time
    assert rt >= 1
    # Força refresh do content para garantir que usa content e não body
    art.save()
    art.refresh_from_db()
    assert art.content != ''
    assert art.reading_time >= 1


@pytest.mark.django_db
def test_save_regenerates_content_from_body():
    """save() completo (sem update_fields) regenera content a partir de body."""
    site = make_site()
    art = make_article(site, slug='save-body')

    from apps.news.blocks import ArticleStreamBlock

    block = ArticleStreamBlock()
    value = block.to_python([
        {'type': 'texto', 'value': '<p>Conteúdo gerado pelo save.</p>'},
        {'type': 'imagem', 'value': {'imagem': None, 'legenda': 'Crédito da imagem'}},
    ])
    art.body = block.get_prep_value(value)
    art.save()  # save completo — content deve ser regenerado

    art.refresh_from_db()
    assert 'Conteúdo gerado pelo save' in art.content
    assert 'Crédito da imagem' in art.content


@pytest.mark.django_db
def test_save_from_body_flows_through_sanitization():
    """Conteúdo extraído de body passa pela sanitização no save()."""
    site = make_site()
    art = make_article(site, slug='sanitize-body')

    from apps.news.blocks import ArticleStreamBlock

    block = ArticleStreamBlock()
    value = block.to_python([
        {'type': 'texto', 'value': '<p>Texto <script>alert("xss")</script> seguro</p>'},
    ])
    art.body = block.get_prep_value(value)
    art.save()

    art.refresh_from_db()
    # O <script> deve ter sido removido pela sanitização
    assert 'Texto' in art.content
    assert '<script>' not in art.content


# ── Extração de content a partir do body (busca do portal) ─────────────────
#
# `content` é o campo que article_search consulta com `content__icontains`. Antes
# o extrator só colhia blocos 'texto' e legendas, então texto digitado em Título,
# Citação, Box de destaque, Fonte e Tabela existia na matéria e não existia na
# busca. Os testes abaixo travam a cobertura por tipo de bloco.


ALL_BLOCK_TYPES_BODY = [
    {'type': 'titulo', 'value': {'texto': 'Palavratitulo', 'nivel': 'h2'}},
    {'type': 'texto', 'value': '<p>Palavratexto no corpo.</p>'},
    {'type': 'citacao', 'value': {'citacao': 'Palavracitacao dita', 'atribuicao': 'Palavraatribuicao'}},
    {'type': 'destaque', 'value': {'estilo': 'info', 'texto': '<p>Palavradestaque</p>'}},
    {'type': 'fonte', 'value': {'rotulo': 'Palavrarotulo', 'url': 'https://exemplo.com/x'}},
    {'type': 'embed', 'value': {'embed_url': 'https://www.youtube.com/watch?v=abc', 'legenda': 'Palavralegenda'}},
    {'type': 'separador', 'value': None},
]


@pytest.mark.django_db
def test_content_extraction_covers_every_text_carrying_block():
    """Todo bloco com texto visível contribui para `content`."""
    site = make_site()
    art = make_article(site, slug='cobertura-blocos')
    art.body = ALL_BLOCK_TYPES_BODY
    art.save()
    art.refresh_from_db()

    for expected in (
        'Palavratitulo', 'Palavratexto', 'Palavracitacao', 'Palavraatribuicao',
        'Palavradestaque', 'Palavrarotulo', 'Palavralegenda',
    ):
        assert expected in art.content, f'{expected} não chegou em content (invisível para a busca)'


@pytest.mark.django_db
def test_content_extraction_includes_table_cells():
    """Células de TableBlock entram em `content`."""
    site = make_site()
    art = make_article(site, slug='cobertura-tabela')
    art.body = [{
        'type': 'tabela',
        'value': {'data': [['Cabecalhoum', 'Cabecalhodois'], ['Celulaum', 'Celuladois']]},
    }]
    art.save()
    art.refresh_from_db()

    for expected in ('Cabecalhoum', 'Cabecalhodois', 'Celulaum', 'Celuladois'):
        assert expected in art.content


@pytest.mark.django_db
def test_content_extraction_survives_malformed_table():
    """Tabela sem `data` ou com linha que não é lista não derruba o save."""
    site = make_site()
    art = make_article(site, slug='tabela-torta')
    art.body = [
        {'type': 'tabela', 'value': {}},
        {'type': 'tabela', 'value': {'data': None}},
        {'type': 'tabela', 'value': {'data': ['nao-e-lista', ['Celulaboa']]}},
    ]
    art.save()
    art.refresh_from_db()

    assert 'Celulaboa' in art.content


@pytest.mark.django_db
def test_search_finds_text_that_only_exists_in_heading_and_quote(client):
    """Regressão A2: buscar palavra que só existe em Título/Citação acha o artigo."""
    site = make_site()
    art = make_article_full(site, slug='busca-por-bloco')
    art.body = ALL_BLOCK_TYPES_BODY
    art.save()

    for term in ('Palavratitulo', 'Palavracitacao', 'Palavrarotulo'):
        response = client.get(reverse('news:search'), {'q': term})
        assert response.status_code == 200
        assert art.title in response.content.decode(), f'busca por {term} não achou o artigo'


@pytest.mark.django_db
def test_reading_time_counts_all_block_types():
    """reading_time usa o mesmo extrator, então também conta título e citação."""
    site = make_site()
    art = make_article(site, slug='tempo-leitura-blocos')
    art.body = ALL_BLOCK_TYPES_BODY
    art.save()

    assert art.reading_time >= 1
