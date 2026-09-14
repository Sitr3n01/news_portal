// Reveal de texto por linha: GSAP SplitText + ScrollTrigger, vendorizados em js/vendor/gsap-3.15.0.
//
//   <h2 data-reveal="mask">  headline grande: cada linha sobe de trás de um recorte
//   <h3 data-reveal="fade">  título menor: cada linha surge sem recorte
//   <div data-reveal-group data-reveal-step="0.2">  os [data-reveal] de dentro entram em cascata, com um gatilho só
//   <section data-reveal-hero>  dispara no load, sem scroll: os [data-reveal] e o [data-reveal-lede] de dentro
//
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
    const observers = [];
    let ctx = null;

    const destroy = () => {
        observers.forEach((observer) => observer.disconnect());
        observers.length = 0;
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

        const config = {
            type: 'lines',
            linesClass: 'line',
            autoSplit: true,    // refaz o split no resize e quando a webfont carrega
            aria: 'auto',       // o título ganha aria-label com o texto e as linhas ficam aria-hidden
            onSplit(self) {
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

        let split = SplitText.create(el, config);

        // O x-text do Alpine troca PT/EN reescrevendo textContent, o que apaga as linhas. O split é refeito
        // com o texto novo; o revert() vem antes porque o SplitText antigo restauraria o idioma anterior.
        const observer = new MutationObserver(() => {
            if (split.lines.every((line) => el.contains(line))) {
                return;
            }
            const text = el.textContent;
            ctx.add(() => {
                split.revert();
                el.textContent = text;
                split = SplitText.create(el, config);
            });
            observer.takeRecords();
        });
        observer.observe(el, { childList: true });
        observers.push(observer);

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
                    tl.add(createBlock(el).animateIn, 'start');
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
                const tl = gsap.timeline({
                    scrollTrigger: {
                        trigger: group,
                        start: 'top bottom',
                        end: 'top top',
                        scrub: false,
                        markers,
                        // Como no bloco isolado: ao sair pela base da tela o grupo volta a esconder, e a próxima
                        // entrada recomeça a cascata.
                        toggleActions: 'play none none reset',
                        onLeaveBack: () => apis.forEach((api) => api.reset()),
                    },
                });
                tl.add('start');
                apis.forEach((api, i) => {
                    tl.add(api.reset, 'start');
                    tl.add(api.animateIn, `start+=${i * (Number.isNaN(step) ? STEP : step)}`);
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
        observers.push(langObserver);
        // Numa navegação comum o navegador libera tudo; isto cobre uma troca do htmx que remova o texto.
        for (const block of blocks) {
            block.el.addEventListener('htmx:beforeCleanupElement', destroy, { once: true });
        }
    };

    // Linha depende da métrica da fonte: dividir antes da webfont carregar deixa as quebras erradas.
    Promise.race([
        document.fonts ? document.fonts.ready : Promise.resolve(),
        new Promise((resolve) => setTimeout(resolve, 2500)),
    ]).then(() => {
        try {
            init();
        } catch (error) {
            destroy();
            console.error('Reveal de texto indisponível:', error);
        }
    });
})();
