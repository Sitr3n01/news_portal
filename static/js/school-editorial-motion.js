/* Progressive enhancement: content is fully visible before this controller runs. */
(() => {
    const root = document.documentElement;
    const nav = document.querySelector('.ed-nav');
    if (!root.classList.contains('ed-root') || !nav) return;

    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const headings = [...document.querySelectorAll('[data-ed-reveal]')];
    const surfaces = [...document.querySelectorAll('[data-ed-theme]')];
    const art = document.querySelector('.ed-hero-art');
    const motionButton = document.querySelector('[data-ed-motion-toggle]');
    const visibleHeadings = new Set(headings);
    const tokens = getComputedStyle(root);
    const number = (name, fallback) => parseFloat(tokens.getPropertyValue(name)) || fallback;
    const start = number('--motion-reveal-start', .8);
    const end = number('--motion-reveal-end', .6);
    const hidden = number('--motion-opacity-hidden', .15);
    const curve = number('--motion-reveal-curve', 1.28);
    let frame = 0;
    let artVisible = false;
    let paused = false;
    try { paused = localStorage.getItem('komuniki-art-paused') === 'true'; } catch (_) { /* Optional preference. */ }

    function syncArt() {
        if (!art) return;
        art.dataset.motionPlaying = String(artVisible && !paused && !reduced.matches && !document.hidden);
        if (motionButton) motionButton.setAttribute('aria-pressed', String(paused));
    }

    function render() {
        frame = 0;
        if (document.hidden) return;
        // Read every rectangle before writing styles; one frame serves all components.
        const height = document.documentElement.clientHeight;
        const navBox = nav.getBoundingClientRect();
        const probe = navBox.top + navBox.height / 2;
        const regions = surfaces.map(element => ({ element, box: element.getBoundingClientRect() }));
        const values = reduced.matches ? [] : [...visibleHeadings].map(element => {
            const top = element.getBoundingClientRect().top;
            const progress = Math.max(0, Math.min(1, (start * height - top) / ((start - end) * height)));
            return { element, opacity: hidden + (1 - hidden) * progress ** curve };
        });
        const dark = root.classList.contains('dark');
        let theme = dark ? 'dark' : 'light';
        // Semantic regions can nest. The last matching region is the deepest surface.
        for (const { element, box } of regions) {
            if (box.width && box.top <= probe && box.bottom > probe) {
                const semantic = element.dataset.edTheme;
                theme = semantic === 'contrast' ? (dark ? 'light' : 'dark')
                    : semantic === 'canvas' ? (dark ? 'dark' : 'light') : semantic;
            }
        }
        if (nav.dataset.surface !== theme) nav.dataset.surface = theme;
        for (const { element, opacity } of values) {
            element.style.setProperty('--ed-reveal-opacity', opacity.toFixed(4));
        }
    }

    function schedule() {
        if (!frame && !document.hidden) frame = requestAnimationFrame(render);
    }

    function syncPreference() {
        if (reduced.matches) {
            headings.forEach(element => element.style.removeProperty('--ed-reveal-opacity'));
        }
        syncArt();
        schedule();
    }

    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver(entries => {
            for (const entry of entries) {
                if (entry.isIntersecting) visibleHeadings.add(entry.target);
                else {
                    visibleHeadings.delete(entry.target);
                    // Reset outside the viewport, including large jumps and reverse scrolling.
                    entry.target.style.setProperty('--ed-reveal-opacity', entry.boundingClientRect.top < 0 ? '1' : String(hidden));
                }
            }
            schedule();
        }, { rootMargin: '100px 0px' });
        headings.forEach(element => observer.observe(element));
        if (art) {
            const artObserver = new IntersectionObserver(entries => {
                artVisible = entries[0].isIntersecting;
                syncArt();
            });
            artObserver.observe(art);
        }
    } else {
        // Old browsers retain native scrolling/reveal and a static decorative image.
        artVisible = false;
    }

    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule, { passive: true });
    window.addEventListener('pageshow', schedule);
    document.addEventListener('visibilitychange', () => { syncArt(); schedule(); });
    document.addEventListener('focusin', schedule);
    reduced.addEventListener('change', syncPreference);
    new MutationObserver(schedule).observe(root, { attributes: true, attributeFilter: ['class', 'lang'] });
    if ('ResizeObserver' in window) {
        const resize = new ResizeObserver(schedule);
        resize.observe(document.querySelector('main'));
        resize.observe(nav);
    }
    document.fonts?.ready.then(schedule);
    motionButton?.addEventListener('click', () => {
        paused = !paused;
        try { localStorage.setItem('komuniki-art-paused', String(paused)); } catch (_) { /* Optional preference. */ }
        syncArt();
    });
    syncPreference();
    root.classList.add('ed-motion-ready');
})();
