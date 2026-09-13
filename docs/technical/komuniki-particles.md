# Hero de partículas da Komuniki

Implementado em 13/09/2026 na worktree `news_portal-komuniki-design`, branch `codex/komuniki-editorial-test`, e versionado junto com a paleta azul clara no commit `feat(school): replace hero illustration with WebGL particle stage`. O hero da Home trocou a ilustração estática por uma nuvem WebGL de 16.000 triângulos (9.000 em telas abaixo de 720 px) que se remonta em loop: **microfone RCA 44-BX → Terra → nuvem dispersa → microfone**. A referência visual é o site da Dala (unseen.co/projects/dala), com um ciclo automático no lugar da rolagem.

## Decisões

- **Única exceção à regra de nenhum movimento.** O resto do site continua estático. Com `prefers-reduced-motion: reduce` não há ciclo nem rotação: o microfone fica parado e a deriva anda a um quarto da velocidade.
- **Palco preto nos dois temas.** O blending aditivo soma luz; sobre o cinza `#e5e5e5` do tema claro as cores estourariam para branco. Os parâmetros foram calibrados sobre preto.
- **three r186 oficial, sem minificação.** A r186 não publica build minificado, nem no npm nem na tag do GitHub, e o projeto não tem bundler. São ~2,3 MB crus e ~455 KB com gzip; somando os modelos, fica abaixo da metade do PNG anterior (1,2 MB).
- **WebGLRenderer.** O shader é GLSL de `ShaderMaterial`; o `WebGPURenderer` exigiria reescrevê-lo em TSL.
- **Rotação medida em segundos.** Os 0,0016 rad por quadro viraram 0,096 rad/s: igual a 60 Hz, sem acelerar em telas de 120/144 Hz.
- O PNG `static/images/komuniki-editorial-hero.png` saiu da Home, mas fica no repositório porque `scripts/preview/prepare.py` o usa como mídia de demonstração.

## Arquivos

| Arquivo | Papel |
|---|---|
| `static/js/school-editorial-particles.js` | Módulo ES: `CONFIG`, amostragem, shader, loop e `mountParticles()` |
| `static/js/vendor/three-r186/` | `three.module.js`, `three.core.js`, `addons/loaders/GLTFLoader.js`, `addons/utils/BufferGeometryUtils.js`, `addons/utils/SkeletonUtils.js` e `LICENSE` (MIT), idênticos ao pacote `three@0.186.0` do npm, com integridade sha512 conferida no registro |
| `static/particles/rca44-geometry.glb` | Microfone sem texturas nem materiais: 3.430 vértices, 4.006 triângulos, só `POSITION` e índices |
| `static/particles/land-mask-640x320.bin` | Terra firme do Natural Earth 110m (domínio público), equiretangular, 1 bit por pixel |
| `templates/school/home.html` | Palco `[data-particles]` dentro de `figure.ed-hero-art`; import map e `<script type="module">` no bloco `extra_js` |
| `static/css/school-editorial.css` | `.ed-particles`: proporção 1:1 (1,15 no celular), cantos de 32/24 px e fundo preto; folha em `?v=9` |
| `apps/school/tests.py` | `test_school_homepage_renders_particle_stage_with_local_three` |

## Carregamento

- O import map aponta `three` e `three/addons/loaders/GLTFLoader.js` para `{% static %}`. As chaves com o prefixo estático, como `/static/js/vendor/three-r186/three.core.js`, remapeiam os imports relativos internos do three para as URLs com hash do `collectstatic`. Sem elas, em produção esses imports cairiam nos nomes sem hash, que o Nginx serve com `Cache-Control: immutable` por 30 dias.
- A CSP do Django e do Nginx já permite script inline, módulos e `fetch` do mesmo domínio. CDN continua bloqueado, por isso o three é copiado para o projeto.
- **Para atualizar o three:** criar outra pasta `three-rNNN` e trocar os caminhos no import map de `home.html`. Não sobrescrever arquivos de uma pasta já publicada.
- Na prévia local o palco recebe `data-particles-debug`, que expõe `window.komunikiParticles` com `renderer`, `state` e `dispose()`. Fora da prévia o atributo não é renderizado.
- `dispose()` para o loop, desliga observers e `Timer`, libera geometria, material e renderer e remove o canvas. O módulo o chama quando o htmx limpa o palco; numa navegação comum o navegador já libera tudo.

## Onde ajustar

Os valores ficam no objeto `CONFIG`, no topo de `static/js/school-editorial-particles.js`. Para mudar um palco sem editar o módulo, use `data-config` no template, como `data-config='{"spread": 1.1}'`, ou `mountParticles(elemento, { config: { … } })`.

