# Reveal de texto por linha da Komuniki

Implementado em 13/09/2026 na worktree `news_portal-komuniki-design`, branch `codex/komuniki-editorial-test`, a partir de uma especificação fechada do usuário: GSAP SplitText + ScrollTrigger, dois modos (`mask` e `fade`) e valores fixos. A primeira rodada cobriu três exemplos na Home (commit `34f0619`). Na segunda, o reveal passou a valer para todo o texto de Início, Sobre e Cursos, inclusive o rodapé dessas páginas. A navbar, Contato, Privacidade e as demais páginas do CMS continuam estáticas. É a segunda exceção à regra de nenhum movimento, ao lado do [hero de partículas](komuniki-particles.md).

## Decisões

- **Valores da spec, sem ajuste.** Cada linha dura 0,9 s, com `power3.out` e 0,1 s entre linhas; blocos de um grupo ficam 0,2 s um do outro. No `mask`, a linha vai de `x -50` a 0 e de `yPercent 100` a 0 dentro de um recorte. No `fade`, vai de `x -50` a 0 e de `opacity 0` a 1. O hero dispara 0,15 s depois do boot, e o parágrafo entra em `start+=0.5`, em 0,8 s, `power2.out`.
- **GSAP 3.15.0 vendorizado.** O projeto não tem npm nem bundler, e a CSP bloqueia CDN. Em 13/09/2026, `^3.13.0` resolvia para 3.15.0. Os três builds UMD vieram do tarball do npm, com a integridade sha512 conferida (`sha512-dMW4CWBT…jfZB+A==`). A licença é a "Standard no-charge" da GSAP: gratuita, inclusive para uso comercial, mas não é MIT.
- **Onde entra.** Os scripts carregam em `base_school_editorial.html`. Os atributos ficam nos templates de Início, Sobre e Cursos, e no rodapé só quando a página o inclui com `reveal=True`, pelo `{% block footer %}`. Vagas, Equipe e Blog mantêm as animações próprias. A regra CSS que zera `animation` e `transition` continua, porque o GSAP escreve estilo inline e não depende dela.
- **Modos.** `mask` vai no h1 e nos h2 de seção alinhados à esquerda. Todo o resto usa `fade`: títulos de card, parágrafos, rótulos, etiquetas, itens de lista, `dt`/`dd`, texto de botão e rodapé. O título centralizado da chamada final de Sobre também usa `fade`, porque o `.line-wrap` com `width: fit-content` alinharia as linhas à esquerda.
- **O que recebe o atributo.** Sempre o elemento que contém o texto, nunca um contêiner flex ou grid, cujas palavras virariam itens do layout.
  - Botões e pílulas ganham um span interno: a caixa fica visível e só o rótulo anima.
  - E-mail e telefone do rodapé, que são inline e o e-mail tem destaque azul, ganham um span em bloco em volta.
  - Os links de navegação do rodapé recebem o `data-reveal` no `<li>`: o link continua inline dentro da linha, e o [sublinhado animado](komuniki-underline-reveal.md) se apoia nele.
  - O copyright virou um `x-text` único no parágrafo. Um filho com `x-text` que quebrasse de linha seria clonado pelo SplitText e reinicializado pelo Alpine.
  - Ficam sem reveal: a legenda do post social, cujo `-webkit-line-clamp` as linhas em bloco quebrariam, e os ícones, marcadores e caixas.
- **Cascatas.**
  - No hero, os textos extras usam `data-reveal-at`: legenda da arte em 0,1, botões em 0,7 e 0,9, "Explore a Komuniki" em 1,1.
  - Cada coluna, card ou introdução de seção é um `data-reveal-group`.
  - Grupos irmãos na mesma fileira começam com 0,2 s entre si, o que faz a onda dos cards. Empilhados, no celular, cada um começa ao entrar.
  - Os cards de curso, densos, usam `data-reveal-step="0.1"`.
  - Ao subir até o grupo sair pela base da tela, ele volta a esconder, e a próxima entrada recomeça a cascata.
