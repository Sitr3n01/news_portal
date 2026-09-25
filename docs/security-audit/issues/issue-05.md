Título: [Segurança] Prévia de newsletter mostra qualquer notícia (inclusive rascunho) a qualquer staff
Labels sugeridas: security, severidade: média

## Descrição
`newsletter_preview` exige só `is_staff` e busca a notícia por ID com `Article.objects`: não confere
`news.view_article`, status nem Site. O Administrador Komuniki (staff, sem permissão de notícias) lê
qualquer notícia; Editor e Repórter (não staff) não alcançam a rota. A rota não é linkada em nenhuma
tela.

## Por que é explorável
`GET /news/newsletter/preview/<n>/` percorrendo IDs sequenciais devolve o e-mail renderizado de
rascunhos e agendadas.

Confirmado com teste dinâmico: Administrador Komuniki sem `news.view_article` recebeu 200 com o
título do rascunho.

## Evidência
- `apps/news/views.py:524-536`
```python
@staff_member_required
def newsletter_preview(request, article_id):
    ...
    article = get_object_or_404(Article, id=article_id)
```

## Impacto
Vazamento de conteúdo não publicado para papéis sem relação com o portal de notícias.

## Sugestão de correção
```python
@login_required
def newsletter_preview(request, article_id):
    if not request.user.has_perm('news.view_article'):
        raise PermissionDenied
    article = get_object_or_404(Article.on_site, id=article_id)
```
Ou remover a rota, se não houver uso.

## Critérios de aceite
- [ ] Conta staff sem `news.view_article` recebe 403.
- [ ] Quem tem `news.view_article` acessa (ou a rota foi removida e as URLs antigas dão 404).
- [ ] Busca restrita a `Article.on_site`; teste de regressão.
