# Reveal de texto por linha da Komuniki

Implementado em 13/09/2026 na worktree `news_portal-komuniki-design`, branch `codex/komuniki-editorial-test`, a partir de uma especificação fechada do usuário: GSAP SplitText + ScrollTrigger, dois modos (`mask` e `fade`) e valores fixos. É a segunda exceção à regra de nenhum movimento, ao lado do [hero de partículas](komuniki-particles.md).

## Decisões

- **Valores da spec, sem ajuste.** Cada linha dura 0,9 s com `power3.out`, com 0,1 s entre linhas e 0,2 s entre blocos de um grupo. `mask`: `x -50 → 0` e `yPercent 100 → 0` dentro de um recorte. `fade`: `x -50 → 0` e `opacity 0 → 1`. O hero dispara 0,15 s depois do boot; o parágrafo entra em `start+=0.5` com `opacity 0 → 1` e `y 50 → 0`, em 0,8 s, `power2.out`.
- **GSAP 3.15.0 vendorizado.** O projeto não tem npm nem bundler, e a CSP bloqueia CDN. Em 13/09/2026, `^3.13.0` resolvia para 3.15.0, que tem `mask`, `autoSplit` e `aria`. Os três builds UMD vieram do tarball do npm com a integridade sha512 conferida (`sha512-dMW4CWBT…jfZB+A==`) e são idênticos aos do pacote. A licença é a "Standard no-charge" da GSAP: gratuita, inclusive para uso comercial, mas não é MIT. Ela está citada no cabeçalho de cada arquivo.
- **Só nas páginas editoriais.** Os scripts entram em `base_school_editorial.html`. Vagas, Equipe e Blog continuam com as animações próprias de `base_school.html`, `base.html` e `base_news.html`. A regra CSS que zera `animation` e `transition` continua: o GSAP escreve estilo inline a cada quadro e não depende dela.
- **Acentos inteiros no modo `mask`.** Com o `line-height` de 0,9 da Barlow, o til e o acento agudo passam 0,05 em acima da caixa da linha, e a cedilha, 0,133 em abaixo. O recorte literal da spec cortaria "COMUNICAÇÃO" para sempre. A linha ganha `padding-block: .15em`, e o recorte volta ao lugar com `top: -.15em` e `margin-bottom: -.3em`, porque margens negativas entre irmãos colapsariam. O título vira `flow-root` para essa margem não vazar. A geometria final é idêntica à do texto estático. Como `yPercent: 100` é relativo à linha, agora mais alta, a subida percorre 1,2 em em vez de 0,9 em. O respiro opcional de .06em entre recortes não foi usado, para não mudar a altura dos títulos aprovados.
- **O hero de partículas fica fora da timeline.** Os canvases ficam fora do `figure`, e a forma acompanha a posição dele a cada quadro. O tween de ilustração da spec só esmaeceria a legenda e faria a forma saltar. A timeline do hero anima só o título e o parágrafo.
- **PT/EN pelo Alpine.** O `x-text` troca o idioma reescrevendo `textContent`, o que apaga as linhas. Um `MutationObserver` por título detecta a troca, reverte o SplitText antigo, que senão restauraria o idioma anterior no próximo resize, e divide o texto novo mantendo o estado: o que estava revelado continua revelado, e o que estava escondido continua escondido. Os scripts do GSAP carregam depois do Alpine, e a mudança de `lang` no `<html>` chama `ScrollTrigger.refresh()`.
- **Estado final depois de um re-split.** O SplitText aplica ao tween novo o tempo do anterior. Se o resize cria linhas, a última pararia no meio, por isso o módulo reforça `progress(1)` num microtask.
- **O grupo reinicia como o bloco isolado.** O timeline do grupo usa `toggleActions: 'play none none reset'`, e o `onLeaveBack` devolve os filhos ao estado inicial. Assim a cascata recomeça quando o usuário sobe e desce.
- **Guard de FOUC.** O script inline do `<head>` adiciona `js` ao `<html>`, exceto com movimento reduzido. Se o módulo não tiver rodado até o `DOMContentLoaded`, a classe sai. O módulo também remove `js` quando falta o GSAP ou quando o init lança erro. O parágrafo do hero tem o mesmo guard, com `[data-reveal-lede]`.
- **Limpeza.** Tudo nasce num `gsap.context()`. `window.komunikiReveal.destroy()` desliga os observers e reverte SplitText, tweens e ScrollTriggers. O evento `htmx:beforeCleanupElement` num título chama essa limpeza; numa navegação comum, o navegador libera tudo.

