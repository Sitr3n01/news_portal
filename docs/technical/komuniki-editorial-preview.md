# Experimento editorial da Escola Komuniki

Implementado e validado localmente em 08/09/2026. Em 09/09/2026, após a aprovação do design e do hover, a versão principal recebeu o conteúdo do projeto antigo local por solicitação do usuário. Não houve publicação, push, migração de banco ou alteração de API.

## Abrir a revisão

**Apresentação atual — 13/09/2026:** todo movimento foi removido, inclusive hover, e os destaques amarelos passaram para o azul oficial `#0b3a75`. Os dados oficiais foram preservados. Consulte [Apresentação estática e rollback](komuniki-static-blue.md) para a validação e o checkpoint atual.

**Atualização de 12/09/2026:** o conteúdo das cinco páginas públicas oficiais foi conferido no navegador e aplicado à porta 8012. Contatos reais, três diferenciais e retirada da seção social de teste estão documentados em [Conteúdo oficial e rollback](komuniki-official-content.md). Os relatos de dados de exemplo e bloqueio de certificado abaixo são históricos. O design segue aprovado; esta entrega permanece local, sem publicação.

| Versão | Endereço | Dados |
|---|---|---|
| Referência local redesenhada | http://127.0.0.1:8011/ | Cópia anterior do banco local, preservada |
| Versão principal com conteúdo oficial | http://127.0.0.1:8012/ | Cópia independente atualizada com o conteúdo público consultado em 12/09/2026; sem seção social de teste ou cartão Jovem Comunicador na Home |

As cinco rotas são `/`, `/sobre/`, `/cursos/`, `/contact/` e `/privacidade/`, disponíveis nas duas portas. Os links de Notícias, Instagram e YouTube conservam os destinos existentes no projeto local. A demonstração sintética e seu CMS com título longo ficam arquivados; podem ser reabertos com `-ReviewSource demo`, conforme abaixo.

Abra a [galeria comparativa histórica](../../.preview/evidence/comparison.html) para ver antes/depois das cinco páginas, Home móvel, tema escuro e os antigos estados demonstrativos. Essas capturas precedem a troca para conteúdo local. O servidor temporário com os templates antigos foi usado somente para capturá-las e foi encerrado.

## Isolamento e execução

- Worktree: `C:\Users\Sitr3n\Documents\Github\news_portal-komuniki-design`.
- Branch: `codex/komuniki-editorial-test`, criada a partir de `4e0fc78`.
- Projeto original: `C:\Users\Sitr3n\Documents\Github\news_portal`, preservado.
- Bancos independentes: `.preview/current.sqlite3`, `.preview/local.sqlite3` (principal) e `.preview/demo.sqlite3` (demonstração arquivada), criados com o backup do SQLite, abrindo a origem somente para leitura.
- Mídia independente: `.preview/current-media/`, `.preview/local-media/` e `.preview/demo-media/`.
- Configuração explícita: `config.settings.design_preview`; nenhuma cópia do `.env` original. Chave Django exclusivamente de teste, cache e e-mail em memória, OAuth desativado, chaves oficiais de teste do Turnstile.
- Cookies de sessão e CSRF separados por cenário. Tema e idioma persistem no armazenamento local de cada origem/porta.
- Servidores vinculados somente a `127.0.0.1`. Dados, logs, processos registrados, evidências e arquivos coletados ficam em `.preview/`, ignorada pelo Git.
- O interpretador e as dependências já instaladas no `.venv` do projeto irmão são reutilizados sem alteração. Código, configuração, SQLite e mídia executados pertencem à worktree experimental.

No PowerShell:

