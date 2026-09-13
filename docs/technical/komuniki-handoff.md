# Continuidade da Komuniki

Estado de 13/09/2026. Trabalhar em `C:\Users\Sitr3n\Documents\Github\news_portal-komuniki-design`, branch **`codex/komuniki-editorial-test`**. A partir de `026249c` (tag `codex/komuniki-static-blue`), a troca dos detalhes menta por azul claro e o hero de partículas foram versionados juntos no commit `8983664` (`feat(school): replace hero illustration with WebGL particle stage`). Os refinamentos do hero, com camadas e tema claro sem bloco, vieram no commit seguinte (`feat(school): layer the hero particles over the copy and drop the black stage`). Não houve push, merge ou publicação.

## Decisões atuais do usuário

- **Nenhum movimento**, inclusive hover, transições e rolagem suave, **com uma exceção aprovada em 13/09/2026: as partículas do hero da Home.** Com `prefers-reduced-motion: reduce` elas ficam paradas. Preservar a regra no resto do site.
- Azul oficial `#0b3a75` nos destaques escuros; azul claro **`#b8d8ff`** substitui todos os antigos detalhes menta `#d1ffca` da base editorial. Etiquetas, seleção de texto, foco do link de salto, hover instantâneo, mensagens e grupos de cursos usam o token `--ed-blue-light`. A cor `primary.200` da configuração Tailwind também foi atualizada.
- **Hero de partículas** no lugar da ilustração estática: nuvem WebGL que alterna microfone, Terra e nuvem dispersa em duas camadas transparentes, uma sob e outra sobre o título, sem palco nem bloco. No tema escuro a luz é aditiva; no claro, as partículas são tinta. Arquivos, parâmetros e validação em [Hero de partículas](komuniki-particles.md). O PNG `komuniki-editorial-hero.png` saiu da Home e fica só como mídia de demonstração do `prepare.py`. A foto da Kelly permanece intacta.
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
- `.preview/` contém bancos, mídia e evidências locais ignorados pelo Git. Outro agente nesta máquina deve reutilizar esta worktree. Um clone Git novo não recebe os bancos; consulte [conteúdo oficial](komuniki-official-content.md) e [preparação da prévia](komuniki-editorial-preview.md) antes de recriá-los.
- O checkout original `C:\Users\Sitr3n\Documents\Github\news_portal` e seu banco foram preservados. Não houve mudança de API, modelos, migrações, formulário ou componentes do Blog/vagas.

## Verificação

- **Paleta azul:** 40 verificações de página passaram (cinco rotas × 375×812 e 1440×900 × claro/escuro × PT/EN) com `scripts/preview/presentation_e2e.mjs`. A auditoria encontrou zero elementos com a antiga cor menta, e as etiquetas renderizaram `rgb(184, 216, 255)` com texto preto. Evidências em `.preview/evidence/light-blue/`.
- **Hero de partículas:** veja [a validação](komuniki-particles.md#validação). A checagem `approved_hero_preserved` de `scripts/preview/verify_public_content.py` virou `particles_hero_present`.

## Reversão

As duas rodadas estão no mesmo commit, sem tag própria; o checkpoint anterior é `codex/komuniki-static-blue` (`026249c`). Para desfazer só o hero de partículas, siga [a reversão do hero](komuniki-particles.md#reversão). **Não restaurar bancos anteriores para reverter visual.**

O histórico de movimento e sua remoção está em [Komuniki estática com destaque azul](komuniki-static-blue.md).