- **Acentos no `mask`.** Com o `line-height` de 0,9 da Barlow, til e agudo passam 0,05 em acima da caixa da linha, e a cedilha, 0,133 em abaixo. A correção:
  - a linha ganha `padding-block: .15em`;
  - o recorte volta ao lugar com `top: -.15em`, `margin-bottom: -.3em` (margens negativas entre irmãos colapsariam) e `margin-right: -.12em`, que devolve o `padding-right` da spec;
  - o título vira `flow-root`.

  A geometria final é idêntica. Como `yPercent: 100` é relativo à linha, agora mais alta, a subida percorre 1,2 em. O nome no rodapé fica dentro de um `inline-flex`, onde o padding mudaria a linha de base; "KOMUNIKI" não tem acento, então usa `fade`.
- **`.line` sem `nowrap`.** A spec pede `white-space: nowrap`. Uma palavra que o layout quebra no meio, como "PROFISSIONALIZANTE" a 375 px ou o e-mail, sai do SplitText como uma linha só. Com `nowrap` ela transbordaria e mudaria a altura da página. Sem `nowrap`, as linhas continuam sendo as que o SplitText mediu, mas podem quebrar dentro de si.
- **Acessibilidade.** Títulos mantêm `aria: "auto"`, como na spec: `aria-label` com o texto e linhas `aria-hidden`. Parágrafo, item de lista e span não aceitam `aria-label`, e o leitor de tela ficaria mudo. Neles o módulo usa `aria: "none"`, e o texto das linhas continua na árvore de acessibilidade.
- **PT/EN pelo Alpine.** O `x-text` reescreve o texto e apaga as linhas. O módulo desfaz recortes e linhas movendo os nós vivos de volta e divide o texto novo mantendo o estado (revelado continua revelado). Não restaura o HTML guardado pelo SplitText, que traria o idioma anterior. A instância antiga é aposentada com `isSplit = false`, para que um resize já agendado nela não restaure o idioma anterior. A mudança de `lang` chama `ScrollTrigger.refresh()`.
- **Resize.** O `autoSplit` observa a largura do próprio elemento. Texto em flex, pílula ou link inline não muda de largura quando a viewport encolhe, e as linhas ficariam largas demais. Quando a largura da viewport muda, todos os blocos são redivididos. Todo split refeito, seja por largura, webfont ou idioma, agenda um único `ScrollTrigger.refresh()` 100 ms depois do último. Sem isso, o refresh do próprio resize podia medir a página antes dos novos splits, com as linhas antigas ainda quebrando e a página mais alta. O start do último grupo passava do scroll máximo, e o rodapé ficava escondido depois de estreitar a janela (corrigido em 14/09/2026).
- **Estado final e texto pré-formatado.** Depois de um re-split, `progress(1)` é reforçado num microtask, porque o SplitText aplicaria o tempo do tween anterior. Com `white-space: pre*`, como no endereço, as quebras viram `<br>` em vez de espaço.
- **Primeira pintura.** O tempo do GSAP fica parado enquanto o módulo divide o texto e cria os gatilhos, e só volta a andar um quadro depois da primeira pintura da página, com teto de 1 s para aba oculta. Assim nenhuma animação de entrada começa antes de a página aparecer. A pausa veio de um relato de 14/09/2026: o título de Cursos aparecia parado ao abrir a página. O sintoma não se reproduziu no Edge headless nem no navegador do app, com cache, com a CPU 4× e 6× mais lenta e de 750 a 1920 px. O título animava inteiro depois da pintura, e no pior caso começava 5% adiantado; com a pausa, 0%. Com ela, as 38 verificações de `reveal-all.mjs` passaram. As medições estão em `.preview/evidence/botoes-e-cursos-2026-09-14/primeira-pintura.txt`.
- **Guard de FOUC e limpeza.** O `<head>` adiciona `js` ao `<html>`, exceto com movimento reduzido, e a remove no `DOMContentLoaded` se o módulo não tiver rodado. O módulo também a remove quando falta GSAP ou quando o init falha. `window.komunikiReveal.destroy()` desliga observers e listeners e reverte SplitText, tweens e ScrollTriggers.

## Arquivos