```powershell
Set-Location 'C:\Users\Sitr3n\Documents\Github\news_portal-komuniki-design'

# Apenas na preparação inicial; execuções seguintes preservam as cópias existentes.
.\scripts\preview\preview.ps1 -Action prepare

# Importação inicial do conteúdo local; já executada neste experimento.
# Cria local.sqlite3/local-media e uma cópia de segurança da demonstração.
.\scripts\preview\preview.ps1 -Action import-local

# Iniciar ambas as versões; 8012 usa o conteúdo local após a importação.
.\scripts\preview\preview.ps1 -Action start

# Consultar as URLs e os processos registrados.
.\scripts\preview\preview.ps1 -Action status

# Encerrar somente os processos registrados deste experimento.
.\scripts\preview\preview.ps1 -Action stop
```

O parâmetro opcional `-Python 'C:\caminho\python.exe'` permite usar outro ambiente compatível com as dependências do projeto. Não é necessário ativar o `.venv`.

O início recusa portas já ocupadas. O encerramento verifica PID, horário de criação e linha de comando antes de parar os processos, inclusive o interpretador filho criado pelo launcher do venv no Windows. Logs atuais: `.preview/current.stderr.log` e `.preview/local.stderr.log`.

Os servidores usam `--noreload`. Depois de editar templates, Python ou configurações, execute `stop` e `start`. Para CSS/JS alterados, recarregue sem cache no navegador. A preparação não substitui bancos ou mídia já existentes.

Para rever os antigos cenários fictícios sem alterar os dados importados:

```powershell
.\scripts\preview\preview.ps1 -Action stop
.\scripts\preview\preview.ps1 -Action start -ReviewSource demo
# A porta 8012 volta temporariamente à demonstração, incluindo /demonstracao-editorial/.

# Retornar ao conteúdo local:
.\scripts\preview\preview.ps1 -Action stop
.\scripts\preview\preview.ps1 -Action start -ReviewSource local
```

## Conteúdo local aplicado — 09/09/2026

Registro histórico da importação inicial. Os contatos e a apresentação da Home na porta 8012 foram atualizados posteriormente, conforme [Conteúdo oficial](komuniki-official-content.md).

A fonte autorizada é `news_portal/db.sqlite3` e a pasta `news_portal/media`, junto dos templates e conteúdos definidos no código do projeto antigo. A importação leu a origem sem alterá-la e criou `.preview/local.sqlite3` e `.preview/local-media`. O design, o hero 3D, a foto da Kelly, as fontes e as animações aprovadas foram mantidos.

O banco importado preserva a configuração do site e da Home, a página do CMS, os 14 registros de diferenciais (respeitando as condições de exibição existentes) e o registro de equipe. Os seis cursos, seus dados e textos institucionais definidos nas views/templates permanecem idênticos. Todos os **44 arquivos de mídia** conferem por SHA-256 com a origem.

A base local não possui depoimentos nem posts; por isso as seções de relatos e cartões fictícios não aparecem na versão principal. O aviso de demonstração e a página sintética também não são servidos nesse cenário. Os contatos de exemplo já existentes na fonte foram preservados, incluindo `contato@exemplo.edu.br`, `(11) 99999-9999` e o endereço de São Paulo. Esta importação não afirma que esses contatos são dados confirmados do site publicado.

A demonstração original permaneceu intacta. Uma cópia adicional do seu banco e mídia foi salva em `.preview/backups/before-local-content-20260909T201405374293Z/`. O manifesto `.preview/local-source.json` registra a origem e ativa o cenário local por padrão. Reexecutar `import-local` preserva a cópia já criada; não existe sincronização automática posterior.

Validação desta importação:

