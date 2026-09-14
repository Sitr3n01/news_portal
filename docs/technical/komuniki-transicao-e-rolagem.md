# Transição entre páginas, rolagem suave e Cursos em inglês

Implementado em 14/09/2026 na worktree `news_portal-komuniki-design`, branch `codex/komuniki-editorial-test`, a pedido do usuário. A rodada cobre cinco pontos:
- rolagem suave no botão de rolar da Home;
- fade entre páginas até tudo carregar;
- revisão da entrada do título de Cursos;
- conteúdo de Cursos em inglês;
- cache das Configurações do Site entre os workers do gunicorn.

## Decisões

- **Rolagem suave só nos botões de âncora.** O botão de rolar da Home (`#hero-support-sheet`) e "Ver cursos" (`#grade-cursos`) usam `scrollIntoView({ behavior: 'smooth' })`. A seção para a 144 px do topo, onde a navbar termina (`scroll-padding-top`), a âncora entra no endereço e o foco vai para a seção, como no salto nativo. O link de pular para o conteúdo continua saltando. Com movimento reduzido, os dois botões também saltam.
- **Fade entre páginas.** O `<head>` marca `<html data-ed-page="loading">`, e `main` e o rodapé ficam com `opacity: 0` e sem cliques. O módulo da página (`static/js/school-editorial.js`) tira a marca, e o conteúdo aparece em 0,4 s, quando estão prontos:
  - as três webfonts;
  - o `load` da página;
  - o reveal, com todos os blocos divididos;
  - na Home, o primeiro quadro das partículas.

  O teto é de 2,5 s desde o início da navegação, e o `<head>` tira a marca sozinho aos 4 s se um script falhar. A navbar não participa: fica parada, igual de uma página para a outra.
- **Saída.** Um clique num link interno para outra página esmaece `main` e o rodapé em 0,2 s e só então navega. Ficam de fora cliques com tecla modificadora ou botão do meio, `target` externo, `download`, links para outro domínio (o Blog, em produção), `mailto:` e `tel:`, e âncoras da mesma página. Voltar pelo histórico mostra a página já visível.
- **Movimento reduzido.** A página continua esperando tudo carregar, mas aparece sem fade, e a saída não esmaece.
- **Atributo, não classe.** O runtime do Tailwind observa as classes do `<html>` e reprocessa a página a cada troca. O `data-ed-page` não dispara esse trabalho.
- **Título de Cursos.** O `document.fonts.ready` resolvia antes de a página pedir as fontes, entre 10 e 26 ms. O reveal dividia o texto com a fonte de fallback, e o `autoSplit` redividia os títulos quando a webfont chegava. Em Cursos, a página mais pesada, isso caía entre 223 e 299 ms, quando o título já subia. Um bloco revelado que é redividido vai direto ao fim, e a entrada parecia travar. Agora o split espera `document.fonts.load()` das três fontes, e as entradas começam um quadro depois de a página aparecer.
- **Cursos em inglês.** Todo texto do catálogo (`apps/school/courses.py`) tem a versão `_en`, e o template usa `x-text`. Também trocam de idioma o prêmio (`COURSE_AWARD_EN`), a etiqueta do curso em Contato, os assuntos do formulário (`ContactInquiryForm.subject_options`) e o slogan do rodapé. Os nomes dos cursos em inglês são os que a Home já usava. A mensagem de contato continua gravando o nome do curso em português.
- **Slogan em inglês.** O campo `SiteExtension.tagline_en` é novo e aparece em Configurações do Site. A migração `common.0010` preenche "Communication that drives results" onde o slogan é o real e o campo está vazio.
- **Cache das Configurações do Site.** O Django guarda o `Site` em cache no processo, e `site.extension` ficava preso a ele. Uma edição salva em um worker do gunicorn só chegava ao outro quando ele era reciclado, e uma migração de dados não chegava a nenhum até reiniciar. `get_site_settings()` (`apps/common/site_settings.py`) lê do banco a cada uso: no context processor, na newsletter e nos e-mails de conta. O signal de `apps/common/signals.py`, que só limpava o cache do processo que salvava, foi removido.

## Arquivos