| Parâmetro | Padrão | O que muda na tela |
|---|---|---|
| `count` | 16000 (9000 abaixo de 720 px) | Quantidade de triângulos. Menos deixa as formas mais ralas e alivia GPUs fracas; o alfa automático compensa o brilho. É lido uma vez, no carregamento. |
| `spread` | 1.35 | Quanto a nuvem se abre no meio da transição. 0 faz as partículas viajarem em linha reta; valores altos jogam partículas para fora do palco, onde são recortadas. |
| `drift` | 0.030 | Amplitude da respiração. Em repouso vale 22% disso e no meio do voo, 100%. 0 congela as posições; o giro próprio dos triângulos e a rotação continuam. |
| `speed` | 0.42 | Progresso da transição por segundo: cada troca leva 1 / 0,42 ≈ 2,4 s. Maior encurta a transição. |
| `alphaTarget` | 7 | Brilho global. Maior deixa tudo mais claro e faz o microfone estourar em branco mais cedo. |
| `triMin` | 0.020 | Tamanho do menor triângulo, em unidades da cena (o microfone tem raio 2,9). |
| `triVar` | 0.150 | Quanto os triângulos podem crescer além do mínimo. O expoente 4,5 mantém quase todos pequenos e poucos grandes. |
| `oceanKeep` | 0.15 | Densidade do oceano em relação aos continentes. Menor destaca mais os continentes; 1 apaga a diferença. |
| `dwellSolid` | 3.4 | Segundos parado no microfone e na Terra. |
| `dwellLoose` | 1.6 | Segundos parado na nuvem dispersa. |

Fora do `CONFIG`, no mesmo arquivo, ficam os raios das formas (microfone 2,9, Terra 2,62, disperso 3,6), a rotação (0,096 rad/s), a paleta com pesos e a câmera (FOV 45, `z = 10.5`). O shader segue a especificação à risca, inclusive nos comentários.

## Validação

Feita em 13/09/2026 na prévia `design_preview` (porta 8013) e numa cópia temporária com `DEBUG=False` e `CompressedManifestStaticFilesStorage` (porta 8014), que serve os estáticos com hash como em produção. Evidências em `.preview/evidence/particles/`.

| Critério | Resultado |
|---|---|
| Uma chamada de draw por frame | `renderer.info.render.calls` = 1 em todas as amostras; 16.000 triângulos, 1 geometria, 0 texturas, 1 programa |
| 60 fps estáveis com 16.000 partículas | 239 fps, o teto do monitor de 240 Hz, no navegador do app; 239,4 fps médios em 4 min no Edge headless; ~0,03 ms de CPU por `render()` |
| Microfone nítido e legível | Cápsula, pinos laterais do suporte, garfo, haste, base e cabo visíveis, sem borrão branco (`shape-microfone.png`) |
| Terra com continentes e limbo, sem listras | Continentes mais densos que o oceano, borda definida e nenhum moiré (`shape-terra.png`) |
| Loop sem crescimento de memória | 240 s (~15 ciclos) com coleta de lixo forçada a cada amostra: heap de 12,87 MB para 13,09 MB; geometrias, texturas e programas constantes (`cdp-soak.json`) |
| Nada renderiza fora da viewport | Com o palco fora da tela, 0 quadros em 1,5 s e loop parado; retoma ao voltar |
| `prefers-reduced-motion: reduce` sem ciclo | 40 amostras em 20 s no Edge headless com a mídia emulada: sempre o microfone, `progress` 1, nenhuma transição (`cdp-reduced.json`) |
| Zero erros e avisos no console | Nenhuma mensagem do componente. Continuam os avisos preexistentes do `tailwind.min.js`, o 404 de `/favicon.ico` e, no Edge, o bloqueio de armazenamento do Turnstile pela Prevenção de Rastreamento |
| Redimensionar não distorce | Buffer do canvas igual ao contêiner × pixel ratio em 1039×908, 1440×900 e 375×812 (proporção 1,15, pixel ratio 2, 9.000 partículas); Terra redonda; sem rolagem horizontal; o título não invade o palco |

Também verificado:

- **Estáticos de produção:** os cinco módulos do three, o módulo da Home e os dois arquivos do modelo carregaram pela URL com hash, sem nenhum pedido sem hash, sob a CSP do Django. O WhiteNoise respondeu `Cache-Control: max-age=315360000, public, immutable`.
- **Liberação:** o evento `htmx:beforeCleanupElement` removeu o canvas e zerou geometrias e programas. Vinte montagens e desmontagens seguidas não deixaram canvas nem aviso de excesso de contextos WebGL.
- **Tema escuro:** o palco preto se funde ao fundo.
- **Testes:** 467 testes do pytest passaram com as variáveis `SECRET_KEY` e `DB_*` que o CI define, incluindo o novo teste da Home; Ruff passou nos arquivos Python alterados.
- O roteiro `scripts/preview/presentation_e2e.mjs` depende do runtime de navegador do Codex e não foi executado nesta rodada. Ele audita animações CSS e o nome `school-editorial-motion`; o canvas não usa nenhum dos dois.

## Reversão

O commit acima também traz a paleta azul clara, então um `git revert` desfaria as duas coisas. Para voltar só à ilustração estática:

1. Em `templates/school/home.html`, trocar o `<div class="ed-particles" …>` por `<img src="{% static 'images/komuniki-editorial-hero.png' %}?v=2" width="1024" height="1024" alt="" fetchpriority="high" decoding="async">` e apagar o bloco `extra_js`.
2. Em `static/css/school-editorial.css`, trocar as regras `.ed-particles` por `.ed-hero-art img{width:100%;aspect-ratio:1;object-fit:contain}` (e `.ed-hero-art img{aspect-ratio:1.15}` no bloco de celular), tirar o `gap:16px` de `.ed-hero-art` e subir a versão da folha.
3. Remover o teste novo de `apps/school/tests.py` e voltar `particles_hero_present` para `approved_hero_preserved` em `scripts/preview/verify_public_content.py`.
4. Opcional: apagar `static/js/school-editorial-particles.js`, `static/js/vendor/three-r186/` e `static/particles/`.
