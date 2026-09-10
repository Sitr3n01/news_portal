# Movimento editorial da Komuniki

Implementado em 9 de setembro de 2026 na worktree `news_portal-komuniki-design`, branch `codex/komuniki-editorial-test`. A aprovação visual anterior foi preservada no commit **`ef03939`** antes desta alteração. Os bancos, mídias locais, exportações e evidências continuam fora do Git, em `.preview/`. Nenhuma publicação foi realizada.

## Regras e implementação

| Elemento | Comportamento |
| --- | --- |
| Rolagem | Reutiliza `scroll-behavior: smooth` para âncoras. Rodinha, trackpad e toque continuam nativos. Mantém a compensação do cabeçalho fixo. |
| Títulos de seção | `data-ed-reveal` seleciona explicitamente os títulos editoriais grandes. A opacidade depende da posição atual na viewport e retrocede ao rolar para cima. Sem translação, escala, blur, divisão em palavras/letras ou animação temporal. |
| Hero e conteúdo funcional | H1, parágrafos, etiquetas, campos, pequenos títulos e metadados permanecem visíveis e estáticos. |
| Ilustração | O render existente recebe translação vertical de até 6 px e rotação de 0,6 grau, num ciclo de 12 s. Em mobile: 3 px, 0,3 grau e 16 s. Não há mouse-follow ou modelo 3D novo. |
| Pausa | Botão sobre a área da ilustração, fora do fluxo do layout, operável por teclado. `aria-pressed` comunica a pausa e a escolha persiste entre visitas. A animação também pausa fora da viewport e quando a aba está oculta. |
| Cabeçalho | Mantém posição, dimensões e cápsula. Superfície clara: marca escura, cápsula branca e CTA preto. Superfície escura: marca branca, cápsula grafite e CTA amarelo. Transição de cor em 350 ms. |
| Seções de contraste | O grande bloco de reconhecimento mantém sua geometria e entrada natural pelo scroll. Nenhuma animação foi aplicada à superfície inteira. |
| Cartões | Os informativos permanecem imóveis. Somente cartões que são links recebem `scale(1.01)` no hover com ponteiro fino. |
| Botões e links | Botões usam feedback de cor e hover até `1.02`, pressionamento `0.99`. Links textuais mantêm o sublinhado existente. Sem novas sombras. |
| Movimento reduzido | CSS elimina animações/transições, força opacidade 1 e desativa scroll suave. O controlador acompanha mudanças de preferência em tempo real. O controle da ilustração fica oculto quando não há movimento a pausar. |
| Sem JavaScript e impressão | Títulos são visíveis por padrão; a ilustração é estática. A impressão também força conteúdo visível. |

## Cálculo do reveal

Usando `h` como altura útil da viewport e `top` como posição do topo do título:

```text
p = clamp((0.80 * h - top) / (0.20 * h), 0, 1)
opacity = 0.15 + 0.85 * p^1.28
```

A curva é espacial, sem duração temporal: aproximadamente 0,15 em 80% da viewport, 0,50 em 70%, 0,74 em 65% e 1 em 60%. Os valores estão centralizados nos tokens CSS. Não há disparo único nem transição CSS de opacidade; cada posição tem uma opacidade determinada.

## Detecção do tema

`data-ed-theme="canvas"` representa o tema escolhido pelo visitante. `contrast` representa sua superfície invertida, como o bloco de reconhecimento; `dark` fixa o rodapé preto. O controlador também aceita `light` para futuras seções claras fixas.

A cada atualização, o controlador mede a linha central vertical do cabeçalho e as regiões marcadas. A região mais interna que cruza essa linha fornece o tema. Não existem coordenadas de scroll específicas de uma página. Cartões pequenos e colunas de uma seção mista não são usados para mudar o tema da navegação inteira. Trocar PT/EN, tema ou tamanho da janela recalcula a posição.

O logo cadastrado mantém a imagem original; quando presente sobre navegação escura, recebe fundo branco neutro, sem filtro que altere sua marca. A base local atual usa o nome textual. Uma eventual versão alternativa do logo real continua dependente dos arquivos da marca.

## Arquivos e componentes

- **Novo** `static/js/school-editorial-motion.js`: um controlador compartilhado de reveal, tema de seção, visibilidade e pausa da arte.
- **Novo** `static/css/school-editorial-motion.css`: tokens, estados, movimento da arte e regras de acessibilidade.
- `static/css/school-editorial.css`: remove o hover amplo anterior de todos os cartões, marca e imagem.
- `templates/base_school_editorial.html`: carrega os arquivos exclusivos da escola e declara a superfície base.
- `templates/school/home.html`: marca títulos e região de contraste, adiciona o controle da ilustração.
- `templates/school/about.html`, `page_detail.html`, `privacy.html` e `editorial/social_feed.html`: marcam explicitamente os títulos grandes.
- `templates/school/editorial/footer.html`: declara a superfície escura.
- **Novos** `scripts/preview/test_editorial_motion.cjs` e `motion_e2e.mjs`: testes do controlador e matriz no navegador CUA.