- [Banco, mídia e preservação da origem](../../.preview/evidence/local-content-import.json): integridade SQLite aprovada, conteúdo equivalente e hashes da origem/demonstração inalterados.
- [Paridade com os templates antigos](../../.preview/evidence/content-parity-local.json): cinco páginas sem perda detectada de textos, traduções, imagens, destinos ou campos. O verificador também inclui outras páginas publicadas do CMS, quando existirem, e confere os arquivos compartilhados protegidos.
- [Revisão no navegador](../../.preview/evidence/local-content-browser.json): 20 verificações — cinco páginas × PT/EN × claro/escuro — aprovadas, sem conteúdo sintético, links internos para a porta errada ou rolagem horizontal.
- [Contato](../../.preview/evidence/contact-isolation-local.json) e [falhas controladas do Turnstile](../../.preview/evidence/turnstile-failures-local.json): rejeições aprovadas, sem gravação nos quatro bancos. A limitação anterior do Turnstile no navegador não foi reclassificada como resolvida.
- Ruff aprovado; Django sem erros, com os dois avisos conhecidos do treebeard. A suíte de 101 testes e a matriz de 38 resoluções registradas abaixo pertencem à revisão anterior do mesmo design; não foram repetidas integralmente para esta troca de dados.

Para verificar o cenário principal, defina `$env:KOMUNIKI_PREVIEW_SCENARIO = 'local'` antes dos comandos Python de validação abaixo. As evidências novas recebem o sufixo `-local`. Para reproduzir a matriz antiga que exige os cenários fictícios, inicie explicitamente `-ReviewSource demo` e mantenha os relatórios anteriores como históricos.

## Matriz de preservação

| Elementos atuais | Apresentação experimental | Condições e verificação |
|---|---|---|
| Marca/logo, Início, Sobre, Cursos, Notícias e contato | Cabeçalho fixo em cápsula | Logo cadastrado ou nome do Site; mesmos destinos. Menu disponível abaixo de 1024 px, inclusive tablet. |
| Idioma, tema e menu móvel | Controles planos com nomes acessíveis | PT/EN, fallback português, persistência entre visitas; Escape fecha o menu e devolve o foco ao botão. |
| Instagram, YouTube, e-mail, telefone, endereço e copyright | Rodapé preto; e-mail em amarelo | Links e dados locais preservados, inclusive valores de exemplo. |
| Badge, título e descrição da Home | Abertura editorial dividida com a nova composição 3D | Mesmos campos, traduções e fallbacks; dois botões e âncora `#hero-support-sheet` mantidos. |
| Apresentação institucional e Prêmio Paulo Freire | Bloco de contraste e composição em duas colunas | Texto e reconhecimento mantidos; no tema escuro o bloco inverte para superfície clara. |
| Diferenciais cadastrados | Grade de cartões e textos | Todos os quatro registros ativos locais continuam visíveis; fallback da view permanece intacto. |
| Três trilhas | Cartões com etiquetas menta | Profissionalizante, cursos livres e desenvolvimento pessoal; descrições e links para Cursos mantidos. |
| Kelly Farias | Foto existente, biografia e quatro etiquetas | Mesmo JPEG, texto e etiquetas; carregamento da imagem conferido após rolagem. |
| Depoimentos | Três cartões com foto ou ícone de fallback | Mesma consulta por Site e `is_featured`, limite de três. Se vazios, a seção continua oculta. Demo exercita ambas as apresentações. |
| Feed social | Componente exclusivo da escola | Mantém habilitação da seção, filtros por plataforma, link oficial condicional, até seis posts; somente três abaixo de 640 px. Imagem, fallback e indicação de vídeo conferidos. |
| Chamadas finais da Home | Dois blocos lado a lado | Cursos/mentorias e contato, com os mesmos textos e links. |
| História, Cursos/Mentorias/Projetos e serviços em Sobre | Abertura editorial e cartões | Quatro áreas de atuação e chamada final preservadas. |
| Seis cursos em três grupos | Catálogo com etiquetas e listas de definição | Descrições, horas, duração, requisitos, formatos, observações, prêmio e CTAs preservados. Âncora `#grade-cursos` testada. |
| Nome, e-mail, telefone, assunto e mensagem | Formulário em cartão plano | Nomes, tipos, obrigatoriedade, opções, CSRF e backend mantidos. Telefone continua opcional. |
| Turnstile, envio, erros e confirmação | Mesmos estados com foco visível e aviso persistente dispensável | Envio real no navegador com chaves de teste; mensagem salva somente no SQLite da demo. Rejeições HTTP e estados inválidos conferidos. |
| Política de privacidade | Coluna de leitura, hierarquia e blocos | Todo o texto, listas, contato e aviso de atualização preservados. |
| Página genérica do CMS | Título editorial, imagem e corpo de leitura | `sanitize_html`, título, imagem, conteúdo e contato mantidos. Demo verifica um título longo nas quatro larguras. |

