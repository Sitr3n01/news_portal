Título: [Segurança] Endurecer a CSP de script-src e remover o |safe residual
Labels sugeridas: security, severidade: baixa

## Descrição
A CSP do Django (`config/settings/base.py:454-459`) e a do nginx (`docker/nginx/nginx.conf:167`)
permitem `'unsafe-inline'` e `'unsafe-eval'` em `script-src`, o que anula a CSP como mitigação de
XSS (é o que torna o XSS de upload executável). Há também um `|safe` residual em
`templates/accounts/password_reset/new_password.html:44`, contra a regra do projeto — hoje
inofensivo (o help text vem dos validadores do Django).

## Por que é explorável
Não é explorável sozinho: amplifica qualquer injeção que escape do autoescape ou da sanitização.

## Evidência
```python
# config/settings/base.py:454-459 (resumido em uma linha)
'script-src': [SELF, UNSAFE_INLINE, UNSAFE_EVAL, 'https://challenges.cloudflare.com'],
```
```django
{# templates/accounts/password_reset/new_password.html:44 #}
<div class="mt-1 text-xs text-slate-500 font-ui">{{ field.help_text|safe }}</div>
```

## Impacto
Defesa em profundidade ausente contra XSS.

## Sugestão de correção
- Trocar o Alpine pelo build CSP (`@alpinejs/csp`) para remover `'unsafe-eval'`.
- Mover scripts inline para `static/` ou usar nonce do django-csp (`{{ request.csp_nonce }}`) e
  retirar `'unsafe-inline'` de `script-src`, mantendo Django e nginx com políticas iguais (o
  navegador aplica a interseção).
- Trocar `{{ field.help_text|safe }}` por `{{ field.help_text }}` (o texto do Django já vem marcado
  como seguro).

## Critérios de aceite
- [ ] Nenhum `|safe` em `templates/` (verificação no CI).
- [ ] `script-src` sem `'unsafe-eval'` e sem `'unsafe-inline'` no Django e no nginx.
- [ ] Portais e painéis sem violações de CSP no console (testes E2E).
