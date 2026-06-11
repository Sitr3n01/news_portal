# Manual do Portal de Notícias — Blog da Kelly

Este manual cobre todas as operações que um **Editor de Notícias** precisa realizar: publicar artigos, gerenciar categorias e tags, disparar newsletters e moderar comentários.

---

## 1. Publicar um Artigo

### 1.1 Criar um novo artigo

1. Na barra lateral, clique em **Blog da Kelly → Artigos**.
2. Clique em **Adicionar Artigo**.
3. Preencha os campos obrigatórios:
   - **Título** — aparece como cabeçalho principal da matéria
   - **URL amigável (slug)** — parte final do endereço (gerado automaticamente a partir do título; edite se necessário). Ex.: `minha-materia` → `kellyfarias.com.br/news/minha-materia/`
   - **Categoria** — seção principal da matéria (aparece no menu de navegação)
   - **Autor** — selecione o usuário responsável pela matéria

4. Preencha os campos opcionais que enriquecem a matéria:
   - **Resumo** — texto curto exibido nas listagens e nos compartilhamentos
   - **Imagem de capa** — imagem principal. O sistema redimensiona e otimiza automaticamente (converte para JPEG, máximo 1200×800px, qualidade otimizada).
   - **Legenda da imagem** — texto exibido abaixo da imagem de capa
   - **Tags** — palavras-chave livres (ex.: `evento`, `2026`). Digite para buscar ou criar.
   - **Destaque** — marque para que este artigo apareça em posição de destaque na home do portal
   - **Título SEO** e **Descrição SEO** — como o artigo aparece no Google (até 70 e 160 caracteres respectivamente). Se vazios, o sistema usa o título e o resumo.

5. Escolha o **Status**:
   - **Rascunho** — o artigo fica salvo mas invisível no site
   - **Publicado** — o artigo aparece no site; a data de publicação é marcada automaticamente no momento em que você salva com este status pela primeira vez
   - **Arquivado** — remove o artigo do site sem excluir

6. Clique em **Salvar**.

### 1.2 Adicionar blocos de conteúdo

O corpo do artigo é formado por **blocos**, adicionados na seção "Blocos de conteúdo" dentro do formulário do artigo.

| Tipo de bloco | Para que serve |
|--------------|----------------|
| **Texto** | Parágrafos, subtítulos, listas, links, negrito/itálico |
| **Imagem** | Seleciona uma imagem da Biblioteca de Mídia, com legenda opcional |
| **Vídeo / Post** | Cola o link de YouTube, Instagram ou TikTok; o embed é gerado automaticamente |

Para cada bloco, defina **Ordem**. Blocos aparecem em ordem crescente. Para reordenar, altere os números e salve.

> O campo **Conteúdo** do artigo é gerado automaticamente a partir dos blocos. Não é necessário preenchê-lo manualmente.

### 1.3 Sobre o editor de texto dos blocos

- Use negrito, itálico, listas, links e cabeçalhos normalmente.
- O sistema sanitiza o HTML ao salvar, removendo scripts e atributos perigosos.
- Embeds são montados de forma segura a partir da URL, sem colar HTML cru no artigo.

---

## 2. Categorias e Tags

### Categorias

Categorias organizam o portal em seções (como "Notícias", "Eventos", "Cultura"). Categorias-raiz (sem categoria pai) aparecem como abas no menu de navegação.

1. Clique em **Blog da Kelly → Categorias**.
2. Para criar: clique em **Adicionar Categoria**, preencha **Nome**, **URL amigável**, **Descrição** (opcional), **Categoria pai** (opcional, para subcategorias) e **Ordem**.
3. Salve.

> Uma categoria só aparece no menu se for raiz (sem `Categoria pai`) e se houver artigos publicados nela.

### Tags

Tags são palavras-chave livres que criam páginas de arquivo automáticas.

1. Clique em **Blog da Kelly → Tags**.
2. Para criar: clique em **Adicionar Tag**, preencha **Nome** e **URL amigável**.
3. Para usar: ao editar um artigo, pesquise pela tag no campo **Tags** ou crie ali mesmo.

---

## 3. Newsletter

### 3.1 Como funciona

O sistema de newsletter funciona em **duas etapas separadas**:

1. **Publicar o artigo** — ao salvar um artigo com status `Publicado`, o sistema o registra automaticamente como candidato para envio de newsletter. **Nenhum e-mail é enviado ainda.**
2. **Processar o envio** — um administrador técnico executa o comando de envio (`send_pending_newsletters`) ou você mesmo dispara manualmente pela ação do admin.

Essa separação existe para que publicar um artigo não bloqueie o painel nem sobrecarregue o servidor de e-mail.

### 3.2 Disparar a newsletter manualmente pelo admin

1. Clique em **Blog da Kelly → Artigos**.
2. Marque os artigos publicados que deseja enviar por e-mail.
3. No menu "Ação", selecione **"Enviar Newsletter para inscritos"** e clique em **Executar**.
4. O sistema criará uma entrega por inscrito ativo e enviará o lote. Um resumo (`enviadas / falhas / ignoradas`) aparecerá na tela.