## Arquivos

| Arquivo | Papel |
|---|---|
| `static/js/school-editorial-reveal.js` | Módulo único: constantes, blocos com `{ el, mode, reset(), animateIn() }`, hero, grupos, blocos isolados e boot depois das fontes |
| `static/js/vendor/gsap-3.15.0/` | `gsap.min.js`, `ScrollTrigger.min.js` e `SplitText.min.js` do pacote `gsap@3.15.0` |
| `static/css/school-editorial.css` | Guard `.js [data-reveal]`, `.line-wrap`, `.line` e a correção dos acentos; folha em `?v=13` |
| `templates/base_school_editorial.html` | Classe `js` no `<head>` e os quatro scripts com `defer`, depois do Alpine |
| `templates/school/home.html` | Os três exemplos aprovados |
| `apps/school/tests.py` | `test_school_homepage_marks_text_reveal_with_local_gsap` |

## Como marcar

```html
<section data-reveal-hero>                        <!-- dispara no load -->
  <h1 data-reveal="mask">…</h1>
  <p data-reveal-lede>…</p>
</section>
<h2 data-reveal="mask">…</h2>                      <!-- bloco isolado, com ScrollTrigger próprio -->
<div data-reveal-group data-reveal-step="0.2">     <!-- um gatilho só, filhos em cascata -->
  <h3 data-reveal="fade">…</h3>
</div>
```

`mask` é para headlines grandes; `fade`, para títulos menores e blocos em coluna. Cada `[data-reveal]` pertence ao hero ou ao grupo mais próximo. Fora deles, é um bloco isolado com `start: 'top bottom'`, `end: 'top top'`, `onEnter` e `onLeaveBack`. Evite `mask` em título centralizado: o `.line-wrap` usa `width: fit-content` e alinharia as linhas à esquerda.

Exemplos aplicados na Home: o título do hero (`mask`, no load), o título do bloco do prêmio (`mask`, isolado) e os três títulos das trilhas (`fade`, em grupo). A aplicação nos demais títulos espera aprovação.

## Como testar

Na prévia http://127.0.0.1:8013/:

1. Role até o título do prêmio: as três linhas entram com 0,1 s entre si.
2. Suba até ele sair pela base da tela e desça de novo: o reveal recomeça. O mesmo vale para os cards de trilhas, em cascata de 0,2 s.
3. Redimensione a janela devagar: as quebras se refazem cerca de 200 ms depois, e o texto continua visível.
4. Inspecione o título do hero. O `h1` tem `aria-label` com o texto original. Dentro dele há `.line-mask.line-wrap` com `overflow: clip` inline e `.line`, ambos com `aria-hidden="true"`. O `overflow: clip` do SplitText sobrepõe o `overflow: hidden` do CSS, e os dois recortam.
5. Ative "reduzir movimento" no sistema: não há classe `js` nem split, e o texto fica estático.
6. No DevTools, em Network, use Slow 4G com o cache desligado: título e parágrafo ficam invisíveis até o split e então animam, sem piscar.
7. Troque PT/EN: os títulos são refeitos no idioma novo sem perder o estado.

Temporário: `?reveal-markers` na URL mostra os markers de `start` e `end`.

## Validação

Feita em 13/09/2026 na prévia 8013, onde as 36 verificações do roteiro CDP passaram. O roteiro usa o Edge headless e fica em `.preview/evidence/text-reveal/reveal-cdp.mjs`, fora do Git. Com a prévia no ar, `node reveal-cdp.mjs` grava `summary.json`, `fouc-samples.json` e as capturas na mesma pasta.

