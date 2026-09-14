# Sublinhado animado da Komuniki

Implementado em 14/09/2026 na worktree `news_portal-komuniki-design`, branch `codex/komuniki-editorial-test`, a pedido do usuário: todo texto que aparecia sublinhado ao interagir ganha uma animação de underline reveal. É a terceira exceção à regra de nenhum movimento, ao lado do [hero de partículas](komuniki-particles.md) e do [reveal de texto](komuniki-text-reveal.md). No mesmo dia vieram o traço nos títulos dos cards e um leve crescimento ao interagir, a quarta exceção. Ele vale para os cards de trilhas da Início, os cards de curso e os botões "Conte-nos mais", "Conheça os cursos" e "Fale com a Komuniki".

## Comportamento

- Ao passar o mouse, ou ao focar pelo teclado (`:focus-visible`), um traço cresce da esquerda para a direita em 0,45 s, com `cubic-bezier(.25,1,.5,1)`, o equivalente CSS do `power3.out` usado no reveal. Ao sair, o traço recolhe em direção à direita com a mesma curva.
- O traço completo ocupa o mesmo lugar e tem a mesma espessura do sublinhado instantâneo que existia antes. O deslocamento continua `text-underline-offset` de 4 px (5 px na navbar), e a espessura é a automática do Chromium: `floor(tamanho da fonte / 10)`, com mínimo de 1 px.
- O link da página atual na navbar fica com o traço inteiro, sem animação.
- Com `prefers-reduced-motion: reduce` não há transição: o traço aparece e some de uma vez, como antes.
- Links sem o gancho (texto corrido do CMS e links futuros) continuam com o sublinhado instantâneo. O sublinhado fixo do texto corrido e dos erros do formulário não muda.
- **Crescimento ao interagir (`.ed-grow`).** Ao passar o mouse ou focar pelo teclado, o elemento cresce para `scale(1.02)` na mesma curva de 0,45 s. Vale para:
  - os cards de trilhas da Início. O fundo claro do hover continua instantâneo, e o título e "Ver cursos" revelam o traço;
  - os seis cards de curso de Cursos. Cada card inteiro é um link para Contato, e o título revela o traço;
  - os botões "Conte-nos mais", "Conheça os cursos" e "Fale com a Komuniki" em todas as páginas, inclusive a navbar, o menu móvel e o rodapé.

  Os títulos dos cards quebram em várias linhas, e cada linha ganha o próprio traço, todos ao mesmo tempo. Os outros botões ("Ver cursos" e "Ir para notícias" em Cursos, "Enviar mensagem" em Contato e o botão do feed social) não crescem. Com movimento reduzido, o crescimento acontece sem transição, e os títulos, que nesse caso não são divididos em linhas, usam o sublinhado instantâneo do navegador.

## Onde

| Lugar | Elemento | Gancho |
|---|---|---|
| Navbar | quatro links | `.ed-underline` no próprio link |
| Navbar | marca em texto | `.ed-underline` no link, só quando não há logo |
| Navbar | menu móvel | `<span class="ed-underline">` dentro do link, que tem padding e ocupa a linha inteira |
| Todas as páginas | "Ir para o conteúdo" | span interno |
| Início | título dos cards de trilhas | `.ed-underline-lines` no `h3`: um traço por linha do reveal |
| Início | "Ver cursos" dos cards de trilhas | `.ed-underline` no span |
| Cursos | título dos cards de curso | `.ed-underline-lines` no `h3`; o card é um `<a>` para Contato com `.ed-grow` |
| Rodapé | seis links | `.ed-underline` no link; nas páginas com reveal, o `data-reveal` passou do link para o `<li>` |
| Rodapé | nome da marca | `.ed-underline` no span `ed-footer-brand` |
| Rodapé e Contato | e-mails | `<span class="ed-underline-text">`. O do rodapé fica numa linha só; o de Contato quebra linha quando falta espaço |
| Privacidade | botão "Falar com a Komuniki" | span interno; é um link sem `.ed-button`, que já sublinhava |
| Página genérica do CMS | "Voltar para a Komuniki" | `.ed-underline` no span existente |
| Feed social da Home | cards | rótulo da rede, data e "Ver publicação" com `.ed-underline`, legenda com `.ed-underline-text`; o card deixa de sublinhar o texto todo de uma vez |

Não entram os botões `.ed-button` e os links só com ícone.

## Como funciona

