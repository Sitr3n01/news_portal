# Sublinhado animado da Komuniki

Implementado em 14/09/2026 na worktree `news_portal-komuniki-design`, branch `codex/komuniki-editorial-test`, a pedido do usuário: todo texto que aparecia sublinhado ao interagir ganha uma animação de underline reveal. É a terceira exceção à regra de nenhum movimento, ao lado do [hero de partículas](komuniki-particles.md) e do [reveal de texto](komuniki-text-reveal.md).

## Comportamento

- Ao passar o mouse, ou ao focar pelo teclado (`:focus-visible`), um traço cresce da esquerda para a direita em 0,45 s, com `cubic-bezier(.25,1,.5,1)`, o equivalente CSS do `power3.out` usado no reveal. Ao sair, o traço recolhe em direção à direita com a mesma curva.
- O traço completo ocupa o mesmo lugar e tem a mesma espessura do sublinhado instantâneo que existia antes. O deslocamento continua `text-underline-offset` de 4 px (5 px na navbar), e a espessura é a automática do Chromium: `floor(tamanho da fonte / 10)`, com mínimo de 1 px.
- O link da página atual na navbar fica com o traço inteiro, sem animação.
- Com `prefers-reduced-motion: reduce` não há transição: o traço aparece e some de uma vez, como antes.
- Links sem o gancho (texto corrido do CMS e links futuros) continuam com o sublinhado instantâneo. O sublinhado fixo do texto corrido e dos erros do formulário não muda.

## Onde

| Lugar | Elemento | Gancho |
|---|---|---|
| Navbar | quatro links | `.ed-underline` no próprio link |
| Navbar | marca em texto | `.ed-underline` no link, só quando não há logo |
| Navbar | menu móvel | `<span class="ed-underline">` dentro do link, que tem padding e ocupa a linha inteira |
| Todas as páginas | "Ir para o conteúdo" | span interno |
| Rodapé | seis links | `.ed-underline` no link; nas páginas com reveal, o `data-reveal` passou do link para o `<li>` |
| Rodapé | nome da marca | `.ed-underline` no span `ed-footer-brand` |
| Rodapé e Contato | e-mails | `<span class="ed-underline-text">`, porque o e-mail quebra linha |
| Privacidade | botão "Falar com a Komuniki" | span interno; é um link sem `.ed-button`, que já sublinhava |
| Página genérica do CMS | "Voltar para a Komuniki" | `.ed-underline` no span existente |
| Feed social da Home | cards | rótulo da rede, data e "Ver publicação" com `.ed-underline`, legenda com `.ed-underline-text`; o card deixa de sublinhar o texto todo de uma vez |

Não entram os botões `.ed-button`, os cards de trilhas (já sem sublinhado) e os links só com ícone.

## Como funciona

- **`.ed-underline`, para uma linha.** Um `::after` absoluto com `transform: scaleX`, de 0 a 1. O `transform-origin` fica à esquerda ao entrar e à direita ao sair. O elemento precisa envolver o texto de forma justa, sem padding, por isso os links com padding ganharam um span interno.
- **Posição do traço.** `top = floor((altura da caixa − A − D) / 2) + A + deslocamento`. A e D são o ascendente e o descendente arredondados como o Blink faz: `round(.96875em)` e `round(.2412em)` na Inter, `round(1em)` e `round(.2em)` na Barlow Condensed. Numa caixa inline a meia-entrelinha é zero. Numa caixa de linha, como item flex ou bloco, o Blink arredonda a meia-entrelinha para baixo, e a fórmula faz o mesmo. A espessura é `max(1px, round(down, .1em, 1px))`.
- **`.ed-underline-text`, para texto que quebra.** Um gradiente de fundo com `background-size` indo de 0 a 100% na base da caixa inline. Ele percorre a primeira linha e depois a segunda. Um `padding-bottom`, que numa caixa inline não altera o layout, leva o fundo até onde o sublinhado ficava.
- **Transições.** A regra global que zera `transition` continua valendo. Os dois ganchos declaram a própria transição com `!important` e especificidade maior.
- **Gatilho.** `:hover` e `:focus-visible` no link, seja o link com o gancho (`a.ed-underline`), seja o gancho dentro dele (`a:hover .ed-underline`).
- **Só CSS.** Não depende do GSAP nem de JavaScript.

## Arquivos

