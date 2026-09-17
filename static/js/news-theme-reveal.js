// Circular reveal do tema, o mesmo da escola (js/school-editorial.js): o tema novo cresce em círculo a partir do
// ícone clicado, por cima do snapshot do tema antigo, sem mover a página. Onde não houver view transition, ou com
// movimento reduzido, a troca acontece de uma vez, como antes.
(() => {
    const DURATION = 450;
    const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Os pseudo-elementos da view transition vivem no snapshot containing block, que abrange a barra de endereço
    // retrátil: no celular a origem dele fica acima da viewport de layout e o tamanho é o da viewport grande.
    // O getBoundingClientRect() responde em coordenadas da viewport de layout, então o centro precisa da diferença.
    const snapshotBlock = () => {
        const fallback = { width: innerWidth, height: innerHeight, offsetTop: 0 };
        if (!window.CSS || !CSS.supports('height', '100lvh') || !document.body) {
            return fallback;
        }
        const probe = document.createElement('div');
        probe.style.cssText = 'position:fixed;left:0;top:0;width:100lvw;height:100lvh;visibility:hidden;pointer-events:none';
        document.body.appendChild(probe);
        const { width, height } = probe.getBoundingClientRect();
        probe.remove();
        // O Chrome do Android deixa a barra retrátil no topo e informa a altura visível em innerHeight, enquanto o
        // Safari do iOS já informa a viewport grande ali: o que a viewport grande tem a mais é o que fica acima.
        return width > 0 && height > 0 ? { width, height, offsetTop: Math.max(0, height - innerHeight) } : fallback;
    };

    // apply troca o tema e devolve uma promessa que resolve quando a nova pintura estiver pronta para o snapshot.
    window.themeReveal = async (event, apply) => {
        // O botão é guardado de forma síncrona: event.currentTarget não sobrevive a um await.
        const trigger = event && event.currentTarget;
        const root = document.documentElement;
        if (!trigger || !document.startViewTransition || !root.animate || reducedMotion()) {
            await apply();
            return;
        }
        root.dataset.themeReveal = '';
        let transition;
        try {
            transition = document.startViewTransition(apply);
            // Uma aba oculta ou uma captura interrompida podem pular a animação; o tema muda do mesmo jeito.
            const finished = transition.finished.catch(() => {});
            try {
                await transition.ready;
                if (reducedMotion()) {
                    transition.skipTransition();
                } else {
                    // Os pseudo-elementos já existem. Ler o centro aqui mantém o reveal no mesmo estado de viewport
                    // do snapshot quando a barra do navegador se mexe.
                    const rect = trigger.getBoundingClientRect();
                    const block = snapshotBlock();
                    const x = rect.left + rect.width / 2;
                    const y = rect.top + rect.height / 2 + block.offsetTop;
                    const radius = Math.hypot(Math.max(x, block.width - x), Math.max(y, block.height - y));
                    // Porcentagem, não pixel: ela se resolve contra a própria caixa do pseudo-elemento, então o
                    // círculo acerta o ícone qualquer que seja a unidade em que o navegador mede essa caixa. O
                    // Chrome do Android mede em pixels de dispositivo, o que encolhia o reveal por devicePixelRatio.
                    // Um raio em porcentagem no circle() se resolve contra a diagonal da caixa dividida por sqrt(2).
                    const reference = Math.hypot(block.width, block.height) / Math.SQRT2;
                    const at = `at ${(x / block.width * 100).toFixed(3)}% ${(y / block.height * 100).toFixed(3)}%`;
                    root.animate({
                        clipPath: [`circle(0% ${at})`, `circle(${(radius / reference * 100).toFixed(3)}% ${at})`],
                    }, {
                        duration: DURATION,
                        easing: 'cubic-bezier(.4,0,.2,1)',
                        pseudoElement: '::view-transition-new(root)',
                    });
                }
            } catch (_) {
                transition.skipTransition();
            }
            await finished;
        } catch (_) {
            if (transition) {
                transition.skipTransition();
            } else {
                await apply();
            }
        } finally {
            delete root.dataset.themeReveal;
        }
    };
})();
