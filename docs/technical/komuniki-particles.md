# Hero de partículas da Komuniki

Implementado em 13/09/2026 na worktree `news_portal-komuniki-design`, branch `codex/komuniki-editorial-test`. A primeira versão, com palco preto, foi versionada junto com a paleta azul clara no commit `8983664` (`feat(school): replace hero illustration with WebGL particle stage`). Os refinamentos de camadas e tema claro descritos aqui vieram no commit seguinte, `feat(school): layer the hero particles over the copy and drop the black stage`.

O hero da Home é uma nuvem WebGL de 16.000 triângulos (9.000 em telas abaixo de 720 px) que se remonta em loop: **microfone RCA 44-BX → Terra → nuvem dispersa → microfone**. A referência visual é o site da Dala (unseen.co/projects/dala), com um ciclo automático no lugar da rolagem.

## Decisões

- **Exceção à regra de nenhum movimento**, ao lado do [reveal de texto por linha](komuniki-text-reveal.md). O resto do site continua estático. Com `prefers-reduced-motion: reduce` não há ciclo nem rotação: o microfone fica parado e a deriva anda a um quarto da velocidade.
- **Duas camadas em vez de um palco.** A nuvem é desenhada em dois canvases transparentes que cobrem o hero inteiro: um atrás do texto (`z-index` 0) e outro na frente (`z-index` 2, sem capturar cliques). Cada partícula fica na camada do seu lado do plano que passa pelo centro da forma, com transição suave de ±0,35 unidade. Quando a nuvem alcança o título, os triângulos da frente cruzam por cima das letras e os de trás passam por baixo. São duas chamadas de draw por quadro, uma por camada.
- **Mesmo enquadramento.** A câmera continua enquadrando o espaço do `figure` (`.ed-particles`) com `setViewOffset`, e os canvases só mostram mais do mesmo plano ao redor. Microfone e Terra ficam no mesmo lugar e tamanho da primeira versão. O topo (72 px) e a base (140 px) do hero somem em degradê, então nada termina num corte reto.
- **Tema claro como tinta.** No escuro vale a luz aditiva calibrada sobre preto. No claro, luz somada estouraria para branco sobre o `#e5e5e5`, então as partículas usam blending normal e uma paleta de tinta com os mesmos matizes em tons médios, visíveis tanto no fundo quanto sobre as letras pretas; o branco azulado vira o azul `#0b3a75` da Komuniki. O tema acompanha a classe `dark` do `<html>` sem recarregar.
- **Nuvem dispersa maior.** `looseRadius` passou de 3,6 para 6,2 para a nuvem chegar ao título, e aos botões no celular. Microfone e Terra não mudaram.
- **Explosão maior do microfone para a Terra.** Essa passagem usa `burstSpread` (3,2) no lugar de `spread` (1,35), então as partículas se espalham pela tela como na passagem Terra → nuvem. As outras duas passagens continuam com `spread`.
- **Arrastar para girar.** Mouse ou toque sobre o espaço da forma gira a nuvem, com inclinação limitada a ±0,6 rad. Ao soltar, a inércia se dissolve na rotação automática e a inclinação volta sozinha para a vista de frente. No toque só o gesto horizontal gira, e o vertical continua rolando a página. Com movimento reduzido o arraste funciona, sem inércia nem rotação automática.
- **Memória de GPU sob controle.** Cada camada tem antialias e cobre o hero inteiro, então o pixel ratio cede quando o buffer passaria de 2,6 milhões de pixels por camada. Buffers de profundidade e stencil não são criados.
- **three r186 oficial, sem minificação.** A r186 não publica build minificado, nem no npm nem na tag do GitHub, e o projeto não tem bundler. São ~2,3 MB crus e ~455 KB com gzip.
- **WebGLRenderer.** O shader é GLSL de `ShaderMaterial`; o `WebGPURenderer` exigiria reescrevê-lo em TSL.
- **Rotação medida em segundos.** Os 0,0016 rad por quadro viraram 0,096 rad/s: igual a 60 Hz, sem acelerar em telas de 120/144 Hz.
- O PNG `static/images/komuniki-editorial-hero.png` saiu da Home, mas fica no repositório porque `scripts/preview/prepare.py` o usa como mídia de demonstração.

## Arquivos

| Arquivo | Papel |
|---|---|
| `static/js/school-editorial-particles.js` | Módulo ES: `CONFIG`, amostragem, shader, camadas, loop e `mountParticles()` |
| `static/js/vendor/three-r186/` | `three.module.js`, `three.core.js`, `addons/loaders/GLTFLoader.js`, `addons/utils/BufferGeometryUtils.js`, `addons/utils/SkeletonUtils.js` e `LICENSE` (MIT), idênticos ao pacote `three@0.186.0` do npm, com integridade sha512 conferida no registro |
| `static/particles/rca44-geometry.glb` | Microfone sem texturas nem materiais: 3.430 vértices, 4.006 triângulos, só `POSITION` e índices |
| `static/particles/land-mask-640x320.bin` | Terra firme do Natural Earth 110m (domínio público), equiretangular, 1 bit por pixel |
| `templates/school/home.html` | `data-particles-scene` na `section.ed-hero`, que recebe os canvases; o espaço `[data-particles]` em `figure.ed-hero-art` define onde a forma fica; import map e `<script type="module">` no bloco `extra_js` |
| `static/css/school-editorial.css` | `.ed-hero` vira contexto de empilhamento; `.ed-particles` guarda a proporção (1:1, 1,15 no celular); `.ed-particles-canvas` cobre o hero com máscara de degradê; folha em `?v=10` |
| `apps/school/tests.py` | `test_school_homepage_renders_particle_stage_with_local_three` |

