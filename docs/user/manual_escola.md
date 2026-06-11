# Manual do Portal Escolar — Komuniki

Este manual cobre todas as operações que um **Administrador Komuniki** precisa realizar no dia a dia. Não é necessário nenhum conhecimento técnico.

---

## 1. Textos da Página Inicial (Home da Escola)

A home da Komuniki é configurada por um registro único chamado **"Configuração da Home Escolar"** (`Home Komuniki` na barra lateral).

### Como editar

1. Na barra lateral, clique em **Komuniki → Home Komuniki**.
2. Clique no único registro existente para abrir o formulário.
3. Edite os campos desejados e clique em **Salvar**.

### Campos disponíveis

Cada seção da home tem um bloco de campos correspondente. Os campos terminados em **(EN)** são opcionais — se vazios, o sistema usa o texto em português.

| Seção na home | Campos no admin |
|--------------|----------------|
| Topo (hero) | `Selo do hero`, `Título do hero`, `Subtítulo do hero` |
| Bloco visual | `Chamada visual`, `Título do bloco visual`, `Título do bloco de comunidade`, `Texto do bloco de comunidade` |
| Proposta pedagógica | `Chamada da proposta`, `Título da proposta`, `Descrição da proposta` |
| Vida escolar | `Chamada de vida escolar`, `Título de vida escolar`, `Descrição de vida escolar` |
| Equipe | `Chamada da equipe`, `Título da equipe`, `Descrição da equipe` |
| Depoimentos | `Chamada de depoimentos`, `Título de depoimentos`, `Descrição de depoimentos` |
| Trabalhe conosco | `Título de trabalhe conosco`, `Descrição de trabalhe conosco` |
| Contato | `Título de contato`, `Descrição de contato` |
| SEO | `Título SEO`, `Descrição SEO`, `Palavras-chave SEO` |

> **Nota:** Se não existir nenhum registro de configuração no banco, a home exibe textos padrão definidos no código. Criar um registro no admin sobrescreve esses textos.

---

## 2. Blocos de Diferenciais (Cards da Home)

Os "blocos de diferenciais" aparecem em três seções da home:

- **Barra de confiança** — cards curtos no topo
- **Proposta pedagógica** — cards explicativos do método
- **Vida escolar** — cards de experiências cotidianas

### Como adicionar um diferencial

1. Na barra lateral, clique em **Komuniki → Blocos da Home**.
2. Clique em **Adicionar Bloco da Home**.
3. Preencha:
   - **Local de exibição**: escolha entre `Barra de confiança`, `Proposta pedagógica` ou `Vida escolar`
   - **Título** (obrigatório) e **Título (EN)** (opcional)
   - **Descrição** (obrigatório) e **Descrição (EN)** (opcional)
   - **Tom visual**: `Verde institucional`, `Âmbar`, `Slate` ou `Branco` — controla a cor do card
   - **Ativo**: marque para exibir; desmarque para ocultar sem excluir
   - **Ordem**: número inteiro; blocos são exibidos em ordem crescente
4. Clique em **Salvar**.

> Se não houver nenhum bloco ativo para uma seção, a home exibe um conjunto padrão do código.

---

## 3. Páginas Institucionais

Use páginas para conteúdo longo e estático, como "Sobre Nós", "Regimento Escolar", "Infraestrutura".

### Como criar uma página

1. Na barra lateral, clique em **Komuniki → Página Cursos**.
2. Clique em **Adicionar Página**.
3. Preencha:
   - **Título** — nome visível no site
   - **URL amigável (slug)** — parte final do endereço (ex.: `sobre-nos` → `komuniki.com.br/sobre-nos/`). Use apenas letras minúsculas, números e hífens.
   - **Conteúdo** — editor de texto rico. Aceita negrito, itálico, listas, links e títulos (`h2`–`h6`).
   - **Imagem destacada** — imagem opcional exibida no topo da página
   - **Publicado** — marque para que a página apareça no site
   - **Ordem** — número inteiro; páginas são ordenadas por este valor
   - **Título SEO**, **Descrição SEO**, **Palavras-chave SEO** — como a página aparece no Google
4. Clique em **Salvar**.

> O slug deve ser único. Dois títulos diferentes não podem ter o mesmo slug.

---

## 4. Equipe e Depoimentos

### Membros da equipe

1. Na barra lateral (em **Recursos guardados**), clique em **Equipe**.
2. Clique em **Adicionar Membro da Equipe**.
3. Preencha **Nome**, **Cargo ou função**, **Foto** (opcional), **Biografia** (opcional), **E-mail** (opcional), **Ativo** e **Ordem**.
4. Salve.

> Os membros da equipe aparecem na página de equipe da escola, ordenados pelo campo **Ordem**.

### Depoimentos

