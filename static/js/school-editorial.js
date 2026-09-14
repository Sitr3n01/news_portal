// Transição entre páginas e rolagem suave, exceções ao site estático aprovadas em 14/09/2026.
// O <head> marca <html data-ed-page="loading">, e o CSS deixa main e footer invisíveis enquanto a marca existe. A página
// aparece de uma vez, com fade, quando fontes, reveal de texto e partículas estão prontos; um link interno esmaece o
// conteúdo antes de navegar. É atributo, e não classe, porque o runtime do Tailwind reprocessa a página a cada classe
// trocada no <html>.
(() => {
    const root = document.documentElement;
    const MAX_WAIT = 2500;   // ms desde o início da navegação: a página aparece mesmo que algo não carregue
    const FADE_OUT = 200;    // o mesmo transition-duration de [data-ed-page="leaving"] no CSS
    const FONTS = ['700 1em "Barlow Condensed"', '400 1em Inter', '400 1em "IBM Plex Mono"'];
    const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // As linhas do reveal dependem da métrica da webfont. O document.fonts.ready sozinho resolvia antes de a página
    // pedir as fontes: o texto era dividido com a fonte de fallback e redividido no meio da animação.
    const fontsReady = document.fonts
        ? Promise.all(FONTS.map((font) => document.fonts.load(font))).catch(() => {})
        : Promise.resolve();

    let markShown;
    const shown = new Promise((resolve) => {
        markShown = resolve;
    });
    window.komunikiPage = { fontsReady, shown };

    const loaded = new Promise((resolve) => {
        if (document.readyState === 'complete') {
            resolve();
        } else {
            window.addEventListener('load', resolve, { once: true });
        }
    });

    const show = () => {
        if (root.dataset.edPage === 'loading') {
            delete root.dataset.edPage;
        }
        markShown();
    };

    // Os scripts com defer, inclusive o reveal, já rodaram quando o DOMContentLoaded dispara.
    document.addEventListener('DOMContentLoaded', () => {
        const waits = [fontsReady, loaded, window.komunikiReveal?.ready];
        const stage = document.querySelector('[data-particles]');
        if (stage && !('particlesReady' in stage.dataset)) {
            waits.push(new Promise((resolve) => stage.addEventListener('komuniki:particles-ready', resolve, { once: true })));
        }
        const cap = new Promise((resolve) => setTimeout(resolve, Math.max(0, MAX_WAIT - performance.now())));
        Promise.race([Promise.all(waits), cap]).then(show);
    });

    // Voltar pelo histórico restaura a página como ela saiu, esmaecida.
    window.addEventListener('pageshow', (event) => {
        if (event.persisted) {
            delete root.dataset.edPage;
        }
    });

    document.addEventListener('click', (event) => {
        if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
            return;
        }
        const link = event.target.closest('a[href]');
        if (!link) {
            return;
        }
        const url = new URL(link.href, window.location.href);
        const samePage = url.origin === window.location.origin && url.pathname === window.location.pathname
            && url.search === window.location.search;

        // Âncora na mesma página: o botão da Home e "Ver cursos" rolam suavemente; as outras saltam, como antes.
        if (samePage && url.hash) {
            const target = link.hasAttribute('data-smooth-scroll') && document.getElementById(decodeURIComponent(url.hash.slice(1)));
            if (target) {
                event.preventDefault();
                target.scrollIntoView({ behavior: reducedMotion() ? 'auto' : 'smooth', block: 'start' });
                history.pushState(null, '', url.hash);
                // O foco segue a âncora, como no salto nativo, sem interromper a rolagem.
                if (!target.hasAttribute('tabindex')) {
                    target.setAttribute('tabindex', '-1');
                }
                target.focus({ preventScroll: true });
            }
            return;
        }

        if (url.origin !== window.location.origin || !/^https?:$/.test(url.protocol)
            || (link.target && link.target !== '_self') || link.hasAttribute('download') || reducedMotion()) {
            return;
        }
        event.preventDefault();
        if (root.dataset.edPage !== 'leaving') {
            root.dataset.edPage = 'leaving';
            setTimeout(() => window.location.assign(url.href), FADE_OUT);
        }
    });
})();

document.addEventListener('alpine:init', () => {
    const readPreference = (key, fallback) => {
        try { return localStorage.getItem(key) || fallback; } catch (_) { return fallback; }
    };
    const savePreference = (key, value) => {
        try { localStorage.setItem(key, value); } catch (_) { /* Private browsing remains usable. */ }
    };
    Alpine.data('schoolEditorial', () => ({
        theme: readPreference('theme', 'light') === 'dark' ? 'dark' : 'light',
        lang: readPreference('lang', 'pt') === 'en' ? 'en' : 'pt',
        t(pt, en) { return this.lang === 'en' && en ? en : pt; },
        init() {
            document.documentElement.classList.toggle('dark', this.theme === 'dark');
            document.documentElement.lang = this.lang === 'en' ? 'en' : 'pt-BR';
            this.$watch('theme', value => {
                savePreference('theme', value);
                document.documentElement.classList.toggle('dark', value === 'dark');
            });
            this.$watch('lang', value => {
                savePreference('lang', value);
                document.documentElement.lang = value === 'en' ? 'en' : 'pt-BR';
            });
        }
    }));
});