## Carregamento

- O import map aponta `three` e `three/addons/loaders/GLTFLoader.js` para `{% static %}`. As chaves com o prefixo estático, como `/static/js/vendor/three-r186/three.core.js`, remapeiam os imports relativos internos do three para as URLs com hash do `collectstatic`. Sem elas, em produção esses imports cairiam nos nomes sem hash, que o Nginx serve com `Cache-Control: immutable` por 30 dias.
- A CSP do Django e do Nginx já permite script inline, módulos e `fetch` do mesmo domínio. CDN continua bloqueado, por isso o three é copiado para o projeto.
- **Para atualizar o three:** criar outra pasta `three-rNNN` e trocar os caminhos no import map de `home.html`. Não sobrescrever arquivos de uma pasta já publicada.
- Na prévia local o espaço recebe `data-particles-debug`, que expõe `window.komunikiParticles` com `renderers` (as duas camadas), `state` (forma, tema, `drawCalls` e demais contadores) e `dispose()`. Fora da prévia o atributo não é renderizado.
- `dispose()` para o loop, desliga observers e `Timer`, libera geometria, material e os dois renderers e remove os canvases. O módulo o chama quando o htmx limpa o espaço; numa navegação comum o navegador já libera tudo.
- Desde 14/09/2026 o espaço recebe `data-particles-ready` e dispara `komuniki:particles-ready` quando desenha o primeiro quadro, quando está fora da tela ou quando a montagem falha. O módulo da página (`js/school-editorial.js`) espera esse aviso para mostrar a Home já com o palco desenhado, com teto de 2,5 s. O script está em `?v=3`. Veja [Transição e rolagem](komuniki-transicao-e-rolagem.md).

## Onde ajustar

Os valores ficam no objeto `CONFIG`, no topo de `static/js/school-editorial-particles.js`. Para mudar sem editar o módulo, use `data-config` no template, como `data-config='{"spread": 1.1}'`, ou `mountParticles(elemento, { config: { … } })`.

| Parâmetro | Padrão | O que muda na tela |
|---|---|---|
| `count` | 16000 (9000 abaixo de 720 px) | Quantidade de triângulos. Menos deixa as formas mais ralas e alivia GPUs fracas; o alfa automático compensa o brilho. É lido uma vez, no carregamento. |
| `spread` | 1.35 | Quanto a nuvem se abre no meio da transição. 0 faz as partículas viajarem em linha reta; valores maiores levam mais triângulos para cima e para baixo do título. |
| `burstSpread` | 3.2 | Explosão só da passagem microfone → Terra. Maior espalha mais as partículas pela tela; com o mesmo valor de `spread`, ela volta a ficar compacta. |
| `drift` | 0.030 | Amplitude da respiração. Em repouso vale 22% disso e no meio do voo, 100%. 0 congela as posições; o giro próprio dos triângulos e a rotação continuam. |
| `speed` | 0.42 | Progresso da transição por segundo: cada troca leva 1 / 0,42 ≈ 2,4 s. Maior encurta a transição. |
| `alphaTarget` | 7 | Brilho global. Maior deixa tudo mais intenso e faz o microfone saturar mais cedo. |
| `triMin` | 0.020 | Tamanho do menor triângulo, em unidades da cena (o microfone tem raio 2,9). |
| `triVar` | 0.150 | Quanto os triângulos podem crescer além do mínimo. O expoente 4,5 mantém quase todos pequenos e poucos grandes. |
| `oceanKeep` | 0.15 | Densidade do oceano em relação aos continentes. Menor destaca mais os continentes; 1 apaga a diferença. |
| `dwellSolid` | 3.4 | Segundos parado no microfone e na Terra. |
| `dwellLoose` | 1.6 | Segundos parado na nuvem dispersa. |
| `looseRadius` | 6.2 | Raio da nuvem dispersa. Maior avança mais por baixo e por cima do título; com 3,6, o valor original, a nuvem não chegava ao texto. |

Fora do `CONFIG`, no mesmo arquivo, ficam os raios do microfone (2,9) e da Terra (2,62), a rotação (0,096 rad/s), a paleta com as cores de luz e de tinta, a câmera (FOV 45, `z = 10.5`), o teto de pixels por camada e a resposta do arraste (radianos por pixel, inclinação máxima, amortecimento da inércia e retorno da inclinação). A largura da transição entre camadas (0,35) está no shader, e as alturas do degradê (72 e 140 px), no CSS. O shader segue a especificação, inclusive nos comentários, com dois acréscimos comentados: camadas e tema.