1. Na barra lateral (em **Recursos guardados**), clique em **Depoimentos**.
2. Clique em **Adicionar Depoimento**.
3. Preencha **Nome**, **Relação com a escola** (ex.: "Mãe de aluno"), **Depoimento**, **Foto** (opcional) e **Destacado**.
4. Marque **Destacado** para que o depoimento apareça na home. Somente os 3 primeiros destaques são exibidos.
5. Salve.

---

## 5. Redes Sociais

### 5.1 Configurar links públicos

1. Na barra lateral, clique em **Sistema → Configurações do Site**.
2. Clique no registro do site.
3. Preencha `Facebook`, `Instagram`, `TikTok` e `YouTube` com URLs completas.
4. Em **Seção de redes na home — textos**, ajuste título e subtítulo da área de redes.
5. Salve.

### 5.2 Ligar/desligar a seção da home

1. Na barra lateral, clique em **Komuniki → Posts de Redes Sociais**.
2. No topo da lista, use os interruptores:
   - **Exibir seção de redes na home**
   - **Exibir Instagram**
   - **Exibir TikTok**
3. Clique em **Salvar exibição**.

### 5.3 Cadastrar uma conta de rede social

1. Clique em **Komuniki → Contas de Redes Sociais**.
2. Clique em **Adicionar Conta de Rede Social**.
3. Escolha `Instagram` ou `TikTok`.
4. Preencha nome de exibição, usuário público e link do perfil.
5. Marque **Ativa**.
6. Salve.

Os campos de credenciais são opcionais e só são necessários para sincronização automática via APIs oficiais.

### 5.4 Adicionar posts manualmente

1. Clique em **Komuniki → Posts de Redes Sociais**.
2. Clique em **Adicionar Post de Rede Social**.
3. Escolha a conta, cole o link público do post, preencha legenda, tipo de mídia, data de publicação e miniatura.
4. Mantenha **Visível no site** marcado.
5. Salve.

> Posts manuais aparecem mesmo sem credenciais de API. A sincronização automática é complementar.

---

## 6. Mensagens de Contato

Visitantes podem enviar mensagens via o formulário de contato da escola.

1. Na barra lateral, clique em **Komuniki → Mensagens**.
2. A lista mostra todas as mensagens recebidas, com nome, e-mail, assunto e status.
3. Clique em uma mensagem para ler e atualizar o status:
   - **Nova** → ainda não foi vista
   - **Lida** → você abriu e leu
   - **Respondida** → você respondeu ao remetente (fora do sistema, por e-mail)
   - **Arquivada** → encerrada
4. Salve após alterar o status.

> O sistema não envia respostas automáticas — o atendimento é feito externamente (por e-mail, telefone etc.).

---

## 7. Configurações Gerais do Site

1. Na barra lateral, clique em **Sistema → Configurações do Site**.
2. Clique no registro existente.
3. Campos disponíveis:

| Campo | Para que serve |
|-------|----------------|
| Tagline | Slogan exibido no rodapé |
| Logo | Logotipo do site |
| Favicon | Ícone na aba do navegador |
| E-mail principal | E-mail de contato exibido no rodapé |
| Telefone | Telefone exibido no rodapé |
| Endereço | Endereço físico |
| E-mail remetente da Newsletter | De qual e-mail as newsletters saem |
| Nome remetente da Newsletter | Nome exibido como remetente (ex.: "Blog da Kelly") |
| Google Analytics | Código GA4 (ex.: `G-XXXXXXXX`) |
| Redes sociais | Links públicos e textos da seção de redes |

4. Salve.

---

## 8. Vagas de Emprego

O módulo de vagas está em **Recursos guardados** na barra lateral (visível apenas para Super Administradores).

### Criar um departamento

1. Clique em **Departamentos → Adicionar**.
2. Preencha **Nome** e **URL amigável**.
3. Salve.

### Criar uma vaga

1. Clique em **Vagas → Adicionar**.
2. Preencha:
   - **Departamento** — o departamento ao qual a vaga pertence
   - **Título** e **URL amigável**
   - **Descrição** e **Requisitos**
   - **Tipo de contratação**: Tempo integral, Meio período, Contrato ou Estágio
   - **Local** e **Faixa salarial** (ambos opcionais)
   - **Status**: `Rascunho` (não visível), `Aberta` (aparece no site), `Fechada` (removida do site)
   - **Prazo final** (opcional)
3. Salve.

### Ver candidaturas

1. Clique em **Candidaturas**.
2. A lista mostra todos os candidatos com nome, vaga e status.
3. Atualize o status conforme o processo avança: `Recebida → Em Análise → Pré-selecionada → Entrevista → Aceita / Rejeitada`.
4. Você pode adicionar **notas internas** (não visíveis ao candidato).

> Currículos enviados pelos candidatos ficam protegidos e só podem ser baixados por administradores autenticados.
