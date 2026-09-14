# Continuidade da Komuniki

Estado de 13/09/2026. Trabalhar em `C:\Users\Sitr3n\Documents\Github\news_portal-komuniki-design`, branch **`codex/komuniki-editorial-test`**. A partir de `026249c` (tag `codex/komuniki-static-blue`), a troca dos detalhes menta por azul claro e o hero de partículas foram versionados juntos no commit `8983664` (`feat(school): replace hero illustration with WebGL particle stage`). Os refinamentos do hero, com camadas e tema claro sem bloco, vieram no commit seguinte (`feat(school): layer the hero particles over the copy and drop the black stage`). Não houve push, merge ou publicação.

## Decisões atuais do usuário

- **Nenhum movimento**, inclusive hover, transições e rolagem suave, **com duas exceções aprovadas em 13/09/2026: as partículas do hero da Home e o reveal de texto por linha.** Com `prefers-reduced-motion: reduce` as partículas ficam paradas e o texto não é dividido nem animado. Preservar a regra no resto do site.
- **Reveal de texto por linha:** GSAP 3.15.0 vendorizado (SplitText + ScrollTrigger), marcado no HTML com `data-reveal="mask"`, `data-reveal="fade"`, `data-reveal-group` e `data-reveal-hero`. Vale para todo o texto de Início, Sobre e Cursos, inclusive o rodapé dessas páginas. A navbar, Contato, Privacidade e as demais páginas do CMS ficam estáticos. Dentro de cards, o começo das linhas aparece cortado enquanto entra, por causa do `x: -50` da spec; o usuário decidiu manter assim. Valores, correção dos acentos e validação em [Reveal de texto](komuniki-text-reveal.md).
- Azul oficial `#0b3a75` nos destaques escuros; azul claro **`#b8d8ff`** substitui todos os antigos detalhes menta `#d1ffca` da base editorial. Etiquetas, seleção de texto, foco do link de salto, hover instantâneo, mensagens e grupos de cursos usam o token `--ed-blue-light`. A cor `primary.200` da configuração Tailwind também foi atualizada.
- **Hero de partículas** no lugar da ilustração estática: nuvem WebGL que alterna microfone, Terra e nuvem dispersa em duas camadas transparentes, uma sob e outra sobre o título, sem palco nem bloco. No tema escuro a luz é aditiva; no claro, as partículas são tinta. Arquivos, parâmetros e validação em [Hero de partículas](komuniki-particles.md). O PNG `komuniki-editorial-hero.png` saiu da Home e fica só como mídia de demonstração do `prepare.py`. A foto da Kelly permanece intacta.
- **Hero interativo:** arrastar com mouse ou toque gira a forma sem parar a rotação automática, e a passagem microfone → Terra espalha as partículas pela tela como a passagem Terra → nuvem.
- **Navbar flutuante:** sem a faixa de fundo atrás da cápsula; o conteúdo passa por baixo e ao redor dela, e os cliques ao lado da cápsula chegam à página. Atrás da cápsula há um desfoque progressivo (`.ed-nav-blur`): quatro camadas de `backdrop-filter`, de 1,5 a 16 px, mais fortes no topo, sobre um véu na cor do fundo que acompanha o tema.
- **Seções centralizadas:** todo bloco direto de `.ed-section` fica centralizado em até 1200 px, o que corrigiu a grade de Cursos em telas largas.
- **Painéis de chamada:** as duas metades do painel final, na Home e em Cursos, são colunas flexíveis com os botões na mesma linha.
- Manter os dados oficiais aplicados em `8d7c349`: contatos reais, três diferenciais na Home, seis cursos, sem seção social fictícia e sem cartão Jovem Comunicador na Home. A menção em Sobre permanece.

## Prévia e dados

```powershell
Set-Location 'C:\Users\Sitr3n\Documents\Github\news_portal-komuniki-design'
.\scripts\preview\preview.ps1 -Action status
.\scripts\preview\preview.ps1 -Action start
# Encerrar antes de reiniciar após mudanças em templates/Python:
.\scripts\preview\preview.ps1 -Action stop
```

- Principal: **http://127.0.0.1:8012/**, cenário `local`, banco `.preview/local.sqlite3`.
- Referência de conteúdo: http://127.0.0.1:8011/, banco `.preview/current.sqlite3`. Compartilha a apresentação da worktree, mas conserva seus próprios dados.
- As prévias 8011 e 8012 rodam com `--noreload`: depois de mudar templates, pare e inicie de novo, ou elas continuam servindo o HTML antigo.
- A prévia do Claude Code, em http://127.0.0.1:8013/, recarrega sozinha e usa o banco `local`, com os dados oficiais, por meio de `.preview/design_preview_local.py` (`manage.py runserver 127.0.0.1:8013 --settings=design_preview_local --pythonpath=.preview`). O banco `current` (8011) continua com os dados de exemplo da migração inicial, de propósito: é a cópia de referência.
- `.preview/` contém bancos, mídia e evidências locais ignorados pelo Git. Outro agente nesta máquina deve reutilizar esta worktree. Um clone Git novo não recebe os bancos; consulte [conteúdo oficial](komuniki-official-content.md) e [preparação da prévia](komuniki-editorial-preview.md) antes de recriá-los.
- O checkout original `C:\Users\Sitr3n\Documents\Github\news_portal` e seu banco foram preservados. Não houve mudança de API, modelos, migrações, formulário ou componentes do Blog/vagas.

## Verificação

- **Paleta azul:** 40 verificações de página passaram (cinco rotas × 375×812 e 1440×900 × claro/escuro × PT/EN) com `scripts/preview/presentation_e2e.mjs`. A auditoria encontrou zero elementos com a antiga cor menta, e as etiquetas renderizaram `rgb(184, 216, 255)` com texto preto. Evidências em `.preview/evidence/light-blue/`.
- **Hero de partículas:** veja [a validação](komuniki-particles.md#validação). A checagem `approved_hero_preserved` de `scripts/preview/verify_public_content.py` virou `particles_hero_present`.
- **Rodada de finalização:** na 8013, botões do painel final alinhados na Home e em Cursos, grade de Cursos centralizada em 1920 px como Sobre, navbar sem faixa, arraste com mouse e toque, dados oficiais nas cinco páginas sem placeholders e 467 testes aprovados. Capturas em `.preview/evidence/round3/`.
- **Reveal de texto:** 38 verificações no Edge headless passaram nas três páginas. O texto fica nas mesmas posições da marcação anterior e do texto estático a 1440 e 375 px, todos os blocos revelam, as cascatas e o reinício funcionam, PT/EN confere com o Alpine, a acessibilidade está correta, Contato e Privacidade seguem intactos e o Slow 4G não pisca. Também passaram o `collectstatic` com manifest, 472 testes e o Ruff. Detalhes e capturas em [Reveal de texto](komuniki-text-reveal.md#validação).

## Reversão

As duas rodadas estão no mesmo commit, sem tag própria; o checkpoint anterior é `codex/komuniki-static-blue` (`026249c`). Para desfazer só o hero de partículas, siga [a reversão do hero](komuniki-particles.md#reversão). **Não restaurar bancos anteriores para reverter visual.**

O histórico de movimento e sua remoção está em [Komuniki estática com destaque azul](komuniki-static-blue.md).
