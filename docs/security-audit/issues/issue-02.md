Título: [Segurança] Favoritar/curtir por ID expõe notícias não publicadas no painel do leitor
Labels sugeridas: security, severidade: alta

## Descrição
`toggle_bookmark` e `toggle_like` buscam a notícia só pelo ID (`get_object_or_404(Article,
id=article_id)`), sem `status=PUBLISHED` nem `Article.on_site`. O painel do leitor
(`/news/account/`) lista os favoritos com `Article.objects`, sem filtro de status, e renderiza o
título e — quando não há resumo — o conteúdo inteiro da notícia (o `line-clamp` é só CSS).

Relacionado (baixa): as mesmas rotas e `add_comment` fogem do isolamento por Site que o projeto
adota ("Views públicas usam `Model.on_site`, nunca `Model.objects`").

## Por que é explorável
Qualquer pessoa cria conta de leitor, confirma o e-mail e faz `POST /news/toggle-bookmark/<n>/` para
n = 1..N (IDs sequenciais). Rascunhos, agendadas e arquivadas aparecem em `/news/account/` com
título e texto.

Confirmado com teste dinâmico: o rascunho dá 404 na URL pública, mas título e conteúdo aparecem no
painel após o POST.

## Evidência
- `apps/news/views.py:436-438` e `:462-464`
```python
def toggle_bookmark(request, article_id):
    article = get_object_or_404(Article, id=article_id)
```
- `apps/news/views.py:398-409` (`saved_articles = Article.objects.filter(bookmarks__user=user)`, sem
  status)
- `templates/news/account/dashboard.html:105-106` (`{{ article.title }}`, `{{
  article.excerpt|default:article.content|striptags }}`)
- Isolamento por Site: `apps/news/views.py:438, 464, 490, 398-409`

## Impacto
Vazamento de conteúdo editorial não publicado (matérias sob embargo, agendadas ou retiradas do ar)
para qualquer leitor. Com multi-site ativado, também mistura dados entre os portais.

## Sugestão de correção
```python
def _published_article_or_404(article_id):
    return get_object_or_404(Article.on_site, id=article_id, status=Article.Status.PUBLISHED)

# toggle_bookmark / toggle_like / add_comment
article = _published_article_or_404(article_id)

# user_dashboard
saved_articles = Article.on_site.filter(status=Article.Status.PUBLISHED, bookmarks__user=user)...
liked_articles = Article.on_site.filter(status=Article.Status.PUBLISHED, likes__user=user)...
```

## Critérios de aceite
- [ ] POST em `/news/toggle-bookmark/<id>/` e `/news/toggle-like/<id>/` para notícia em rascunho,
      arquivada ou de outro Site retorna 404 e não cria registro.
- [ ] `/news/account/` lista só notícias publicadas do Site atual, mesmo que existam favoritos
      antigos para outras.
- [ ] `add_comment` usa `Article.on_site`.
- [ ] Testes cobrindo rascunho e notícia de outro Site.
