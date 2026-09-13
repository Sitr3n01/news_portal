# Komuniki estática com destaque azul

Revisão local de **13/09/2026**, na branch `codex/komuniki-editorial-test`, partindo do checkpoint de conteúdo oficial `8d7c349`. O usuário pediu a remoção de todo movimento, inclusive hover, mantendo os dados atualizados. Checkpoint desta apresentação: tag `codex/komuniki-static-blue`.

## Apresentação

- Removidos o controlador e CSS de movimento, reveal dos títulos, flutuação da ilustração, botão de pausa e mudança de superfície do cabeçalho ao rolar. O cabeçalho permanece fixo e acompanha somente o tema escolhido.
- Removidas ampliações e deslocamentos no hover/pressionamento. Animações, transições e rolagem suave ficam desativadas na base editorial, incluindo estados do formulário. Foco, sublinhado e mudanças instantâneas de cor continuam dando retorno às interações.
- Mantidos tema claro/escuro, idioma PT/EN, persistência das preferências, menu móvel, links e compensação do cabeçalho nas âncoras.
- O amarelo foi substituído pelo azul **`#0b3a75`**, medido em 13/09/2026 no fundo do botão principal “Fale com a Komuniki” em [komuniki.com.br](https://komuniki.com.br/): `rgb(11, 58, 117)`, texto branco. O e-mail destacado e o selo do prêmio usam azul com conteúdo branco para preservar o contraste.
- O pequeno botão da composição 3D também recebeu azul. A imagem mantém a composição, marca, dimensões de 1254×1254 e transparência RGBA. A edição generativa pode variar detalhes finos das texturas. A foto da Kelly não foi alterada.

O checkpoint anterior ao experimento de movimento era `ef03939`, tag `codex/komuniki-editorial-approved`, na mesma branch. Ele ainda tinha hover e rolagem suave; esta revisão remove também esses efeitos. O checkpoint com animações continua disponível em `f295ed5` e o conteúdo oficial em `8d7c349`.

## Dados e isolamento

Nenhum banco foi restaurado ou gravado. Os hashes SHA-256 do banco original, dos três bancos experimentais e da foto da Kelly foram comparados antes/depois. A versão principal mantém contatos oficiais, três diferenciais, seis cursos, textos institucionais e privacidade, sem cartão Jovem Comunicador na Home ou seção social de teste. A menção em Sobre permanece.

As portas 8011 e 8012 compartilham os templates/estáticos desta worktree, mas seus bancos continuam independentes. A porta 8011 conserva o conteúdo de referência; a 8012 conserva o conteúdo oficial. Não houve alteração do checkout original, APIs, modelos, migrações ou lógica de envio do formulário. Blog e vagas continuam com seus componentes próprios.

## Validação

- **101 testes Django passaram**, cobrindo escola, contato, redes sociais, componentes comuns e vagas. Ruff passou e o Django não apresentou erros; os avisos preexistentes de treebeard, URLField/Django 6 e diretório de estáticos dos testes permanecem.
- **80 verificações de página passaram:** cinco rotas × 375×812, 768×1024, 1024×768 e 1440×900 × claro/escuro × PT/EN. Mais 16 verificações de menu móvel, Escape e foco. Sem rolagem horizontal, sobreposição da navegação, cortes nos cartões, títulos ocultos ou animações/transições CSS.
- Inspeção real de hover confirmou `transform: none`, `animation: none` e `transition: 0s`. A âncora da Home chegou ao conteúdo visível abaixo do cabeçalho, com `scroll-behavior: auto`.
- Paridade das cinco páginas com a captura pública de 12/09: textos, expressões de tradução, títulos, descrições, links, imagem da Kelly e campos do formulário preservados. O verificador agora trata somente a data dinâmica “Última atualização” separadamente, exigindo que a prévia exiba a data atual. Isso evita marcar como conteúdo faltante a diferença natural entre dias de consulta.
- Inspeção visual final do PNG atualizado em claro/escuro, desktop e móvel, com transparência real e detalhe azul. A matriz foi executada antes da troca final do PNG, cujas dimensões foram preservadas; a Home foi novamente conferida após a troca e atualização do cache.

Cobertura no Chromium local, em pixels CSS. O envio pelo serviço externo Turnstile não foi repetido nesta revisão visual; a lógica do formulário e seus testes de backend permanecem. O CSS da escola não controla o conteúdo do iframe externo.

Evidências locais, ignoradas pelo Git, em `.preview/evidence/static-blue/`: `summary.json`, `matrix.jsonl`, `parity.json`, `interactions.json`, `isolation.json`, `home-desktop-light.png`, `home-desktop-dark.png`, `home-mobile-dark.png` e `footer-desktop-blue.png`. O roteiro atual é `scripts/preview/presentation_e2e.mjs`; os roteiros do controlador removido permanecem nos checkpoints anteriores.

## Iniciar, encerrar e reverter somente esta apresentação

```powershell
Set-Location 'C:\Users\Sitr3n\Documents\Github\news_portal-komuniki-design'
.\scripts\preview\preview.ps1 -Action start
# Revisão principal: http://127.0.0.1:8012/
# Referência de conteúdo: http://127.0.0.1:8011/
.\scripts\preview\preview.ps1 -Action stop
```

Para desfazer esta rodada, com a árvore de trabalho limpa:

```powershell
.\scripts\preview\preview.ps1 -Action stop
git revert codex/komuniki-static-blue
.\scripts\preview\preview.ps1 -Action start
```

Esse revert restaura a apresentação animada/amarela de `8d7c349` e **mantém o banco com os contatos oficiais**. Não restaurar o backup `before-official-content` para reverter a apresentação, pois ele contém os dados anteriores. Não usar reset para descartar trabalho posterior. Esta revisão termina localmente, sem push, merge ou publicação.

## Registro da edição da imagem

Ferramenta: `image_gen.imagegen` integrada, sem CLI. Arquivo final no projeto: `static/images/komuniki-editorial-hero.png`, servido com `?v=2`. Saída final da ferramenta: `C:\Users\Sitr3n\.codex\generated_images\01a081e6-6269-7f50-9dea-e4207ff99441\exec-62364b39-364c-44bb-9970-b71c9fc755e9.png`.

Prompt da alteração de cor:

> Use case: precise-object-edit. Input image is the edit target, an approved transparent PNG website hero sculpture for KOMUNIKI. Make exactly one small local color edit: change the small yellow circular button on the front lower-right concrete block to deep institutional navy blue #0b3a75, retaining its circular shape, metallic rim, highlights and shadows. Preserve every other part of the image as closely as possible: exact composition, framing and scale; same black/silver microphone, concrete blocks, wood block, mint-green speech-bubble block, text 'KOMUNIKI', lighting, material textures, and edges. Do not redesign or reposition anything. Keep original square canvas and genuinely transparent background with alpha. No background, no floor, no new shadows, no extra objects or text.

A primeira saída tinha um fundo xadrez opaco e não foi aplicada. Segunda edição para obter transparência real:

> Use case: background-extract. Edit this image: remove the entire gray-and-white checkerboard background completely. Return the isolated sculpture as a PNG with actual transparent alpha pixels (RGBA). The checkerboard is unwanted painted image content; do NOT draw or retain any checker pattern and do NOT replace it with white, black, gray, or any other solid background. Keep only the microphone, concrete blocks, wood block, mint speech bubble and small blue button, with crisp antialiased transparent edges. Preserve all foreground objects, exact KOMUNIKI text, colors, dimensions, placement and framing unchanged. This is a website cutout that must composite over both black and gray page backgrounds.