Não foi adicionada biblioteca nem etapa de compilação frontend. Django, Alpine e os arquivos vendorizados existentes continuam na mesma arquitetura. Blog, vagas, views, consultas, modelos, formulários, sanitização e rotas não foram modificados.

## Performance

Há um único listener passivo de scroll e um único `requestAnimationFrame` agendado por atualização. Eventos repetidos são agrupados; não há loop JavaScript enquanto a página está parada. `IntersectionObserver` limita as leituras dos títulos aos próximos da viewport e pausa a arte fora da tela. `ResizeObserver`, carregamento de fontes e mudanças de idioma/tema atualizam as medidas quando necessário.

As leituras geométricas do frame acontecem antes das escritas de estilo. O movimento usa apenas `opacity` e `transform`; o cabeçalho transiciona cores. Não há animação de tamanho, margem ou posição de layout, nem `will-change` aplicado indiscriminadamente.

## Validação desta rodada

- **101 testes Django existentes passaram**: escola, contato, redes sociais, componentes comuns e vagas.
- **7 testes do controlador passaram**: progressão e reversão, agrupamento de frames, temas, preferência reduzida em tempo real, pausa persistente, saltos de scroll e falhas de armazenamento/observers.
- **152 combinações passaram**: 38 resoluções de 280 a 4096 px × claro/escuro × PT/EN; **760 verificações de página e 176 verificações de interação**. Todas as cinco páginas, cabeçalho, menu móvel, Escape, foco e ausência de cortes/rolagem horizontal foram conferidos.
- Geometria de títulos, textos, seções e cartões comparada com o checkpoint: **dez casos** (cinco páginas em 375 e 1440 px), sem mudanças de posição ou dimensão. Textos normalizados preservados. Isso é comparação geométrica, não uma medição instrumentada de CLS de produção.
- No navegador: reveal em scroll de ida e volta; cores finais do cabeçalho e CTA em superfícies claras/escuras; rodapé móvel; pausa por Enter e persistência após recarga; âncoras Home/Cursos; movimento móvel reduzido para 3 px/16 s; cartões informativos sem transform e cartões clicáveis em 1,01. Nenhum erro de console na inspeção final da Home.
- Paridade de conteúdo aprovada, inclusive textos, traduções, destinos, imagens e contrato dos campos. Ruff e sintaxe JavaScript passaram. `collectstatic` completou na pasta isolada.
- Django check: zero erros e os dois avisos preexistentes de treebeard. A coleta mantém os avisos conhecidos de nomes duplicados de arquivos do admin. Pytest mantém avisos anteriores de Django 6 e diretório de estáticos de testes.

**Limites:** Chromium local; não cobre aparelhos físicos nem todos os motores. O navegador disponível não expõe emulação de `prefers-reduced-motion` ou toque: a preferência reduzida foi verificada no controlador por simulação e no CSS por revisão, sem alegar teste nativo dessa configuração. A matriz usa navegação para cada página e interações do menu; medições de scroll/pausa/âncoras são casos complementares específicos. Não foi repetido envio externo de contato; permanecem os limites de Turnstile documentados no relatório anterior.

**Aproximações deliberadas:** o smooth scroll usa o comportamento nativo existente, sem impor um `lerp` à rolagem da rodinha. A arte é um PNG composto, então seu movimento é aplicado ao render completo; não há peças ou câmera 3D independentes. Essas escolhas preservam a stack e evitam dependências e interferência na navegação.

Evidências locais: [resumo](../../.preview/evidence/editorial-motion/summary.json), [matriz](../../.preview/evidence/editorial-motion/matrix.jsonl), [geometria](../../.preview/evidence/editorial-motion/geometry-comparison.json), [reveal](../../.preview/evidence/editorial-motion/scroll-reveal.json), [cabeçalho escuro](../../.preview/evidence/editorial-motion/header-dark-surface.png), [cabeçalho claro](../../.preview/evidence/editorial-motion/header-light-surface.png) e [mobile](../../.preview/evidence/editorial-motion/home-mobile.png).

## Revisão e rollback

Prévia principal: `http://127.0.0.1:8012/`. A porta 8011 continua usando sua cópia independente de conteúdo e os mesmos templates do experimento. Para iniciar/parar, mantenha os comandos de `preview.ps1` do [guia do experimento](komuniki-editorial-preview.md).

Referências Git locais:

- `codex/komuniki-editorial-approved`: checkpoint aprovado, commit `ef03939`.
- `codex/komuniki-editorial-motion-v1`: commit isolado desta rodada de animações.

Para voltar ao comportamento aprovado anterior, preserve primeiro eventuais alterações posteriores. Com a worktree limpa, reverta somente o commit de motion; os bancos e a mídia em `.preview/` não são tocados:

```powershell
Set-Location 'C:\Users\Sitr3n\Documents\Github\news_portal-komuniki-design'
git status --short
git revert --no-edit codex/komuniki-editorial-motion-v1
.\scripts\preview\preview.ps1 -Action stop
.\scripts\preview\preview.ps1 -Action start
```

Recarregue a página depois. Não é necessário resetar a branch ou recriar os bancos. As referências são locais; não houve push, merge ou deploy. A pendência de conteúdo real de produção permanece separada desta aprovação visual.
