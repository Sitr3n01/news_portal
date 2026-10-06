"""Busca do portal: os sete caminhos continuam achando, sem duplicar e sem vazar rascunho."""

import pytest
from django.urls import reverse

from apps.news.models import Article, Category, Tag
from apps.news.testing import make_article, make_site

# ── Busca: os sete caminhos continuam achando, sem duplicar ─────────────────


@pytest.mark.django_db
def test_busca_acha_por_titulo_excerpt_conteudo_tag_categoria_e_autor(client, django_user_model):
    """Trava da reestruturação: os termos que cruzam join saíram para uma subquery.

    Antes, tag/categoria/autor entravam no mesmo OR do título/conteúdo. O join M2M
    de tags multiplicava as linhas e forçava um `.distinct()`, que o Paginator
    pagava duas vezes (COUNT + página). Agora são semi-join — o resultado precisa
    continuar idêntico.
    """
    site = make_site()
    categoria = Category.objects.create(name='Zebrapolitica', slug='zebrapolitica')
    autor = django_user_model.objects.create_user(
        username='reporter', password='x', first_name='Girafanome', last_name='Girafasobrenome',
    )

    por_titulo = make_article(site, slug='por-titulo')
    por_titulo.title = 'Elefantetitulo em pauta'
    por_titulo.save()

    por_excerpt = make_article(site, slug='por-excerpt')
    por_excerpt.excerpt = 'Resumo com Rinoceronteresumo dentro'
    por_excerpt.save()

    por_conteudo = make_article(site, slug='por-conteudo')
    por_conteudo.content = 'Corpo com Hipopotamocorpo dentro'
    por_conteudo.save()

    por_tag = make_article(site, slug='por-tag')
    tag = Tag.objects.create(name='Leopardotag', slug='leopardotag')
    por_tag.tags.add(tag)
    por_tag.save()  # ParentalManyToManyField so persiste no save()

    por_categoria = make_article(site, slug='por-categoria')
    por_categoria.category = categoria
    por_categoria.save()

    por_autor = make_article(site, slug='por-autor')
    por_autor.author = autor
    por_autor.save()

    casos = [
        ('Elefantetitulo', por_titulo),
        ('Rinoceronteresumo', por_excerpt),
        ('Hipopotamocorpo', por_conteudo),
        ('Leopardotag', por_tag),
        ('Zebrapolitica', por_categoria),
        ('Girafanome', por_autor),
        ('Girafasobrenome', por_autor),
    ]
    for termo, esperado in casos:
        response = client.get(reverse('news:search'), {'q': termo})
        assert response.status_code == 200
        encontrados = list(response.context['page_obj'])
        assert encontrados == [esperado], f'busca por {termo} devolveu {encontrados}'


@pytest.mark.django_db
def test_busca_nao_duplica_artigo_com_varias_tags_casando(client):
    """Sem `.distinct()`, o fan-out do join M2M não pode voltar.

    O artigo tem duas tags que casam com o mesmo termo: no desenho antigo isso
    trazia a mesma linha duas vezes.
    """
    site = make_site()
    art = make_article(site, slug='multi-tag')
    art.tags.add(Tag.objects.create(name='Pantanalnorte', slug='pantanalnorte'))
    art.tags.add(Tag.objects.create(name='Pantanalsul', slug='pantanalsul'))
    art.save()  # ParentalManyToManyField so persiste no save()

    response = client.get(reverse('news:search'), {'q': 'Pantanal'})

    assert list(response.context['page_obj']) == [art]


@pytest.mark.django_db
def test_busca_nao_vaza_rascunho_por_nenhum_dos_caminhos(client, django_user_model):
    """Trava de seguranca: a subquery precisa manter o escopo de status.

    A reestruturacao moveu tag/categoria/autor para um `pk__in`. Se aquele filtro
    interno perdesse `status=PUBLISHED`, um rascunho passaria a aparecer na busca
    publica por tag, categoria ou nome do autor — vazamento de conteudo nao
    publicado.
    """
    site = make_site()
    categoria = Category.objects.create(name='Draftcategoria', slug='draftcategoria')
    autor = django_user_model.objects.create_user(
        username='rascunhista', password='x', first_name='Draftnome', last_name='Draftsobrenome',
    )

    rascunho = make_article(site, slug='rascunho-secreto', status=Article.Status.DRAFT)
    rascunho.title = 'Draftitulo confidencial'
    rascunho.excerpt = 'Draftresumo confidencial'
    rascunho.content = 'Draftcorpo confidencial'
    rascunho.category = categoria
    rascunho.author = autor
    rascunho.save()
    rascunho.tags.add(Tag.objects.create(name='Drafttag', slug='drafttag'))
    rascunho.save()

    for termo in (
        'Draftitulo', 'Draftresumo', 'Draftcorpo',
        'Drafttag', 'Draftcategoria', 'Draftnome', 'Draftsobrenome',
    ):
        response = client.get(reverse('news:search'), {'q': termo})
        assert response.status_code == 200
        assert list(response.context['page_obj']) == [], f'rascunho vazou na busca por {termo}'
        assert 'Draftitulo confidencial' not in response.content.decode()