- **`.ed-underline`, para uma linha.** Um `::after` absoluto com `transform: scaleX`, de 0 a 1. O `transform-origin` fica à esquerda ao entrar e à direita ao sair. O elemento precisa envolver o texto de forma justa, sem padding, por isso os links com padding ganharam um span interno.
- **Posição do traço.** `top = floor((altura da caixa − A − D) / 2) + A + deslocamento`. A e D são o ascendente e o descendente arredondados como o Blink faz:
  - Inter: `round(.96875em)` e `round(.2412em)`;
  - Barlow Condensed: `round(1em)` e `round(.2em)`;
  - IBM Plex Mono: `round(1.025em)` e `round(.275em)`.

  Numa caixa inline a meia-entrelinha é zero. Numa caixa de linha, como item flex ou bloco, o Blink arredonda a meia-entrelinha para baixo, e a fórmula faz o mesmo. A espessura é `max(1px, round(down, .1em, 1px))`.
- **`.ed-underline-text`, para texto que quebra.** Um gradiente de fundo com `background-size` indo de 0 a 100% na base da caixa inline. Ele percorre a primeira linha e depois a segunda. Um `padding-bottom`, que numa caixa inline não altera o layout, leva o fundo até onde o sublinhado ficava.
- **`.ed-underline-lines`, para título dividido pelo reveal.** O reveal (`fade`) transforma o título em `.line`. Cada `.line` encolhe até o texto com `width: fit-content` e recebe o mesmo `::after` de `.ed-underline`. Sem split, com movimento reduzido ou sem JavaScript, o título usa `text-decoration: underline` com o mesmo deslocamento. O traço passa por cima de descendentes como a cedilha de "Ç", que o sublinhado do navegador contornaria. Um link que contém o gancho fica fora do sublinhado instantâneo geral, senão todo o texto do card sublinharia.
- **`.ed-grow`.** `transform: scale(1.02)` no `:hover` e no `:focus-visible` do link.
- **Transições.** A regra global que zera `transition` continua valendo. Os ganchos e `.ed-grow` declaram a própria transição com `!important` e especificidade maior, e a zeram de novo com movimento reduzido.
- **Gatilho.** `:hover` e `:focus-visible` no link, seja o link com o gancho (`a.ed-underline`), seja o gancho dentro dele (`a:hover .ed-underline`).
- **Só CSS.** Não depende do GSAP nem de JavaScript; o reveal só fornece as linhas dos títulos.

## Arquivos

| Arquivo | Papel |
|---|---|
| `static/css/school-editorial.css` | Regras `.ed-underline`, `.ed-underline-text`, `.ed-underline-lines` e `.ed-grow`, traço fixo da página atual e sublinhado instantâneo restrito aos links sem gancho; folha em `?v=18` |
| `templates/school/editorial/navbar.html` | Ganchos nos links e na marca; spans do menu móvel; `.ed-grow` no "Fale com a Komuniki" da navbar e do menu móvel |
| `templates/base_school_editorial.html` | Span do link de pular e versão da folha |
| `templates/school/home.html` | Ganchos no título e em "Ver cursos" dos cards de trilhas; `.ed-grow` nos cards e nos quatro botões |
| `templates/school/page_detail.html` | Cards de curso como links para Contato com `.ed-grow` e título com `.ed-underline-lines`; `.ed-grow` em "Fale com a Komuniki" e nos "Conte-nos mais" |
| `templates/school/about.html` | `.ed-grow` em "Conte-nos mais" |
| `templates/school/editorial/footer.html` | Ganchos nos links, na marca e no e-mail; reveal dos links no `<li>`; `.ed-grow` em "Conte-nos mais" |
| `templates/contact/contact_page.html`, `templates/school/privacy.html`, `templates/school/editorial/social_post_card.html` | Spans e ganchos |
| `apps/school/tests.py` | Ganchos em Início, Sobre, Contato e Privacidade, nos cards de trilhas e de curso e nos botões que crescem, reveal do rodapé no `<li>` e coluna Contato do rodapé |

## Como testar

Na prévia http://127.0.0.1:8013/, ou na 8012 depois de reiniciá-la:

1. Passe o mouse num link da navbar: o traço cresce da esquerda. Tire o mouse: ele sai pela direita.
2. Pressione Tab no topo de uma página: "Ir para o conteúdo" aparece com o traço. Tab de novo leva à marca, e o traço acompanha o foco.
3. A 375 px, abra o menu e passe o mouse num item: o traço tem a largura da palavra, não da linha.
4. No rodapé, passe o mouse no e-mail: ele fica numa linha e o traço o percorre. Em Contato, a 375 px, o e-mail quebra linha e o traço percorre a primeira linha e depois a segunda.
5. Na Início, passe o mouse num card de trilha e nos botões do hero: eles crescem de leve, e cada linha do título do card e "Ver cursos" ganham o traço. Tab entre os cards faz o mesmo.
6. Em Cursos, passe o mouse num card de curso: ele cresce e o título ganha o traço; o clique abre Contato. "Ver cursos", ao lado de "Fale com a Komuniki", não cresce.
7. Ative "reduzir movimento": o traço aparece e some sem animação, e cards e botões crescem sem transição.

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

