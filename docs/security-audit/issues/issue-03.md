Título: [Segurança] Upload de HTML/SVG em mídia e documentos permite XSS armazenado
Labels sugeridas: security, severidade: alta

## Descrição
A Biblioteca de mídia (Django admin) aceita qualquer extensão — inclusive `.html` e `.svg` — e os
Documentos do Wagtail não têm `WAGTAILDOCS_EXTENSIONS`. O nginx serve `/media/` direto, com o
Content-Type do `mime.types` (`text/html`, `image/svg+xml`), sem `Content-Disposition: attachment`,
e o bloco `/media/` (que só usa `expires`) herda do `server` a CSP com `script-src 'unsafe-inline'`.
A view `/documents/` do Wagtail aplica sandbox, mas o arquivo bruto em `/media/documents/` não passa
por ela.

## Por que é explorável
Um Administrador Komuniki (mídia) ou Editor de Notícias (documentos) envia `evil.html`. Um
superusuário que abrir o link em `https://komuniki.com.br/media/...` executa JavaScript na mesma
origem do `/admin/` e do `/cms/`: o script lê o `csrftoken` de uma página do painel e cria ou
promove contas.

Confirmado com teste dinâmico: `.html` e `.svg` foram aceitos na Biblioteca de mídia (POST no admin
→ 302) e `.html` passou na validação do modelo de Documento do Wagtail (`full_clean`).

## Evidência
- `apps/media_library/admin.py:97-103`
```python
def clean_file(self):
    uploaded = self.cleaned_data.get('file')
    # ... a biblioteca aceita qualquer arquivo.
    if uploaded and Path(uploaded.name).suffix.lower() in ALLOWED_IMAGE_EXTENSIONS:
        validate_uploaded_image(uploaded)
    return uploaded
```
- `apps/media_library/admin.py:27` (`.svg` tratado como imagem), `apps/media_library/models.py:37`
- `config/settings/base.py:200-201` (sem `WAGTAILDOCS_EXTENSIONS`)
- `docker/nginx/nginx.conf:216-219` (`location /media/`) e `:167` (CSP herdada)

## Impacto
XSS armazenado na origem dos painéis → escalada de uma conta com upload até superusuário (ação em
nome de quem abrir o link).

## Sugestão de correção
1. Allowlist na Biblioteca de mídia (validador no modelo e no form); sem `.svg`, `.html`, `.htm`,
   `.xhtml`, `.xml`, `.js`.
2. `WAGTAILDOCS_EXTENSIONS = ['pdf', 'doc', 'docx', 'odt', 'rtf', 'txt', 'csv', 'xls', 'xlsx',
   'ppt', 'pptx']`.
3. nginx: `location /media/documents/ { internal; }` (documentos só pela view do Wagtail) e bloquear
   tipos ativos com `location ~* ^/media/.+\.(html?|xhtml|svg|xml|js)$ { return 404; }`. Se o bloco
   `/media/` ganhar `add_header` próprio (ex.: `Content-Disposition: attachment`, `CSP: sandbox`),
   repetir nele HSTS/nosniff — `add_header` num location cancela a herança do `server`.
4. Varrer os volumes: `find /app/media -iregex '.*\.\(html?\|xhtml\|svg\|xml\|js\)'` e remover o que
   houver.
5. Médio prazo: servir uploads de um domínio próprio, sem cookies dos painéis.

## Critérios de aceite
- [ ] Upload de `.html`, `.htm`, `.svg`, `.xml` e `.js` é recusado na Biblioteca de mídia e em
      Documentos (teste automatizado).
- [ ] `GET /media/documents/<arquivo>` não é servido diretamente; documentos saem só por
      `/documents/<id>/<nome>`.
- [ ] `curl -I https://<domínio>/media/<arquivo>.html` não devolve `text/html` executável (404 ou
      attachment + sandbox).
- [ ] Varredura dos volumes de produção sem arquivos ativos remanescentes.