| Arquivo | Papel |
|---|---|
| `static/css/school-editorial.css` | Regras `.ed-underline` e `.ed-underline-text`, traço fixo da página atual, sublinhado instantâneo restrito aos links sem gancho; folha em `?v=16` |
| `templates/school/editorial/navbar.html` | Ganchos nos links e na marca; spans do menu móvel |
| `templates/base_school_editorial.html` | Span do link de pular e versão da folha |
| `templates/school/editorial/footer.html` | Ganchos nos links, na marca e no e-mail; reveal dos links no `<li>` |
| `templates/contact/contact_page.html`, `templates/school/privacy.html`, `templates/school/page_detail.html`, `templates/school/editorial/social_post_card.html` | Spans e ganchos |
| `apps/school/tests.py` | Ganchos em Início, Sobre, Contato e Privacidade, e reveal do rodapé no `<li>` |

## Como testar

Na prévia http://127.0.0.1:8013/, ou na 8012 depois de reiniciá-la:

1. Passe o mouse num link da navbar: o traço cresce da esquerda. Tire o mouse: ele sai pela direita.
2. Pressione Tab no topo de uma página: "Ir para o conteúdo" aparece com o traço. Tab de novo leva à marca, e o traço acompanha o foco.
3. A 375 px, abra o menu e passe o mouse num item: o traço tem a largura da palavra, não da linha.
4. No rodapé, passe o mouse no e-mail: quando ele quebra linha, o traço percorre a primeira linha e depois a segunda.
5. Ative "reduzir movimento": o traço aparece e some sem animação.

## Validação

Feita em 14/09/2026 no Edge headless via CDP, contra uma referência medida na versão commitada (`10cb822`) antes de qualquer mudança. Os roteiros e as capturas estão em `.preview/evidence/underline-reveal/`, fora do Git.

| Critério | Resultado |
|---|---|
| Layout | Posições de todo o texto do `body`, caixas de todos os links e altura da página idênticas às da referência em Início, Sobre, Cursos, Contato e Privacidade, a 1440 e 375 px |
| Sublinhado dobrado | Nenhum dos 13 elementos amostrados usa mais `text-decoration` no hover |
| Pixel a pixel | Nas 13 amostras, em 1x e 2x, o traço completo ocupa as mesmas linhas de pixel e tem a mesma espessura do sublinhado antigo. A diferença é só o pixel suavizado da ponta esquerda, onde o sublinhado antigo começava numa fração de pixel: de 1 a 12 pixels por captura (12 no "KOMUNIKI", que tem 6 linhas de espessura). No estado parado não há diferença, exceto nas pontas do traço fixo de "Início" (`pixel-counts.txt`) |
| Posição e espessura | Valores calculados iguais aos do sublinhado antigo: marca 33 px e 2 px, botão de Privacidade 19 px e 1 px, "KOMUNIKI" 58 px e 6 px, links do rodapé e de pular 20 px e 1 px, e-mail com `padding-bottom` de 2 px |
| Mouse de verdade | O traço cresce a partir da esquerda e completa em até 0,6 s; ao sair, recolhe em direção à direita |
| Teclado | O foco visível revela o traço no link de pular e na marca, e ele some quando o foco sai |
| Página atual | "Início" com o traço inteiro parado; em Contato, que não está na navbar, nenhum traço fixo |
| Menu móvel | Traço com a largura da palavra, não da linha do menu |
| E-mail que quebra | Fundo animado chega a 100% no hover e percorre as duas linhas |
| Idioma | Em inglês, textos com `x-text` corretos, links do rodapé dentro das linhas refeitas pelo reveal e traço funcionando |
| Movimento reduzido | Traço e fundo sem transição |
| Quadros no meio | Transição congelada a 110 ms na entrada e na saída em cinco lugares, com uma única transição por traço |
| Reveal de texto | As 38 verificações de `reveal-all.mjs` passaram com o reveal dos links do rodapé no `<li>`. A regressão também revelou um bug do reveal da rodada anterior, sem relação com o sublinhado: depois de estreitar a janela, o rodapé podia ficar escondido. O bug foi corrigido; veja [a validação do reveal](komuniki-text-reveal.md#validação) |
| Testes | 476 testes do pytest, o Ruff e o `collectstatic` com `CompressedManifestStaticFilesStorage` passaram |

## Reversão

- **Tirar a animação:** remover o bloco "Underline reveal" de `school-editorial.css`, voltar a regra geral para `.ed-school a:not(.ed-button):hover{text-decoration:underline;text-underline-offset:4px}` e devolver o `text-decoration:underline;text-underline-offset:5px` ao hover e à página atual da navbar. Depois, subir a versão da folha.
- Os spans e as classes nos templates não fazem nada sem o CSS e podem ficar. Se forem removidos, o `data-reveal` dos links do rodapé deve voltar do `<li>` para o link, e o `x-text` dos spans internos deve voltar para o link.