O novo `base_school_editorial.html` e `templates/school/editorial/` isolam a apresentação. O `base_school.html` original, o `base_news.html` e os dois componentes sociais compartilhados continuam idênticos aos do projeto original; vagas e Blog da Kelly conservam esses consumidores. Views, modelos, formulários e rotas públicas também permanecem idênticos.

## Evidências e limites

- **101 testes existentes passaram** em `apps/school`, `apps/contact`, `apps/social`, `apps/common` e `apps/hiring`.
- **Ruff passou**. O check do Django não encontrou erros; permanecem dois avisos preexistentes do treebeard sobre alterações futuras de comportamento. `collectstatic` completou no diretório isolado.
- [Paridade de conteúdo](../../.preview/evidence/content-parity.json): cinco páginas sem perdas detectadas nos fragmentos de texto, traduções, conjuntos de destinos/imagens e contrato dos campos. O relatório também verifica hashes dos arquivos compartilhados e de backend protegidos.
- [Geometria](../../.preview/evidence/responsive-audit.json): matriz de 80 combinações, além de cinco inspeções iniciais — cinco páginas × 375/768/1024/1440 px × claro/escuro × PT/EN, sem rolagem horizontal. Fontes carregadas; superfícies principais sem sombras ou gradientes.
- O campo histórico `brokenImages` desse primeiro relatório incluía imagens lazy ainda fora da tela. A inspeção após rolagem confirmou todas as seis imagens da Home demonstrativa carregadas, incluindo a foto da Kelly; não se tratava de URLs quebradas.
- [Verificação complementar](../../.preview/evidence/responsive-followup.json): 28 casos após os ajustes de tipografia, incluindo título longo do CMS, feed da demo, e Home/Sobre/Cursos em inglês. Sem rolagem horizontal.
- [Interações](../../.preview/evidence/interaction-audit.json): menu, teclado/foco, persistência, âncoras, mídia e envio. Nenhum erro de console foi registrado na verificação final.
- [Contato e isolamento](../../.preview/evidence/contact-isolation.json): campos inválidos, assunto fora das opções, Turnstile ausente e CSRF ausente rejeitados. Hashes dos três bancos inalterados durante essas requisições rejeitadas. A única mensagem `visual-test@example.invalid` está na demo; origem e cópia atual têm zero mensagens.
- [Falhas do Turnstile](../../.preview/evidence/turnstile-failures.json): rejeição, timeout e resposta inválida do provedor exercitados com respostas controladas e banco aberto somente para leitura. O formulário mostra o erro e não grava. A integração real no navegador foi validada para sucesso com as chaves oficiais de teste.
- O conteúdo é legível sem animações de entrada. A regra `prefers-reduced-motion` remove as transições e a rolagem suave. Esta rodada verifica o navegador local, sem alegar cobertura de aparelhos físicos, outros motores de navegador ou produção.

Comandos para reproduzir as verificações locais:

```powershell
# Na worktree, com as duas versões iniciadas:
& '..\news_portal\.venv\Scripts\python.exe' -B scripts/preview/verify_content.py
& '..\news_portal\.venv\Scripts\python.exe' -B scripts/preview/verify_contact.py
& '..\news_portal\.venv\Scripts\python.exe' -B scripts/preview/verify_turnstile_failure.py
& '..\news_portal\.venv\Scripts\python.exe' -m ruff check .
& '..\news_portal\.venv\Scripts\python.exe' -B manage.py check --settings=config.settings.design_preview

# A suíte usa o banco de testes configurado pelo projeto:
$env:SECRET_KEY = 'editorial-tests-only-not-for-production'
$env:DB_NAME = 'unused'
$env:DB_USER = 'unused'
$env:DB_PASSWORD = 'unused'
& '..\news_portal\.venv\Scripts\python.exe' -B -m pytest apps/school apps/contact apps/social apps/common apps/hiring -q
```

`verify_contact.py` verifica também a existência de exatamente um envio de navegador com `visual-test@example.invalid` na demo, feito nesta rodada. Em uma preparação totalmente nova, realize esse envio uma vez antes de reproduzir a verificação. As requisições que o script faz são somente casos que devem ser rejeitados.

O banco de referência local não contém depoimentos nem posts. Mantém `contato@exemplo.edu.br`, `(11) 99999-9999`, `Rua da Educação, 123, São Paulo - SP`, `https://instagram.com/exemplo` e o título social `TESTE FASE 11 — Redes Sociais Kelly`. São dados de exemplo já existentes, não contatos confirmados da escola. Nenhuma sincronização com produção foi executada. O canal de contato salva no banco e usa e-mail em memória; não envia mensagens externas.

## Hover e auditoria ampliada — 9 de setembro de 2026

**Registro histórico:** o hover descrito abaixo foi preservado no checkpoint `ef03939`. A rodada seguinte acrescenta o sistema de movimento solicitado, documentado em [Movimento editorial e rollback](komuniki-editorial-motion.md), com testes próprios e um commit separado.

O CSS exclusivo da escola agora aplica somente uma ampliação discreta ao passar o mouse: `scale(1.02)` em botões, controles, marca e seta; `scale(1.01)` nos cartões e na imagem do hero. A transição usa `transform 180ms ease-out`. Não há animação de entrada ou movimento contínuo. As regras só entram com `hover: hover`, `pointer: fine` e `prefers-reduced-motion: no-preference`; campos e painéis do formulário ficam estáveis. A versão do CSS no template é `v=5`.

A inspeção em 280 px identificou palavras quebradas no título. Abaixo de 360 px, a marca e os títulos receberam tamanhos menores, preservando a composição nas demais larguras.

### Resultado da matriz

- **152 jornadas completas aprovadas**, em 38 resoluções × dois temas × PT/EN.
- **1.064 verificações de página e 1.392 verificações de interação**. Cada jornada visita Home, Sobre, Cursos, Contato e Privacidade com o conteúdo atual, além da Home demonstrativa e da página do CMS com título longo.
- Verificados: navegação real pelos links, seis cursos, âncora da grade, menu móvel com Escape e retorno do foco, foco visível por teclado, persistência após recarregar/navegar, campos obrigatórios e e-mail inválido, limites de três/seis posts, fontes e ausência de rolagem horizontal, cortes internos e sobreposição do cabeçalho.
- Medição real do hover confirmou as escalas de 1,01 e 1,02, a duração de 180 ms e o retorno a `transform: none`. A largura usada pelo layout permaneceu igual antes/depois.
- Reexecutados: **101 testes existentes aprovados**, Ruff sem erros, paridade de conteúdo aprovada e Django sem erros, com os dois avisos preexistentes do treebeard. O pytest reportou avisos conhecidos sobre Django 6 e diretório de estáticos da configuração de testes.

Resoluções em pixels CSS: 280×653, 320×568, 360×640, 375×667, 390×844, 412×915, 430×932, 568×320, 667×375, 844×390, 932×430, 600×960, 768×1024, 820×1180, 1024×768, 1180×820, 1280×720, 1366×768, 1440×900, 1536×864, 1920×1080, 2560×1440, 3440×1440, 3840×2160 e 4096×1440. Os limites do CSS também foram exercitados em 399×844, 400×844, 639×960, 640×960, 641×960, 767×1024, 769×1024, 1023×768, 1025×768, 1100×820, 1101×820, 1599×900 e 1600×900.