| Arquivo | Papel |
|---|---|
| `templates/base_school_editorial.html` | Marca `data-ed-page="loading"` e teto de 4 s no `<head>`; folha em `?v=19`, `school-editorial.js` em `?v=2`, reveal em `?v=4` |
| `static/js/school-editorial.js` | Módulo da página: webfonts, espera, fade de saída, `pageshow` e rolagem suave |
| `static/css/school-editorial.css` | Transição de opacidade de `main` e rodapé, estados `loading` e `leaving` e movimento reduzido |
| `static/js/school-editorial-reveal.js` | `ready` exposto, espera das webfonts e retomada do GSAP quando a página aparece |
| `static/js/school-editorial-particles.js` | `data-particles-ready` e evento `komuniki:particles-ready`; script em `?v=3` |
| `templates/school/home.html`, `templates/school/page_detail.html` | `data-smooth-scroll` nos dois botões; `x-text` em todo o catálogo e no prêmio |
| `apps/school/courses.py`, `apps/school/views.py` | Textos `_en` do catálogo e `COURSE_AWARD_EN` |
| `templates/contact/contact_page.html`, `apps/contact/forms.py` | Etiqueta do curso e assuntos em inglês |
| `templates/school/editorial/footer.html`, `apps/common/models.py`, `apps/common/migrations/0010_siteextension_tagline_en.py`, `apps/common/wagtail_hooks.py` | Slogan em inglês |
| `apps/common/site_settings.py`, `apps/common/context_processors.py`, `apps/news/newsletter.py`, `apps/accounts/mailer.py` | Configurações do Site lidas do banco a cada uso |
| `apps/common/tests.py`, `apps/accounts/test_emails.py`, `apps/school/tests.py`, `apps/contact/tests.py`, `apps/social/tests.py` | Edição feita fora do processo, traduções e marcação dos templates |

## Implantação

- O `migrate` aplica `common.0010`, que cria o campo e preenche o slogan em inglês.
- Depois do deploy, uma edição em Configurações do Site aparece no request seguinte em todos os workers, sem reiniciar.

## Como testar

1. Na Home, clique no botão redondo abaixo do título: a página rola até o bloco de reconhecimento.
2. Troque de página pela navbar: o conteúdo some em 0,2 s, a página nova aparece inteira com fade, e os textos entram em seguida.
3. Em Cursos, recarregue algumas vezes: o título sobe linha a linha até o fim, sem saltar.
4. Troque para EN em Cursos e em Contato: catálogo, prêmio, etiqueta, assuntos e slogan em inglês.
5. Com "reduzir movimento" no sistema: página sem fade e salto nas âncoras.
6. Edite o slogan em Configurações do Site e recarregue qualquer página: o rodapé muda na hora.

## Validação

Feita em 14/09/2026 no Edge headless via CDP, a 1440 × 900. Roteiros e resultados em `.preview/evidence/transicao-e-cursos/`, fora do Git.

| Critério | Antes | Depois |
|---|---|---|
| Redivisões depois do split | Cursos: 10 blocos, o título entre 223 e 299 ms, durante a entrada; Sobre: 2; Início: 6 | Nenhuma depois de a página aparecer, em oito cargas frias e quentes de cinco páginas |
| Página ao aparecer | Os blocos surgiam aos poucos | Fontes carregadas, todos os blocos divididos e, na Home, partículas desenhadas; `main` passa por vários quadros de opacidade |
| Começo das entradas | Um quadro depois da primeira pintura | Um quadro depois de a página aparecer: Início 358 → 365 ms, Sobre 167 → 170 ms, Cursos 272 → 277 a 288 ms |
| Saída e volta | Troca seca | Início → Sobre esmaece antes de navegar; voltar pelo histórico mostra a página |
| Rolagem suave | Salto | Botão da Home e "Ver cursos": vários quadros até a âncora, a 144 px do topo, com a âncora no endereço e o foco na seção. Com movimento reduzido, salto |
| Inglês | Catálogo, prêmio, etiqueta, assuntos e slogan em português | Tudo em inglês no navegador; em Cursos, nenhuma linha em português além do endereço |
| Console | — | Nenhum erro novo; restam os avisos do Tailwind CDN, do Turnstile e o 404 de `/favicon.ico` |
| Testes | — | 493 do pytest, o Ruff e o `makemigrations --check` passaram |
| Regressão do reveal | — | As 38 verificações de `reveal-all.mjs` passaram, inclusive o texto de cada bloco igual ao `x-text` em PT e EN em Cursos. A geometria foi comparada com a própria 8013, porque as prévias 8011 e 8012 estavam desligadas. Resultado em `.preview/evidence/botoes-e-cursos-2026-09-14/regressao-transicao-2026-09-14/` |

Nota sobre a medição: o primeiro amostrador lia `getComputedStyle` a cada 8 ms e sugeria 25 quadros por segundo no título de Sobre e de Cursos. Era o custo do próprio amostrador. Lida pelo ticker do GSAP, a entrada já rodava a 60 quadros por segundo: o problema era o salto da redivisão, não a cadência.

## Reversão

- **Só a rolagem suave:** tirar `data-smooth-scroll` dos dois links.
- **Só o fade:** tirar a marca `data-ed-page` do `<head>` e o bloco "Page transition" do CSS, subindo a versão da folha. O módulo da página continua carregando as fontes e liberando o reveal.
- **Esperar só o `document.fonts.ready` no título:** não recomendado, porque traz o salto de volta.
- **O slogan em inglês:** reverter o rodapé; a coluna pode ficar no banco.
- **O cache:** voltar a `site.extension` traz de volta o atraso entre workers.
