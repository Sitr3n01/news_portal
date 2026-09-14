// Reveal de texto por linha: GSAP SplitText + ScrollTrigger, vendorizados em js/vendor/gsap-3.15.0.
//
//   <h2 data-reveal="mask">  headline grande: cada linha sobe de trás de um recorte
//   <p data-reveal="fade">   texto menor: cada linha surge sem recorte
//   <div data-reveal-group data-reveal-step="0.2">  os [data-reveal] de dentro entram em cascata, com um gatilho só;
//                                                   grupos irmãos na mesma fileira começam com STEP entre si
//   <section data-reveal-hero>  dispara no load: os [data-reveal] de dentro (data-reveal-at="0.7" adia em segundos)
//                               e o [data-reveal-lede]
//
// Marque o elemento que contém o texto, nunca um contêiner flex ou grid: as palavras virariam itens do layout.
// Temporário: ?reveal-markers na URL liga os markers dos ScrollTriggers para conferir start e end.
(() => {
    const DUR = 0.9;            // duração de cada linha
    const EASE = 'power3.out';  // curva de cada linha
    const STAGGER = 0.1;        // atraso entre linhas do mesmo bloco
    const STEP = 0.2;           // atraso entre blocos irmãos de um grupo
    const OWNER = '[data-reveal-hero],[data-reveal-group]';

    const root = document.documentElement;
    const { gsap, ScrollTrigger, SplitText } = window;
    const blocks = [];
    const cleanups = [];
    let ctx = null;
    let refreshTimer = 0;
    const normalize = (text) => text.replace(/\s+/g, ' ').trim();

    // Um split refeito (largura nova, webfont, idioma) muda a altura do texto depois que o ScrollTrigger mediu a
    // página. O refresh do próprio resize pode rodar antes dos splits; sem medir de novo, o start dos gatilhos abaixo
    // fica errado e, no fim da página, passa do scroll máximo: o último grupo nunca entra. Os blocos refazem o split
    // na mesma leva, então o refresh é um só, depois do último.
    const refreshAfterSplit = () => {
        clearTimeout(refreshTimer);
        refreshTimer = setTimeout(() => ScrollTrigger.refresh(), 100);
    };

    const destroy = () => {
        clearTimeout(refreshTimer);
        cleanups.forEach((cleanup) => cleanup());
        cleanups.length = 0;
        // O contexto reverte os SplitText (devolvendo o HTML original), tweens, timelines e ScrollTriggers.
        ctx?.revert();
        ctx = null;
        blocks.length = 0;
        root.classList.remove('js');
    };
    // O guard do <head> confere esta referência no DOMContentLoaded para saber se o módulo chegou a rodar.
    window.komunikiReveal = { blocks, destroy };

    // Movimento reduzido, GSAP ausente ou guard já desfeito: texto estático, sem split.
    if (!root.classList.contains('js') || !gsap || !ScrollTrigger || !SplitText
        || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        root.classList.remove('js');
        return;
    }
    gsap.registerPlugin(ScrollTrigger, SplitText);
    const markers = new URLSearchParams(window.location.search).has('reveal-markers');

    const createBlock = (el) => {
        const mode = el.dataset.reveal === 'mask' ? 'mask' : 'fade';
        let state = 'hidden';   // hidden | pending | revealed
        let tl = null;
        let splitText = '';

        const config = {
            type: 'lines',
            linesClass: 'line',
            autoSplit: true,    // refaz o split no resize e quando a webfont carrega
            // Título: aria-label com o texto e linhas aria-hidden, como na spec. Parágrafo, item de lista e span não
            // aceitam aria-label, e o leitor de tela ficaria mudo; neles as linhas continuam legíveis.
            aria: /^H[1-6]$/.test(el.tagName) ? 'auto' : 'none',
            // Na troca de idioma o bloco ganha um SplitText novo, que não deve restaurar o HTML do anterior.
            overwrite: false,
            onSplit(self) {
                // splitText só está vazio no primeiro split, feito antes de os gatilhos medirem a página.
                if (splitText) {
                    refreshAfterSplit();
                }
                if (mode === 'mask') {
                    for (const line of self.lines) {
                        let wrap = line.parentElement;
                        if (wrap === el) {
                            // Versão sem mask: o recorte é criado aqui.
                            wrap = document.createElement('div');
                            el.insertBefore(wrap, line);
                            wrap.appendChild(line);
                        }
                        wrap.classList.add('line-wrap');
                    }
                }
                splitText = normalize(el.textContent);
                const tween = mode === 'mask'
                    ? gsap.fromTo(self.lines, { x: -50, yPercent: 100 }, { x: 0, yPercent: 0, duration: DUR, stagger: STAGGER, ease: EASE, paused: true })
                    : gsap.fromTo(self.lines, { x: -50, opacity: 0 }, { x: 0, opacity: 1, duration: DUR, stagger: STAGGER, ease: EASE, paused: true });
                tl = tween;
                gsap.set(el, { opacity: 1 });
                if (state === 'revealed') {
                    tween.progress(1);
                    // Ao receber o tween, o SplitText aplica nele o tempo do anterior, que fica curto quando o
                    // resize criou linhas: a última pararia no meio. O microtask roda depois disso.
                    queueMicrotask(() => tl === tween && tween.progress(1));
                } else if (state === 'pending') {
                    state = 'revealed';
                    tween.play(0);
                }
                return tween;
            },
        };
        if (mode === 'mask') {
            config.mask = 'lines';  // cria o wrapper de recorte
        }
        // Com white-space pre*, as quebras do texto são conteúdo: viram <br> em vez de espaço.
        if (getComputedStyle(el).whiteSpace.startsWith('pre')) {
            config.reduceWhiteSpace = false;
        }

        let split = SplitText.create(el, config);

        // O x-text do Alpine troca PT/EN reescrevendo o texto do elemento ou de um filho, o que apaga ou desatualiza
        // as linhas. Recortes e linhas são desfeitos movendo os nós vivos de volta, porque o HTML guardado pelo
        // SplitText traria o idioma anterior e perderia os vínculos do Alpine, e o texto novo é dividido.
        const observer = new MutationObserver(() => {
            if (split.lines.every((line) => el.contains(line)) && normalize(el.textContent) === splitText) {
                return;
            }
            ctx.add(() => {
                split.kill();
                // Aposentada: um resize já agendado no SplitText antigo restauraria o HTML do idioma anterior.
                split.isSplit = false;
                tl?.kill();
                for (const node of el.querySelectorAll('.line-mask, .line')) {
                    node.replaceWith(...node.childNodes);
                }
                el.normalize();
                el.removeAttribute('aria-label');
                split = SplitText.create(el, config);
            });
            observer.takeRecords();
        });
        observer.observe(el, { childList: true, subtree: true, characterData: true });
        cleanups.push(() => observer.disconnect());

        const api = {
            el,
            mode,
            reset() {
                state = 'hidden';
                tl?.pause(0);
            },
            animateIn() {
                if (tl) {
                    state = 'revealed';
                    tl.play(0);
                } else {
                    state = 'pending';
                }
            },
            resplit() {
                if (split.isSplit) {
                    split.split(split.vars);
                }
            },
        };
        blocks.push(api);
        return api;
    };

    const init = () => {
        // Sem função, gsap.context() devolve o contexto ativo (nenhum), não um novo.
        ctx = gsap.context(() => {});
        ctx.add(() => {
            const ownedBy = (container) => [...container.querySelectorAll('[data-reveal]')]
                .filter((el) => el.closest(OWNER) === container);

            // Hero: dispara no load. A ilustração da spec fica de fora, porque o hero da Home é o palco de partículas.
            for (const hero of document.querySelectorAll('[data-reveal-hero]')) {
                const tl = gsap.timeline({ delay: 0.15 });
                tl.add('start');
                for (const el of ownedBy(hero)) {
                    tl.add(createBlock(el).animateIn, `start+=${Number.parseFloat(el.dataset.revealAt) || 0}`);
                }
                const lede = hero.querySelector('[data-reveal-lede]');
                if (lede) {
                    tl.fromTo(lede, { opacity: 0, y: 50 }, { opacity: 1, y: 0, duration: 0.8, ease: 'power2.out' }, 'start+=0.5');
                }
            }

            // Grupo: um timeline pai com um gatilho só, para a cascata seguir a ordem e não a entrada de cada filho.
            for (const group of document.querySelectorAll('[data-reveal-group]')) {
                const step = Number.parseFloat(group.dataset.revealStep);
                const apis = ownedBy(group).map(createBlock);
                const tl = gsap.timeline({ paused: true });
                tl.add('start');
                apis.forEach((api, i) => {
                    tl.add(api.reset, 'start');
                    tl.add(api.animateIn, `start+=${i * (Number.isNaN(step) ? STEP : step)}`);
                });
                // Grupos irmãos lado a lado, como cards de uma fileira, começam com STEP entre si. Empilhados, no
                // celular, cada um começa ao entrar.
                const rowDelay = () => {
                    const top = group.getBoundingClientRect().top;
                    const row = [...group.parentElement.children].filter((sibling) => sibling.matches('[data-reveal-group]')
                        && Math.abs(sibling.getBoundingClientRect().top - top) < 2);
                    return Math.max(0, row.indexOf(group)) * STEP;
                };
                ScrollTrigger.create({
                    trigger: group,
                    start: 'top bottom',
                    end: 'top top',
                    scrub: false,
                    markers,
                    onEnter: () => tl.delay(rowDelay()).restart(true),
                    // Como no bloco isolado: ao sair pela base da tela o grupo volta a esconder, e a próxima entrada
                    // recomeça a cascata.
                    onLeaveBack: () => {
                        tl.pause(0);
                        apis.forEach((api) => api.reset());
                    },
                });
            }

            // Bloco isolado. O onLeaveBack reinicia o reveal quando o usuário sobe e desce de novo.
            for (const el of document.querySelectorAll('[data-reveal]')) {
                if (el.closest(OWNER)) {
                    continue;
                }
                const api = createBlock(el);
                ScrollTrigger.create({
                    trigger: el,
                    start: 'top bottom',
                    end: 'top top',
                    scrub: false,
                    markers,
                    onEnter: () => api.animateIn(),
                    onLeaveBack: () => api.reset(),
                });
            }
        });

        // Trocar o idioma muda a altura dos textos: os gatilhos abaixo precisam medir de novo.
        const langObserver = new MutationObserver(() => requestAnimationFrame(() => ScrollTrigger.refresh()));
        langObserver.observe(root, { attributes: true, attributeFilter: ['lang'] });
        cleanups.push(() => langObserver.disconnect());

        // Texto em flex, inline ou pílula tem a largura das próprias linhas, e linha não quebra: o autoSplit, que
        // observa o elemento, não percebe a viewport encolher. Largura nova da viewport, split novo em todos.
        let lastWidth = window.innerWidth;
        let resizeTimer = 0;
        const onResize = () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                if (window.innerWidth !== lastWidth) {
                    lastWidth = window.innerWidth;
                    blocks.forEach((block) => block.resplit());
                }
            }, 200);
        };
        window.addEventListener('resize', onResize);
        cleanups.push(() => {
            clearTimeout(resizeTimer);
            window.removeEventListener('resize', onResize);
        });

        // Numa navegação comum o navegador libera tudo; isto cobre uma troca do htmx que remova o texto.
        for (const block of blocks) {
            block.el.addEventListener('htmx:beforeCleanupElement', destroy, { once: true });
        }
    };

    // Com a webfont em cache o init roda antes da primeira pintura, e dividir e medir todo o texto a atrasa: uma animação
    // iniciada no init já teria andado ou acabado quando a página aparecesse (o título de Cursos, primeiro da cascata,
    // surgia parado). O tempo do GSAP fica parado até um quadro depois da primeira pintura; o teto cobre aba oculta.
    const afterFirstPaint = (callback) => {
        let done = false;
        const run = () => {
            if (!done) {
                done = true;
                requestAnimationFrame(callback);
            }
        };
        if (window.PerformanceObserver && PerformanceObserver.supportedEntryTypes?.includes('paint')) {
            new PerformanceObserver((list, observer) => {
                observer.disconnect();
                run();
            }).observe({ type: 'paint', buffered: true });
        } else {
            requestAnimationFrame(run);
        }
        setTimeout(run, 1000);
    };

    // Linha depende da métrica da fonte: dividir antes da webfont carregar deixa as quebras erradas.
    Promise.race([
        document.fonts ? document.fonts.ready : Promise.resolve(),
        new Promise((resolve) => setTimeout(resolve, 2500)),
    ]).then(() => {
        gsap.globalTimeline.pause();
        try {
            init();
        } catch (error) {
            destroy();
            console.error('Reveal de texto indisponível:', error);
        } finally {
            afterFirstPaint(() => gsap.globalTimeline.resume());
        }
    });
})();