### Limites e ocorrências

Esta é uma matriz finita no Chromium local. Não equivale a todos os aparelhos físicos, densidades, zooms ou motores de navegador. O controle de viewport limitou pedidos de 5120 px a 4096 px; por isso 5120 px não consta como aprovado. As regras de toque e movimento reduzido foram revisadas no CSS, sem emulação dessas preferências pelo navegador disponível.

Uma aba de auditoria encerrou a renderização durante a sequência longa em 3440 px. Os cinco casos interrompidos passaram na repetição em uma aba nova; a causa do encerramento não foi determinada. O registro bruto preserva essas tentativas, os quatro pedidos limitados de 5120 px e uma chamada com argumento inválido que não executou ações. O resumo usa a última tentativa válida de cada combinação declarada. Após a retomada da sessão, os servidores locais estavam encerrados e foram reiniciados sem recriar os bancos.

**Contato nesta rodada:** em 280 px, um envio fictício sem token foi rejeitado com a mensagem anti-bot e os valores preservados. As verificações HTTP de campos, assunto, CSRF e Turnstile ausente passaram, assim como as falhas controladas de rejeição, timeout e JSON inválido. Nenhuma nova mensagem foi gravada: origem e conteúdo atual continuam com zero; a demo mantém o único envio válido da revisão anterior. A nova tentativa de sucesso não foi concluída: o widget retornou `300030` e não disponibilizou token, inclusive após tentar o formulário em desktop. A [documentação oficial do Turnstile](https://developers.cloudflare.com/turnstile/troubleshooting/client-side-errors/error-codes/) classifica `300*` como falha genérica do desafio; a causa específica desta sessão não foi determinada. A geometria do widget carregado e novos envios válidos nas demais resoluções ficam **não verificados nesta rodada**. A matriz de layout e campos não deve ser interpretada como sucesso dessa dependência externa.

### Evidências e reprodução

- [Resumo da matriz](../../.preview/evidence/hover-e2e/summary.json) e [tentativas completas](../../.preview/evidence/hover-e2e/matrix-v5.jsonl).
- [Medição do hover](../../.preview/evidence/hover-e2e/hover.json), [captura do cartão](../../.preview/evidence/hover-e2e/hover-card.png) e [Home atualizada](../../.preview/evidence/hover-e2e/home-desktop-v5.png).
- [Limitação do contato](../../.preview/evidence/hover-e2e/contact-provider-session.json) e [erro visível em 280 px](../../.preview/evidence/hover-e2e/contact-turnstile-error-280.png).

`scripts/preview/browser_e2e.mjs` exporta a matriz e `runFlow`, executado dentro do navegador CUA com os controles documentados de aba e viewport. Não é um programa Playwright independente. Em uma nova execução, use outro nome de relatório para preservar as evidências. Interrompa o lote se uma chamada retornar `error`, recupere a aba e repita apenas os casos interrompidos. O resumo desta rodada pode ser regenerado com:

```powershell
& '..\news_portal\.venv\Scripts\python.exe' -B scripts/preview/summarize_e2e.py
```

Os dois endereços e os comandos de iniciar/encerrar no início deste documento continuam válidos. Tudo permanece na worktree experimental, sem publicação.

## Fonte atual de produção — pendência e exportação

**Histórico:** a consulta pública voltou a funcionar em 12/09/2026 e permitiu concluir a atualização dos dados visíveis, sem acesso administrativo. O exportador abaixo continua disponível para uma eventual leitura autorizada de registros internos, que não foi necessária nesta rodada.

Na nova solicitação de informações reais para produção, o acesso a `https://komuniki.com.br/` voltou a falhar com `ERR_CERT_DATE_INVALID`. Não foi encontrada configuração de alias SSH em `~/.ssh/config`; o repositório documenta `/opt/kelly_sys`, o projeto Compose `kellysys` e o serviço `web`, mas não fornece um endpoint administrativo utilizável nesta sessão. Nenhum aviso de segurança foi contornado, nenhuma credencial foi copiada e nada foi publicado.

`scripts/preview/export_school_content.py` está preparado para ler o projeto em execução na origem. Ele exporta JSON para a saída padrão: Site e campos públicos da configuração, Home ativa, diferenciais ativos, páginas publicadas, depoimentos destacados, posts que a Home exibe, campos públicos das respectivas contas sociais, constantes de cursos e HTML renderizado das páginas públicas. A exportação não inclui usuários, mensagens de contato, assinantes, tokens sociais nem variáveis de ambiente. As mídias binárias não entram no JSON; suas referências devem ser revisadas para transferência posterior.

A leitura usa uma transação PostgreSQL `REPEATABLE READ, READ ONLY` ou SQLite com `query_only`. O script foi validado nas duas cópias locais, incluindo os casos sintéticos com redes sociais: 18 registros/cinco páginas na cópia local e 30 registros/seis páginas na demonstração. O hash do banco demonstrativo permaneceu igual e os campos sensíveis explicitamente excluídos não apareceram nos registros exportados. Ruff passou. **A execução no PostgreSQL de produção ainda não foi realizada.**

Para executar o exportador, o diretório atual deve ser a raiz do projeto e `DJANGO_SETTINGS_MODULE` deve estar configurado para o ambiente cuja fonte se quer ler. A saída JSON deve ser guardada fora do versionamento. A importação real depende do alias/host SSH com autenticação existente ou de uma exportação recente fornecida pelo responsável; a pergunta de acesso foi apresentada ao usuário.

Contatos, logo e textos administráveis já são lidos do banco pelo design novo. Os textos fixos das páginas e cursos também precisam ser comparados com a versão implantada; a exportação inclui o HTML e as constantes para permitir essa conferência. Não foram alterados contatos, links sociais ou textos institucionais com base em suposições.

## Arte e fontes

Asset final: `static/images/komuniki-editorial-hero.png`, PNG RGBA com transparência, 1254 × 1254, gerado pela ferramenta integrada **imagegen**. A imagem é uma composição ilustrativa própria deste experimento. A foto da Kelly não foi substituída. A marca também mantém seu mecanismo de logo cadastrado/nome do Site no cabeçalho.

As três fontes ficam em `static/fonts/editorial/`: Barlow Condensed 700, Inter variável e IBM Plex Mono regular. São servidas localmente; suas licenças OFL acompanham os arquivos. O restante do JavaScript usa as bibliotecas já vendorizadas pelo projeto.

Prompt final usado no imagegen:

> Create a premium photorealistic 3D product sculpture for the hero of Komuniki, a Brazilian communication, arts and leadership school. This is a single isolated raster website asset, NOT a screenshot or web layout. Composition: a compact sculptural arrangement of two tactile light-gray raw concrete cubes and one warm natural wood block, with a finely detailed black and brushed-silver studio microphone emerging from the tallest cube, a pale mint #d1ffca speech-shaped geometric protrusion, and a very small voltage-yellow #fff100 circular detail. Confident gallery product photography, front three-quarter view, subtly playful and sophisticated brutalist editorial mood. Print the exact word 'KOMUNIKI' in crisp black uppercase neo-grotesque letters on the front concrete face. Only that text, no other brands or words. Neutral studio illumination that reveals the concrete pores, wood grain and microphone mesh. The whole sculpture fully visible with breathing room around it, centered in a near-square composition, no props beyond the stated objects. Genuinely transparent background with alpha; no backdrop, no floor plane, no large cast shadow, no glow, no gradients in the background. It will sit on #e5e5e5 light canvas and black dark canvas. High-quality realistic materials, clean silhouette, no people, no stock photography, no watermarks.