| Critério | Resultado |
|---|---|
| Cascata entre linhas | Título do prêmio: as linhas partem a 13, 109 e 209 ms |
| Cascata do grupo | Primeiras linhas dos três títulos a 18, 209 e 410 ms, com 0,1 s entre linhas dentro de cada um |
| Reinício | Subir até o bloco sair pela base devolve o estado inicial; descer repete os mesmos intervalos, no bloco e no grupo |
| Salto e recarga | Pular direto ao fim, ou recarregar já rolado, deixa prêmio e trilhas revelados |
| Geometria | Em 1440 e 375 px, posições das linhas, alturas dos títulos, blocos seguintes e altura da página idênticas às do texto estático (diferença ≤ 0,1 px) |
| Acentos | Cedilha e til inteiros no estado final (`premio-acentos-revelado.png`). No estado inicial a captura sai toda preta, sem nenhum traço de letra (`premio-estado-inicial.png`) |
| Resize | 1440 → 1024 → 768 → 375 → 1440 px em inglês: o texto continua em inglês, dividido e revelado, sem rolagem horizontal |
| Idioma | EN refaz hero e prêmio com `aria-label` em inglês, preservando o que estava revelado ou escondido; a volta para PT também funciona |
| Acessibilidade | Na árvore real, os headings têm o nome completo, como "Comunicação que gera resultados", e recortes e linhas são ignorados por `aria-hidden` |
| Movimento reduzido | Sem `js` e sem split; título e parágrafo com opacidade 1 |
| Rede lenta | Slow 4G sem cache: estilo aplicado a 3,9 s, split a 5,1 s e fim a 6,5 s, sem título ou parágrafo visível antes do split |
| Markers | 4 com `?reveal-markers` (dois gatilhos × start/end) e nenhum sem o parâmetro |
| Cards | Em `fade` dentro de `.ed-card`, que tem `overflow: hidden`, o `x: -50` passa do padding de 24 px, e o começo da linha aparece cortado enquanto ela ainda está esmaecida (`trilhas-cascata-meio.png`). É o deslocamento da spec; convém considerar isso ao aplicar em outros cards |
| Console | Nenhuma mensagem do reveal. Continuam os avisos preexistentes do Tailwind CDN, o 404 de `/favicon.ico` e o bloqueio de armazenamento do Turnstile no Edge |
| Estáticos de produção | O `collectstatic` com `CompressedManifestStaticFilesStorage` passou: módulo, GSAP e CSS saíram com hash e `.gz`, e nenhum source map é referenciado |
| Testes | 468 testes do pytest (com as variáveis `SECRET_KEY` e `DB_*` que o CI define) e o Ruff passaram |

Limites: Chromium (Edge), em pixels CSS, sem aparelhos físicos, Safari ou Firefox. O movimento reduzido e a rede lenta foram emulados pelo CDP. O roteiro `scripts/preview/presentation_e2e.mjs`, do Codex, não foi executado. Em duas execuções o Edge headless deixou de entregar quadros de `requestAnimationFrame` e os tweens pararam no quadro 0; isso coincidiu com a abertura da mesma página no navegador do Claude Code. Repetida com os quadros normais, a verificação passou inteira. Se a trava voltar, o roteiro aborta sozinho em 300 s.

## Reversão

- **Tirar só os exemplos:** apagar os atributos `data-reveal*` de `templates/school/home.html`. Sem elementos marcados, o módulo não faz nada.
- **Tirar o sistema:** remover os quatro `<script>` e o guard do `<head>` em `base_school_editorial.html`, o bloco "Line-by-line text reveal" de `school-editorial.css` (subindo a versão da folha), o teste novo e, se quiser, `static/js/school-editorial-reveal.js` e `static/js/vendor/gsap-3.15.0/`.
- **Atualizar o GSAP:** criar outra pasta `gsap-X.Y.Z` e trocar os caminhos no base. Não sobrescrever arquivos de uma pasta já publicada.
