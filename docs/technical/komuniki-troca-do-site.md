# Troca do site da Komuniki

Feita em 14/09/2026 na worktree `news_portal-komuniki-design`, branch `codex/komuniki-editorial-test`, a pedido do usuário. O site editorial virou o site da escola, o site antigo saiu do projeto e o backend passou a alimentar o front novo nos pontos que ainda estavam fixos no código. Depois do commit, o `master` local avançou até a branch por fast-forward. Não houve push nem publicação.

## Decisões do usuário

- **Troca no `master` local, sem push.** A integração foi testada na branch, e o `master` avançou por fast-forward.
- **Vagas fora do site.** Lista, detalhe e formulário de candidatura saíram. Modelos, dados e admin ficam, e o download protegido de currículos continua.
- **Prévia mantida para desenvolvimento.** `config/settings/design_preview.py`, `scripts/preview/` e `apps/school/preview_context.py` continuam. Saiu só o site antigo.
- **Só dados reais no banco.** A migração `school.0010` troca os valores de exemplo que migrações antigas gravaram (veja [Dados reais](#dados-reais)).

## O que saiu

| Arquivo | Papel no site antigo |
|---|---|
| `templates/base_school.html` | Base visual do site antigo. Na última versão, só as páginas de vagas ainda a usavam |
| `templates/components/navbar_school.html`, `footer_school.html` | Navbar e rodapé dessa base |
| `templates/base.html`, `templates/components/navbar.html`, `footer.html` | Base genérica, sem nenhum uso |
| `templates/hiring/job_list.html`, `job_detail.html` | Lista e detalhe de vagas |
| `apps/hiring/forms.py` | `ApplicationForm`, com a validação do currículo |
| `templates/school/team_list.html` | Página de equipe. `/team/` já redirecionava para o Blog |

`apps/hiring/views.py` e `apps/hiring/urls.py` ficaram só com `download_resume`. `/hiring/` e `/hiring/<slug>/` respondem 404.

## Backend ligado ao front novo

- **Título da Home:** com o **Título SEO** da Home Komuniki preenchido, a aba do navegador mostra esse título. Vazio, mostra o nome do site e o título do hero, como antes.
- **Rodapé:** os ícones de Instagram e YouTube usam os links de Configurações do Site. Vazios, apontam para `https://www.instagram.com/komunikiescola/` e `https://youtube.com/@escolakomuniki?si=8AR-FzPrJh8QCbu3`, os endereços que estavam fixos no código.
- **Admin da Home Komuniki:** o formulário segue a ordem da Home editorial, e os rótulos dizem onde cada texto aparece. Os campos `hiring_*`, que alimentam o painel final de cursos, aparecem como "Título da chamada de cursos" e "Texto da chamada de cursos". Os campos que a Home não mostra (`visual_footer_*`, `proposal_title`, `life_*` e `team_*`) ficam numa seção recolhida, só para superusuários. Os rótulos vêm do formulário do admin, sem migração.
- **Blocos da Home:** a equipe só escolhe a barra de confiança, a única posição que a Home exibe. O guia do admin e o dashboard contam só esses blocos.
- **Equipe e vagas no admin:** os textos dizem que nada disso aparece no site. A aba SEO das vagas saiu, e o texto de ajuda do status mudou na migração `hiring.0008`, que não altera o banco além do registro da migração.
- **Scripts da prévia:** `verify_content.py` e `export_school_content.py` não citam mais `base_school.html`.

## Dados reais

O rodapé antigo tinha Instagram e YouTube fixos no código e ignorava o banco, então valores errados nesses campos nunca apareceram. Com o rodapé ligado a Configurações do Site, eles apareceriam. A migração `school.0010_komuniki_real_public_data` troca pelos dados reais, publicados no site em 12/09/2026, os valores de exemplo que migrações antigas gravaram:

| Campo | Valores trocados | Valor real |
|---|---|---|
| Tagline | `Moldando o futuro, inspirando mentes.` | `Comunicação que gera resultados` |
| E-mail | `contato@exemplo.edu.br` | `komunikicomunicacao@gmail.com` |
| Telefone | `(11) 99999-9999` | `(61) 92003-8428` |
| Endereço | `Rua da Educação, 123, São Paulo - SP` | `QI 11 Bloco A Comércio Local salas 102/104 Guará 1`, com `Brasília DF, 70274-530, BR` na linha seguinte |
| Facebook | `https://facebook.com/exemplo` | vazio |
| Instagram | `https://instagram.com/exemplo` e `https://www.instagram.com/komunikiagencia/` | `https://www.instagram.com/komunikiescola/` |
| YouTube | `https://youtube.com/exemplo` e o canal por ID de `school.0007` | `https://youtube.com/@escolakomuniki?si=8AR-FzPrJh8QCbu3` |
| Nome do site | `Escola e Portal de Notícias` | `Komuniki` |
| Seção social | Título `TESTE FASE 11 — Redes Sociais Kelly` | Título `Acompanhe a Komuniki nas redes`, com a seção desligada |
| Cartão da Home | `Projeto Jovem Comunicador` ativo | Desativado, sem exclusão |

- Um campo só muda quando ainda guarda exatamente um desses valores. O que foi editado no admin fica como está, e rodar de novo não muda nada.
- Ficam de fora o domínio do site, definido no deploy com `set_site_domain`, o remetente da newsletter e o Facebook `https://www.facebook.com/Komunikicomunicacao/` de `school.0007`, que o site não exibe.
- A migração não tem volta: desfazê-la só a marca como não aplicada, sem restaurar os exemplos.
- Todo banco que rodar `migrate` recebe os dados reais, inclusive `current.sqlite3` e `demo.sqlite3` da prévia.

## Implantação

1. **Backup do banco**, como o `kellysys-deploy` já faz antes de alterar os containers.
2. **`migrate`.** Aplica `contact.0005`, do curso de interesse, necessária antes de o site receber mensagens, `hiring.0008`, `school.0010`, que troca os valores de exemplo pelos [dados reais](#dados-reais), e `common.0010`, que cria o slogan em inglês (veja [Transição e rolagem](komuniki-transicao-e-rolagem.md)).
3. **Configurações do Site.** Depois do `migrate`, confira se contatos, Instagram e YouTube são os da escola. Um valor editado no admin não é trocado, mesmo que esteja errado.
4. **Conteúdo exibido pela Home editorial.** Os textos vêm dos mesmos modelos, mas a Home nova mostra campos que a antiga não usava, como o bloco Komuniki. O conteúdo oficial da revisão foi aplicado só em `.preview/local.sqlite3`. Em produção, confira no admin a Home Komuniki, os blocos ativos da barra de confiança e a página Cursos publicada. `scripts/preview/export_school_content.py` exporta esses dados em modo somente leitura para a comparação.
5. **Smoke test:** Home, Sobre, Cursos, Contato e Privacidade carregam, `/contact/?curso=jornalismo-cultural` mostra a etiqueta e `/hiring/` responde 404. Os itens estão no [checklist de go-live](go-live-checklist.md).

## Validação

| Critério | Resultado |
|---|---|
| Referências ao site antigo | Nenhuma no código a `base_school.html`, `navbar_school`, `footer_school`, `team_list.html`, `ApplicationForm`, `hiring:list` ou `hiring:job_detail` |
| Testes | 486 do pytest passaram, incluindo os novos: vagas fora do site, links sociais do rodapé com e sem configuração, Título SEO da Home, rótulos e campos do admin da Home, escolha só da barra de confiança e a migração de dados reais, que troca os valores semeados, preserva o que foi editado, pode rodar de novo e deixa um banco novo com os perfis da escola |
| Lint e migrações | Ruff passou, `makemigrations --check` ficou sem pendências e o `check` mostrou só os dois avisos antigos do treebeard |
| Prévia 8013 | As cinco páginas respondem 200 com a base editorial. Contato mostra a etiqueta do curso, `/hiring/` e `/hiring/professor/` respondem 404, `/team/` redireciona, nenhuma página tem link para vagas ou equipe e todos os estáticos respondem 200 |
| Banco da prévia | `hiring.0008` aplicada em `.preview/local.sqlite3`, com cópia anterior em `.preview/backups/local-antes-troca-do-site-2026-09-14.sqlite3` |

O teste social do botão de Instagram passou a olhar só a seção de redes, porque o rodapé agora também usa o `instagram_url` do site.

## Reversão

- **Voltar o `master` local ao site antigo:** com o código atual, desfaça antes as migrações novas. `migrate contact 0004` apaga os cursos de interesse gravados; `migrate hiring 0007` só troca o texto de ajuda. Depois, `git switch master` e `git reset --keep 4e0fc78`. A branch `codex/komuniki-editorial-test` continua com todos os commits.
- **Só esta troca, mantendo as rodadas anteriores:** `migrate hiring 0007` e `git revert` do commit da troca, que devolve o site antigo, as vagas e os textos anteriores do admin.
- **Só as vagas:** recupere `apps/hiring/forms.py`, as views, as rotas e os templates do commit `02027f0`, e refaça os templates sobre `base_school_editorial.html`.
- **Só os links do rodapé:** volte os `href` de `templates/school/editorial/footer.html` para os endereços fixos.
- **Dados reais:** a migração não restaura os exemplos. Os valores anteriores estão nos backups dos bancos feitos antes do `migrate`.