| Arquivo | Papel |
|---|---|
| `static/js/school-editorial-reveal.js` | Módulo único: blocos `{ el, mode, reset(), animateIn() }`, hero, grupos, blocos isolados, troca de idioma, resize e refresh depois de split refeito |
| `static/js/vendor/gsap-3.15.0/` | `gsap.min.js`, `ScrollTrigger.min.js` e `SplitText.min.js` do pacote `gsap@3.15.0` |
| `static/css/school-editorial.css` | Guard `.js [data-reveal]`, `.line-wrap`, `.line` e a correção dos acentos; folha em `?v=18` |
| `templates/base_school_editorial.html` | Classe `js` no `<head>`, os quatro scripts com `defer` (módulo em `?v=3`) e o `{% block footer %}` |
| `templates/school/home.html`, `about.html`, `page_detail.html` | Atributos em todo o texto; `page_detail` só no ramo de Cursos |
| `templates/school/editorial/footer.html` | Atributos condicionados a `reveal` |
| `templates/school/editorial/social_feed.html`, `social_post_card.html` | Feed social da Home, quando ativo |
| `apps/school/tests.py` | Reveal nas três páginas, navbar sem marcação e Contato, Privacidade e outras páginas do CMS estáticas |

## Como marcar

```html
<section data-reveal-hero>                          <!-- dispara no load -->
  <h1 data-reveal="mask">…</h1>
  <p data-reveal-lede>…</p>
  <a class="ed-button"><span data-reveal="fade" data-reveal-at="0.7">…</span></a>
</section>
<div class="grid">
  <article data-reveal-group>                         <!-- cards lado a lado entram em onda -->
    <h3 data-reveal="fade">…</h3>
    <p data-reveal="fade">…</p>
  </article>
</div>
<p data-reveal="fade">…</p>                           <!-- fora de hero e grupo: bloco isolado -->
```

## Como testar

Na prévia http://127.0.0.1:8013/, ou na 8012 depois de reiniciá-la, porque ela roda com `--noreload`:

1. Role pelas três páginas: cada bloco entra quando chega à tela, com as linhas 0,1 s uma da outra. Os cards lado a lado entram em onda.
2. Suba até uma seção sair pela base da tela e desça de novo: a cascata recomeça.
3. Redimensione a janela devagar: as quebras se refazem e nada transborda. Depois de estreitar, role até o fim da página: o rodapé aparece.
4. Inspecione o h1: `aria-label` com o texto, `.line-mask.line-wrap` com `overflow: clip` inline e `.line` dentro. Um parágrafo tem as linhas sem `aria-hidden`.
5. Ative "reduzir movimento" no sistema: não há classe `js`, split nem animação.
6. No DevTools, use Slow 4G com o cache desligado: nenhum texto aparece antes de animar.
7. Troque PT/EN nas três páginas, também depois de redimensionar: o texto troca e continua visível.

Temporário: `?reveal-markers` na URL mostra os markers de `start` e `end`.

## Validação

Feita em 13/09/2026: 38 verificações passaram no Edge headless via CDP. Os roteiros `reveal-all.mjs` e `cdp-lib.mjs`, o `summary.json` e as capturas estão em `.preview/evidence/text-reveal-all/`, fora do Git. A primeira rodada, com os três exemplos, está em `.preview/evidence/text-reveal/`.