### Cards de trilhas e refinamentos de 14/09/2026

Referência medida no commit `3c81fdc`, antes das mudanças. Roteiros e capturas estão em `.preview/evidence/refinamentos-2026-09-14/`.

| Critério | Resultado |
|---|---|
| Layout | Com movimento reduzido, ficaram idênticos todo o texto fora do rodapé e as caixas dos cards e do bloco de reconhecimento. A comparação cobriu a Início de 375 a 1920 px e Sobre, Cursos, Contato e Privacidade a 375, 1024 e 1440 px |
| Mouse | O card cresce para 1,02, e cada linha do título e "Ver cursos" revelam o traço a partir da esquerda. Ao sair, o card volta e os traços recolhem para a direita. Congeladas a 110 ms, a entrada e a saída mostram uma transição no card e uma por traço |
| Teclado | Tab chega ao card com `:focus-visible`, que cresce e revela os traços |
| Pixel a pixel | Com o card sem escala, o traço de cada linha do título ocupa as mesmas linhas de pixel do `text-decoration` do navegador (3 px, fonte de 32 px), e o de "Ver cursos" também (1 px). Só difere o pixel suavizado da ponta esquerda |
| Movimento reduzido | Card e traço sem transição; título sem split com o sublinhado instantâneo; nada sublinhado sem interação |
| Idioma e 375 px | Em inglês e a 375 px, as linhas são refeitas com um traço por linha, e o card crescido não cria rolagem horizontal |
| E-mail do rodapé | Uma linha em todas as larguras, em PT e EN, dentro da coluna Contato e sem rolagem horizontal. As colunas Komuniki e Atendimento mantêm uma linha por link |
| Reveal de texto | As 38 verificações de `reveal-all.mjs` voltaram a passar, inclusive a onda dos cards de trilhas |
| Testes | 476 testes do pytest, o Ruff e o `collectstatic` com manifest passaram |

### Botões e cards de curso de 14/09/2026

Referência medida no commit `1604fc6`, antes das mudanças. Roteiros e capturas estão em `.preview/evidence/botoes-e-cursos-2026-09-14/`.

| Critério | Resultado |
|---|---|
| Layout | Com movimento reduzido, todo o texto das cinco páginas ficou na mesma posição, com a mesma altura de página, mesmo com os cards de curso trocando `<article>` por `<a>` |
| Mouse | Crescem para 1,02 e voltam a 1: na Início, navbar, os dois botões do hero, os três cards de trilhas, os dois botões do painel final e o do rodapé; em Sobre, "Conte-nos mais", navbar e rodapé; em Cursos, "Fale com a Komuniki", "Conte-nos mais", os seis cards, navbar e rodapé. "Ver cursos" e "Ir para notícias" continuam parados |
| Cards de curso | Cada card leva a `/contact/`, revela o traço de cada linha do título e não sublinha o resto do texto; o clique em "Jornalismo Cultural" abre Contato |
| Teclado | Tab chega ao card seguinte, que cresce e revela o traço |
| Movimento reduzido | Cards e botões sem transição; título sem split com o sublinhado instantâneo e o resto do card sem sublinhado |
| 375 px | O "Fale com a Komuniki" do menu móvel cresce sem criar rolagem horizontal |
| Reveal de texto | As 38 verificações de `reveal-all.mjs` passaram, com o card de curso já como link, e o título de Cursos, Sobre e Início parado no ponto de partida quando a página é pintada |
| Testes | 477 testes do pytest, o Ruff e o `collectstatic` com manifest passaram |

## Reversão

- **Tirar a animação:** remover o bloco "Underline reveal" de `school-editorial.css`, voltar a regra geral para `.ed-school a:not(.ed-button):hover{text-decoration:underline;text-underline-offset:4px}` e devolver o `text-decoration:underline;text-underline-offset:5px` ao hover e à página atual da navbar. Depois, subir a versão da folha.
- **Tirar só o crescimento:** remover as três regras `.ed-grow` de `school-editorial.css` e subir a versão da folha. A classe nos templates não faz nada sem elas.
- **Cards de curso sem link:** voltar o `<a href="{% url 'contact:page' %}" ...>` de `page_detail.html` para `<article>` e o seletor `.ed-course-group .ed-card>div:first-child>span` para `article>div:first-child>span`.
- Os spans e as classes nos templates não fazem nada sem o CSS e podem ficar. Se forem removidos, o `data-reveal` dos links do rodapé deve voltar do `<li>` para o link, e o `x-text` dos spans internos deve voltar para o link.