## Validação

Feita em 13/09/2026 na prévia `design_preview` (porta 8013), com o Edge headless na GPU (AMD Radeon RX 9070 XT via ANGLE/D3D11). Evidências da versão em camadas em `.preview/evidence/particles-layers/`; as da primeira versão ficam em `.preview/evidence/particles/`.

| Critério | Resultado |
|---|---|
| Chamadas de draw | Uma por camada, duas por quadro, em todas as amostras; 16.000 triângulos, 1 geometria, 0 texturas e 1 programa por camada |
| 60 fps estáveis com 16.000 partículas | 239,7 fps médios em 90 s, o teto da tela de 240 Hz; 0,028 ms de CPU por quadro somando as duas camadas |
| Microfone nítido e legível | Igual à primeira versão nos dois temas: cápsula, suporte, haste, base e cabo |
| Terra com continentes e limbo, sem listras | Continentes mais densos que o oceano e borda definida, também no tema claro |
| Camadas e continuidade | Na nuvem dispersa e nas transições, triângulos da frente cruzam as letras do título e os de trás somem sob elas (`*-rest-disperso-zoom.png`); nenhum corte reto no hero |
| Loop sem crescimento de memória | 90 s (~6 ciclos) com coleta de lixo forçada: heap de 13,25 MB para 13,52 MB; geometrias, texturas e programas constantes (`cdp-soak.json`) |
| Nada renderiza fora da viewport | Com o hero fora da tela, 0 quadros em 1,5 s e loop parado; volta a 239 fps |
| `prefers-reduced-motion: reduce` sem ciclo | 40 amostras em 20 s: sempre o microfone, `progress` 1, nenhuma transição (`cdp-reduced.json`) |
| Zero erros e avisos no console | Nenhuma mensagem do componente. Continuam os avisos preexistentes do `tailwind.min.js`, o 404 de `/favicon.ico` e, no Edge, o bloqueio de armazenamento do Turnstile pela Prevenção de Rastreamento |
| Redimensionar não distorce | Buffers das duas camadas iguais ao hero × pixel ratio em 1440×900, 1024×768 e 375×812 (9.000 partículas); sem rolagem horizontal; a forma continua no espaço do `figure` |

Também verificado:

- **Troca de tema** sem recarregar: claro → escuro → claro.
- **Arraste:** com o mouse, 200 px na horizontal giraram 1,2 rad e 80 px na vertical inclinaram 0,48 rad. Depois de soltar, a forma continuou girando e a inclinação voltou para 0,08 rad em 1,5 s. Um deslize de toque de 150 px girou 0,9 rad.
- **Explosão microfone → Terra:** com `burstSpread` 3,2 as partículas ocupam a área da nuvem dispersa (`.preview/evidence/round3/r3-burst-terra.png`).
- **Liberação:** o evento `htmx:beforeCleanupElement` removeu os dois canvases e zerou geometrias e programas.
- **Estáticos de produção:** o `collectstatic` com `CompressedManifestStaticFilesStorage` passou. O import map não mudou desde a primeira versão, quando todos os módulos carregaram pela URL com hash sob a CSP.
- **Testes:** 467 testes do pytest (com as variáveis `SECRET_KEY` e `DB_*` que o CI define) e Ruff passaram.
- **Janela oculta:** com a sessão do Windows bloqueada ou a aba escondida, o Chromium segura o `requestAnimationFrame` e o `THREE.Timer` zera o delta, então a animação para até a página voltar a aparecer. É o comportamento esperado; as medições acima usaram as flags do headless que desligam essa suspensão.
- O roteiro `scripts/preview/presentation_e2e.mjs` depende do runtime de navegador do Codex e não foi executado. Ele audita animações CSS e o nome `school-editorial-motion`; os canvases não usam nenhum dos dois.

## Reversão

- **Voltar ao palco preto da primeira versão:** restaurar `static/js/school-editorial-particles.js`, `static/css/school-editorial.css`, `templates/school/home.html`, `templates/base_school_editorial.html` e `apps/school/tests.py` do commit `8983664`.
- **Voltar à ilustração estática:** partir da primeira versão e seguir os passos abaixo.
  1. Em `templates/school/home.html`, trocar o `<div class="ed-particles" …>` por `<img src="{% static 'images/komuniki-editorial-hero.png' %}?v=2" width="1024" height="1024" alt="" fetchpriority="high" decoding="async">` e apagar o bloco `extra_js`.
  2. Em `static/css/school-editorial.css`, trocar as regras `.ed-particles` por `.ed-hero-art img{width:100%;aspect-ratio:1;object-fit:contain}` (e `.ed-hero-art img{aspect-ratio:1.15}` no bloco de celular), tirar o `gap:16px` de `.ed-hero-art` e subir a versão da folha.
  3. Remover o teste novo de `apps/school/tests.py` e voltar `particles_hero_present` para `approved_hero_preserved` em `scripts/preview/verify_public_content.py`.
  4. Opcional: apagar `static/js/school-editorial-particles.js`, `static/js/vendor/three-r186/` e `static/particles/`.