| Critério | Resultado |
|---|---|
| Marcação nova x anterior | Com movimento reduzido, todo o texto de `main` e `footer` fica nas mesmas posições que na versão commitada (8012), em Início, Sobre e Cursos, a 1440 e 375 px |
| Load | 70, 44 e 96 blocos divididos; nada visível antes da hora; navbar sem marcação; nenhum `x-text` aninhado |
| Depois de rolar | Todos os blocos revelados; texto e altura da página idênticos ao estático (diferença ≤ 1 px); nenhuma linha transbordando e nenhuma rolagem horizontal |
| Cascatas | Trilhas da Início em onda, com 0,2 s entre cards e entre os textos de cada card; reinício ao subir e descer; card de curso com 0,1 s |
| Idioma | Cada bloco confere com o `x-text` calculado pelo Alpine em PT, em EN, em EN a 375 px e de volta em PT; nenhum `aria-label` desatualizado |
| Acessibilidade | O h1 tem o nome inteiro e linhas ocultas; as linhas de parágrafo, o botão e o link do rodapé são legíveis |
| Fora do pedido | Contato e Privacidade sem reveal e sem texto escondido |
| Rede lenta | Slow 4G sem cache: estilo aplicado a 3,9 s e todos os blocos divididos a 5,1 s, nenhum visível antes |
| Markers | Presentes com `?reveal-markers` |
| Console | Nenhuma mensagem do reveal. Continuam o 404 de `/favicon.ico` e os avisos preexistentes do Tailwind CDN e do Turnstile |
| Estáticos de produção | O `collectstatic` com `CompressedManifestStaticFilesStorage` passou |
| Testes | 472 testes do pytest (com as variáveis `SECRET_KEY` e `DB_*` do CI) e o Ruff passaram |

Limites e observações:

- Chromium (Edge), em pixels CSS, sem aparelhos físicos, Safari ou Firefox. Movimento reduzido e rede lenta foram emulados pelo CDP.
- O feed social e os depoimentos não existem no banco local e não foram exercitados no navegador.
- **Corte durante a entrada:** dentro de caixas com `overflow: hidden` e pouco padding (cards e o painel dos grupos de Cursos), o `x: -50` da spec corta o começo da linha enquanto ela entra. O corte some quando a linha chega (`cursos-grupo-meio.png`). Mantido assim a pedido do usuário em 13/09/2026.
- **Quadros congelados no teste:** em algumas execuções o Edge headless parou de entregar quadros de `requestAnimationFrame`. O `cdp-lib.mjs` empurra o ticker do GSAP quando isso acontece e registra quantas vezes; na rodada válida o contador ficou em zero.

### Correção de 14/09/2026: rodapé escondido depois de estreitar a janela

A regressão da rodada do sublinhado encontrou, em algumas execuções, o último grupo do rodapé (copyright e frase) parado no estado inicial depois de a janela ir de 1440 para 375 px. O registro mostrou a causa na Início:
- o ScrollTrigger mediu a página no resize, quando ela ainda tinha 7306 px de altura, com as linhas de 1440 px quebrando;
- os novos splits deixaram a página com 6972 px, mas nada mediu de novo;
- o start do grupo (6337) ficou além do scroll máximo (6160), e o grupo nunca entrava.

O bug é do módulo de reveal e não tem relação com o sublinhado. Agora todo split refeito agenda um `ScrollTrigger.refresh()` (veja "Resize" em Decisões), e o módulo foi para `?v=2`.

| Teste | Antes | Depois |
|---|---|---|
| Ordem forçada: na página, os debounces de 200 ms passam a 600 ms, como num aparelho lento; Início e Sobre, com e sem troca de idioma, duas rodadas | Rodapé escondido em 6 de 8 | 0 de 8 |
| Regressão completa (`reveal-all.mjs`) | Rodapé escondido em 2 de 3 páginas numa execução e em 1 de 3 na seguinte | 38 de 38 |

O roteiro passou a procurar o link do rodapé em `li[data-reveal] a`, porque o reveal desses links foi para o `<li>`. Roteiros, registros e resultados estão em `.preview/evidence/text-reveal-resize-fix/`. Também passaram 476 testes do pytest, o Ruff e o `collectstatic` com manifest.

## Reversão

- **Tirar o reveal de uma página:** apagar os atributos `data-reveal*` do template dela e o `{% block footer %}` que passa `reveal=True`.
- **Tirar o sistema:** remover os quatro `<script>` e o guard do `<head>` em `base_school_editorial.html`, o bloco "Line-by-line text reveal" de `school-editorial.css` (subindo a versão da folha) e os testes do reveal. Se quiser, apague também `static/js/school-editorial-reveal.js` e `static/js/vendor/gsap-3.15.0/`. Sem atributos, os spans internos dos botões e das etiquetas não mudam nada no visual.
- **Atualizar o GSAP:** criar outra pasta `gsap-X.Y.Z` e trocar os caminhos no base. Não sobrescrever arquivos de uma pasta já publicada.
