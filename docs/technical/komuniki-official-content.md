# Conteúdo oficial da Komuniki na revisão local

**Revisão visual de 13/09/2026:** o conteúdo documentado aqui foi preservado na [versão estática com destaque azul](komuniki-static-blue.md), que remove todo movimento. Para reverter somente a apresentação, siga esse documento, sem restaurar o banco anterior ao conteúdo oficial. A validação visual abaixo descreve a aplicação original dos dados.

Conteúdo público consultado em **12/09/2026**, no navegador, em [Home](https://komuniki.com.br/), [Sobre](https://komuniki.com.br/sobre/), [Cursos](https://komuniki.com.br/cursos/), [Contato](https://komuniki.com.br/contact/) e [Privacidade](https://komuniki.com.br/privacidade/). O HTTPS abriu normalmente nesta consulta; a pendência anterior de acesso ao site público foi resolvida. Não houve acesso ao banco ou à administração de produção.

A versão principal está em **http://127.0.0.1:8012/**. A referência anterior permanece em **http://127.0.0.1:8011/**. Esta entrega é local, sem push, merge ou publicação.

## O que mudou

| Área | Resultado |
|---|---|
| Contato e rodapé | `komunikicomunicacao@gmail.com`, `(61) 92003-8428`, `QI 11 Bloco A Comércio Local salas 102/104 Guará 1`, seguido de `Brasília DF, 70274-530, BR` na próxima linha. |
| Configuração administrável | Tagline `Comunicação que gera resultados`; Instagram e YouTube oficiais; URL fictícia de Facebook removida. Notícias já apontava para `https://kellyfarias.com.br/news/`. |
| Home | Três diferenciais: Mentorias com Kelly Farias; Cursos online, híbridos e presenciais; Atuação corporativa. O registro do cartão Jovem Comunicador foi desativado, sem exclusão. |
| Sobre | Menção institucional ao Jovem Comunicador preservada, conforme a correção do usuário. |
| Seção social | Desativada para corresponder à Home pública. O título de teste voltou ao padrão existente do modelo, sem exibição. Não foram inventados depoimentos ou posts. |
| Conteúdo preservado | Seis cursos e seus dados, biografia, textos institucionais e de privacidade, títulos, descrições SEO, expressões PT/EN e fallbacks para português. |
| Apresentação | Nenhuma alteração nos templates, CSS, JavaScript da aplicação, fontes, foto da Kelly ou ilustração 3D. |

A ausência pública da seção social orienta a apresentação local; ela não permite inferir os valores de configurações ocultas em produção. O manifesto diferencia valores publicados, limpeza de exemplos e decisões de apresentação. O escopo é o conteúdo público das cinco páginas, não registros privados, páginas não vinculadas ou dados internos do cliente.

## Aplicação reproduzível

O [manifesto](../../scripts/preview/komuniki-public-content.json) versiona os valores, a origem e a data de consulta. O [aplicador](../../scripts/preview/apply_public_content.py) usa uma lista fixa de campos, confere o Site e os valores anteriores esperados e aceita somente `.preview/local.sqlite3` na worktree experimental. Conteúdo editado manualmente que divirja do manifesto interrompe a operação antes das gravações.

```powershell
Set-Location 'C:\Users\Sitr3n\Documents\Github\news_portal-komuniki-design'

# Simular; abre o banco em modo somente leitura e não cria arquivos.
& '..\news_portal\.venv\Scripts\python.exe' -B scripts/preview/apply_public_content.py

# Aplicar somente após preparar a cópia local, com a prévia encerrada.
.\scripts\preview\preview.ps1 -Action stop
& '..\news_portal\.venv\Scripts\python.exe' -B scripts/preview/apply_public_content.py --apply
.\scripts\preview\preview.ps1 -Action start
```

A aplicação criou backup SQLite íntegro antes das dez alterações, dentro de uma transação que impede escritores concorrentes. Uma falha reverte a transação. Reexecutar depois do sucesso não altera o banco nem cria outro backup. Não há migração, mudança de API, sincronização automática ou alteração de credenciais. O comando é exclusivo da prévia; não deve ser adaptado para execução em produção sem revisão própria.

## Validação

- **107 testes passaram:** 101 de escola, contato, redes sociais, componentes comuns e vagas, mais seis testes do aplicador: simulação sem gravação, backup/idempotência, conflito com edição existente, rollback em falha, rejeição do checkout original e rejeição de campos não permitidos.
- **80 verificações de página passaram:** cinco páginas × 375×812, 768×1024, 1024×768 e 1440×900 × claro/escuro × PT/EN. Mais 16 verificações de menu móvel, Escape e retorno de foco.
- Navegação complementar pelos links Home → Sobre → Cursos → Contato e menu móvel → Home; endereço e e-mail sem cortes nos cartões e rodapé. Imagens carregadas e animação da ilustração ativa.
- Paridade com o DOM público: nenhum texto, expressão de tradução, destino ou imagem de referência faltante nas cinco páginas; títulos e descrições SEO equivalentes; seis cursos e contrato dos campos do formulário preservados. O comparador normaliza espaços e caixa visual e conserva a ordem na apresentação dos dados de contato.
- Os hashes dos **50 arquivos protegidos** permaneceram iguais: banco original, bancos current/demo, imagens estáticas e 44 arquivos de mídia local. A comparação integral das tabelas entre backup e banco aplicado encontrou somente os dez campos previstos; esquema e quantidades de registros idênticos, integridade SQLite `ok`.
- Ruff passou; Django sem erros, com os dois avisos preexistentes do treebeard. Os testes mantêm os avisos conhecidos de URLField/Django 6 e diretório de estáticos da configuração de testes.

O primeiro caso visual detectou um erro no roteiro antigo: comparar `pt` com o atributo HTML correto `pt-BR` fazia o próprio teste alternar o idioma indevidamente. `browser_e2e.mjs` agora normaliza o idioma para selecionar a preferência, e `motion_e2e.mjs` exige `pt-BR` quando solicitado português. A matriz completa acima foi executada novamente com a correção. Os relatórios antigos de 152 combinações são históricos e não substituem esta execução. A tentativa inicial falha permanece em `matrix.jsonl`, separada do resultado corrigido.

Cobertura no Chromium local, em pixels CSS, sem alegar aparelhos físicos ou outros motores. O envio bem-sucedido pelo Turnstile externo não foi repetido; os testes de backend passaram e o formulário não foi modificado. Não foram enviados formulários ao site publicado.

Evidências em `.preview/evidence/official-content/` (fora do Git): [paridade](../../.preview/evidence/official-content/parity.json), [isolamento](../../.preview/evidence/official-content/isolation.json), [resumo da matriz](../../.preview/evidence/official-content/summary.json), [contato móvel claro](../../.preview/evidence/official-content/contact-mobile-light.png), [contato móvel escuro](../../.preview/evidence/official-content/contact-mobile-dark.png), [contato desktop](../../.preview/evidence/official-content/contact-desktop-light.png) e [Home](../../.preview/evidence/official-content/home-desktop-dark.png). `published-pages.json` guarda a captura pública usada na comparação; uma nova consulta requer nova captura datada, especialmente por causa do aviso dinâmico de atualização da privacidade.

## Reverter esta rodada

Checkpoint anterior: `f295ed5`. A tag local `codex/komuniki-official-content` identifica o commit desta rodada. Como o banco é ignorado pelo Git, **reverter o commit não restaura os dados**.

Backup criado nesta aplicação:

`.preview/backups/before-official-content-20260913T012739001637Z/local.sqlite3`

O carimbo do diretório usa UTC (13/09); a consulta e a aplicação ocorreram em 12/09 no fuso de São Paulo. `changes.json`, ao lado do backup, registra os valores anteriores e posteriores.

Para voltar ao conteúdo anterior, mantendo uma cópia dos dados que existirem no momento da restauração:

```powershell
Set-Location 'C:\Users\Sitr3n\Documents\Github\news_portal-komuniki-design'
.\scripts\preview\preview.ps1 -Action stop
$restoreSource = (Resolve-Path '.preview\backups\before-official-content-20260913T012739001637Z\local.sqlite3').Path
$restoreTarget = (Resolve-Path '.preview\local.sqlite3').Path
$restorePreserved = Join-Path (Split-Path $restoreSource) ('local-before-restore-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '.sqlite3')
Copy-Item -LiteralPath $restoreTarget -Destination $restorePreserved
Copy-Item -LiteralPath $restoreSource -Destination $restoreTarget -Force
.\scripts\preview\preview.ps1 -Action start

# Opcional: reverter também os scripts/documentação desta rodada,
# após preservar eventuais alterações posteriores no Git.
git revert --no-edit codex/komuniki-official-content
```

Nenhuma mídia precisa ser restaurada. Para reaplicar os dados oficiais, mantenha ou restaure os scripts desta rodada e execute novamente o aplicador com `--apply`.