> Esta ação pode ser executada mesmo em artigos já enviados anteriormente, permitindo reenvio manual pontual.

### 3.3 Monitorar entregas

1. Clique em **Blog da Kelly → Entregas de Newsletter**.
2. Cada linha representa um par (artigo × inscrito) com os campos:
   - **Status**: `Pendente`, `Enviado`, `Falhou`, `Ignorado`
   - **Tentativas**: quantas vezes o sistema tentou enviar
   - **Último erro**: mensagem de erro, se houver
   - **Enviado em**: horário de confirmação do envio

3. Use os filtros disponíveis para localizar falhas e reprocessar.

### 3.4 Gerenciar inscritos

1. Clique em **Blog da Kelly → Newsletter**.
2. A lista mostra todos os e-mails inscritos.
3. Para cancelar manualmente uma inscrição, abra o registro e desmarque **Ativo**.

### 3.5 Pré-visualizar um e-mail

Para ver como o e-mail ficará antes de enviar:
1. Acesse no navegador: `seudominio.com.br/news/newsletter/preview/<id-do-artigo>/` (requer login de staff)
2. A página renderiza o template HTML do e-mail com dados reais do artigo.

### 3.6 Configurar o remetente

Se os e-mails saem com remetente genérico, configure:
1. Clique em **Sistema → Configurações do Site**.
2. Preencha os campos **E-mail remetente da Newsletter** (ex.: `noticias@kellyfarias.com.br`) e **Nome remetente da Newsletter** (ex.: `Blog da Kelly`).
3. Salve.

---

## 4. Comentários

Leitores registrados podem comentar nos artigos.

### Moderar comentários

1. Clique em **Blog da Kelly → Comentários**.
2. A lista mostra todos os comentários de todos os artigos.
3. Para **ocultar** um comentário sem excluir: abra o registro, desmarque o campo **Visível** e salve. O comentário desaparece do site mas permanece no banco para auditoria.
4. Para **excluir** permanentemente: clique em **Excluir** na tela do comentário.

> O autor do comentário pode excluir o próprio comentário pelo site (botão na página do artigo). Comentários de outros usuários só podem ser removidos por administradores pelo painel.

---

## 5. Biblioteca de Mídia

A biblioteca de mídia é um repositório central de arquivos compartilhado entre os dois portais.

### Enviar um arquivo

1. Clique em **Sistema → Biblioteca de Mídia**.
2. Clique em **Adicionar Arquivo de Mídia**.
3. Preencha:
   - **Título** — nome descritivo para encontrar depois
   - **Arquivo** — envie o arquivo do seu computador
   - **Tipo de arquivo** — Imagem, Documento, Vídeo, Áudio ou Outro
   - **Texto alternativo** — descrição para imagens (acessibilidade e SEO)
   - **Pasta** — opcional; organiza arquivos em pastas hierárquicas
4. Salve.

### Organizar em pastas

1. Clique em **Pastas de Mídia → Adicionar**.
2. Dê um nome e, opcionalmente, selecione uma **Pasta superior** para criar subpastas.
3. Ao enviar arquivos, selecione a pasta no campo **Pasta**.

---

## 6. Usuários e Acesso

> Esta seção é para **Super Administradores** apenas.

### Criar um usuário

1. Clique em **Sistema → Usuários**.
2. Clique em **Adicionar Usuário**.
3. Preencha **Username**, **E-mail**, **Senha** e **Cargo**:
   - **Super Administrador** — acesso total
   - **Administrador Komuniki** — acesso à escola (home, páginas, depoimentos, mensagens, mídia)
   - **Editor de Notícias** — acesso ao portal de notícias (artigos, categorias, tags, comentários, newsletter, mídia)
4. Opcionalmente adicione **Foto de perfil** e **Biografia** (aparecem na página de autor do artigo).
5. Salve.

> O sistema sincroniza automaticamente o grupo de permissões com o cargo selecionado. Mudar o cargo revoga automaticamente os privilégios do cargo anterior.

### Alterar a senha de um usuário

1. Abra o usuário em **Sistema → Usuários**.
2. Clique no link **"Alterar senha"** no topo do formulário.
3. Digite a nova senha duas vezes e confirme.

---

## 7. Perguntas frequentes

**O artigo não aparece no site.**
Verifique: (1) o status está como `Publicado`? (2) o site correto está selecionado no campo **Site** do artigo?

**A newsletter não foi enviada mesmo publicando o artigo.**
Esperado por design. Publicar não envia automaticamente. Um administrador técnico precisa executar o comando de envio, ou você usa a ação manual descrita na seção 3.2.

**Um inscrito reclama que recebeu o e-mail com links quebrados.**
O domínio configurado em **Sistema → Sites** pode estar errado. Verifique se o campo **Domain** contém o domínio correto (ex.: `kellyfarias.com.br`).

**Quero ver quantas pessoas abriram o artigo.**
O campo **Visualizações** é contado automaticamente por sessão (um acesso por sessão de navegador). Veja na lista de artigos.
