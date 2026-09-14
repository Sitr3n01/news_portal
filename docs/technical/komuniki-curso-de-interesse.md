# Curso de interesse no contato

Implementado em 14/09/2026 na worktree `news_portal-komuniki-design`, branch `codex/komuniki-editorial-test`, a pedido do usuário. Quem clica num card de curso em Cursos chega a Contato com o curso já indicado, e a mensagem enviada guarda esse curso.

## Comportamento

- Cada card de curso em Cursos leva a `/contact/?curso=<slug>`.
- Em Contato, acima dos campos, aparece "Curso de interesse" com uma etiqueta com o nome do curso. O assunto já vem em "Cursos e inscrições".
- "Remover" tira a etiqueta sem recarregar a página e sem apagar o que já foi digitado; a mensagem então segue sem curso. Sem JavaScript, o link abre Contato sem o curso.
- Ao enviar, a mensagem grava o título do curso no campo "Curso de interesse". Quem abre Contato por outro caminho não vê a etiqueta, e o campo fica vazio.
- Um `?curso=` que não está no catálogo é ignorado: sem etiqueta e sem curso gravado. O valor da URL nunca é exibido.
- Se o envio falhar, por exemplo na verificação anti-bot, a página volta com a etiqueta, a menos que ela tenha sido removida.

## Slugs

| Curso | Slug |
|---|---|
| Comunicador Profissionalizante | `comunicador-profissionalizante` |
| Produção Cultural | `producao-cultural` |
| Jornalismo Cultural | `jornalismo-cultural` |
| Apresentação de Palco e Eventos | `apresentacao-de-palco-e-eventos` |
| Espanhol – Conversação e Escrita | `espanhol-conversacao-e-escrita` |
| Comunicação Destravada | `comunicacao-destravada` |

Os slugs são fixos, para que links já compartilhados continuem funcionando: mudar o título de um curso não muda o slug. Um curso novo precisa de um slug novo em `apps/school/courses.py`.

## No admin

Em Mensagens de Contato, a lista ganhou a coluna "Curso de interesse", com filtro e busca por curso. O detalhe mostra o campo, somente leitura, logo abaixo do assunto.

## Como funciona

- `apps/school/courses.py` guarda o catálogo `COURSE_GROUPS`, que antes ficava em `apps/school/views.py`, e a função `find_course(slug)`.
- A view de Contato lê `?curso=`, busca o curso e passa `selected_course` ao template. O formulário recebe como valores iniciais o slug no campo oculto `course_interest` e o assunto `admissions`.
- `ContactInquiryForm.clean_course_interest` troca o slug pelo título do curso, ou por vazio quando o slug não está no catálogo. É o título que fica gravado.
- `ContactInquiry.course_interest` é um `CharField` opcional de 120 caracteres. A migração `contact.0005_contactinquiry_course_interest` só adiciona a coluna, vazia nas mensagens antigas.

## Arquivos

| Arquivo | Papel |
|---|---|
| `apps/school/courses.py` | Catálogo com slugs e `find_course` |
| `apps/school/views.py` | Importa o catálogo |
| `templates/school/page_detail.html` | Link do card com `?curso=<slug>` |
| `apps/contact/models.py`, `apps/contact/migrations/0005_contactinquiry_course_interest.py` | Campo `course_interest` |
| `apps/contact/forms.py` | Campo oculto e troca do slug pelo título |
| `apps/contact/views.py` | Leitura de `?curso=` e valores iniciais |
| `apps/contact/admin.py` | Coluna, filtro, busca e campo no detalhe |
| `templates/contact/contact_page.html` | Etiqueta, campo oculto e "Remover" |
| `apps/contact/tests.py`, `apps/school/tests.py` | Etiqueta, curso fora do catálogo, gravação e links dos cards |

## Implantação

A migração `contact.0005` precisa ser aplicada no banco antes de a versão nova receber mensagens; sem ela, o envio do formulário falha. Na worktree, a prévia 8013 usa `.preview/local.sqlite3`. As prévias 8011 e 8012 usam `current.sqlite3` e `demo.sqlite3` e precisam de `migrate` quando forem religadas.

## Como testar

1. Em Cursos, clique no card de Jornalismo Cultural: Contato abre com "Curso de interesse" e a etiqueta "Jornalismo Cultural", e o assunto está em "Cursos e inscrições".
2. Digite algo na mensagem e clique em "Remover": a etiqueta some e o texto continua.
3. Abra `/contact/?curso=qualquer-coisa`: nenhuma etiqueta.
4. Envie uma mensagem vinda de um card e confira a coluna "Curso de interesse" no admin.

## Validação

Feita em 14/09/2026. O roteiro, os resultados e as capturas estão em `.preview/evidence/curso-de-interesse-2026-09-14/`, fora do Git.

| Critério | Resultado |
|---|---|
| Links dos cards | Os seis cards de Cursos levam a `/contact/?curso=<slug>`, cada um com o seu slug |
| Clique no card | Um clique real no card de Jornalismo Cultural abre Contato com a etiqueta, o slug no campo oculto e o assunto "Cursos e inscrições" |
| Remover | A etiqueta some sem recarregar, o campo oculto fica vazio e a mensagem digitada continua |
| Slug fora do catálogo | Sem etiqueta, sem campo oculto, assunto padrão e nenhum pedaço da URL na página |
| Contato sem curso | Igual ao anterior: sem etiqueta e com o assunto "Geral" |
| Idioma | Em inglês, "Course of interest", "Remove" e o aria-label traduzidos. Desde 14/09/2026 a etiqueta também mostra o nome do curso em inglês; a mensagem continua gravando o nome em português |
| 375 px | Etiqueta de "Apresentação de Palco e Eventos" sem rolagem horizontal |
| Gravação e admin | Nos testes do Django, a mensagem enviada a partir de um card grava "Jornalismo Cultural", um slug inventado grava vazio, e o admin lista e filtra o curso |
| Migrações e testes | `makemigrations --check` sem mudanças pendentes; 482 testes do pytest e o Ruff passaram |
| Prévia | Migração aplicada em `.preview/local.sqlite3`, com cópia anterior em `.preview/backups/local-antes-curso-de-interesse-2026-09-14.sqlite3` |

O formulário não foi enviado no navegador, para não gravar mensagens de teste no banco da prévia.

## Reversão

- **Só o link:** tirar `?curso={{ course.slug }}` do link dos cards em `page_detail.html`; o card volta a abrir Contato sem curso.
- **A lógica, sem perder dados:** remover a etiqueta do template, o campo `course_interest` do formulário e a leitura de `?curso=` na view. A coluna pode ficar no banco.
- **A coluna:** remover o campo do modelo e do admin e gerar a migração de remoção, que apaga os cursos já gravados.
