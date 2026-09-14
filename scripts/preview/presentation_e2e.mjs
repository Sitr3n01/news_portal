// Static presentation audit through documented CUA tab/viewport handles.
import { appendFile } from 'node:fs/promises';
import { preferences, VIEWPORTS } from './browser_e2e.mjs';
export { VIEWPORTS };

export async function runCase(tab, viewportControl, viewport, dark, lang, output) {
    const report = { viewport, dark, lang, pages: [], interactions: [] };
    await viewportControl.set(viewport);
    for (const path of ['/', '/sobre/', '/cursos/', '/contact/', '/privacidade/']) {
        await tab.goto('http://127.0.0.1:8012' + path);
        await preferences(tab, dark, lang);
        const state = await tab.playwright.evaluate(() => {
            const doc = document.documentElement;
            const box = document.querySelector('.ed-brand').getBoundingClientRect();
            const controls = document.querySelector('.ed-nav-right').getBoundingClientRect();
            return {
                motionControllerRemoved: !doc.classList.contains('ed-motion-ready')
                    && !document.querySelector('[data-ed-motion-toggle],script[src*="school-editorial-motion"]'),
                width: doc.clientWidth, height: doc.clientHeight,
                overflow: doc.scrollWidth > doc.clientWidth + 1,
                overlap: box.right > controls.left + 1,
                heading: getComputedStyle(document.querySelector('h1')).opacity,
                theme: doc.classList.contains('dark'), lang: doc.lang,
                hiddenHeadings: [...document.querySelectorAll('main h1,main h2,main h3')].some(e => getComputedStyle(e).opacity !== '1'),
                animated: [...document.querySelectorAll('.ed-school,.ed-school *')].some(e => {
                    const css = getComputedStyle(e);
                    return css.animationName !== 'none' || css.transitionDuration.split(',').some(duration => duration.trim() !== '0s');
                }),
                scrollBehavior: getComputedStyle(doc).scrollBehavior,
                emailBackground: getComputedStyle(document.querySelector('.ed-footer a[href^="mailto:"]')).backgroundColor,
                emailColor: getComputedStyle(document.querySelector('.ed-footer a[href^="mailto:"]')).color,
                officialEmail: !!document.querySelector('.ed-footer a[href="mailto:komunikicomunicacao@gmail.com"]'),
                clipped: [...document.querySelectorAll('main .ed-card,main .ed-panel,form')].some(e => e.clientWidth > 0 && e.scrollWidth > e.clientWidth + 2),
                menu: getComputedStyle(document.querySelector('.ed-nav-menu-button')).display !== 'none',
            };
        });
        state.passed = state.motionControllerRemoved && !state.overflow && !state.overlap && !state.clipped
            && !state.hiddenHeadings && !state.animated && state.scrollBehavior === 'auto' && state.officialEmail
            && state.emailBackground === 'rgb(11, 58, 117)' && state.emailColor === 'rgb(255, 255, 255)'
            && state.heading === '1' && state.theme === dark && state.lang === (lang === 'pt' ? 'pt-BR' : lang)
            && state.menu === (viewport.width < 1024) && Math.abs(state.width - viewport.width) <= 20;
        report.pages.push({ path, ...state });
    }
    if (viewport.width < 1024) {
        await tab.playwright.locator('.ed-nav-menu-button').click();
        const opened = await tab.playwright.locator('.ed-nav-menu-button').getAttribute('aria-expanded');
        await tab.pressKey('Escape');
        report.interactions.push(await tab.playwright.evaluate(() => ({
            name: 'mobile menu / Escape / focus',
            passed: document.querySelector('.ed-nav-menu-button').getAttribute('aria-expanded') === 'false'
                && document.activeElement === document.querySelector('.ed-nav-menu-button'),
        })));
        report.interactions.push({ name: 'menu opened', passed: opened === 'true' });
    }
    report.passed = report.pages.every(p => p.passed) && report.interactions.every(p => p.passed);
    await appendFile(output, JSON.stringify(report) + '\n');
    return { width: viewport.width, dark, lang, passed: report.passed };
}
