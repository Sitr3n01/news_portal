// Deterministic controller tests. Browser rendering is covered by motion_e2e.mjs.
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const source = readFileSync(resolve(__dirname, '../../static/js/school-editorial-motion.js'), 'utf8');

function fixture({ reduce = false, observers = true, storageFails = false } = {}) {
    const callbacks = {};
    const frames = [];
    const intersections = [];
    const mutations = [];
    const stored = new Map();
    const element = (top = 0, bottom = 1500, height = 100) => ({
        dataset: {}, attributes: {}, values: {}, top, bottom, height,
        getBoundingClientRect() { return { top: this.top, bottom: this.bottom, height: this.height, width: 1000 }; },
        style: {
            setProperty(name, value) { this[name] = value; },
            removeProperty(name) { delete this[name]; },
        },
        setAttribute(name, value) { this.attributes[name] = value; },
        addEventListener(name, callback) { this[name] = callback; },
    });
    const classes = new Set(['ed-root']);
    const root = { classList: { contains: name => classes.has(name), add: name => classes.add(name) }, clientHeight: 1000 };
    const nav = element(0, 128, 128);
    const heading = element(800);
    const canvas = element(-2000, 5000);
    canvas.dataset.edTheme = 'canvas';
    const contrast = element(1100, 1600);
    contrast.dataset.edTheme = 'contrast';
    const footer = element(1700, 2500);
    footer.dataset.edTheme = 'dark';
    const art = element();
    const button = element();
    const media = { matches: reduce, addEventListener(name, callback) { this[name] = callback; } };
    const document = {
        documentElement: root, hidden: false,
        querySelector: selector => ({ '.ed-nav': nav, '.ed-hero-art': art, '[data-ed-motion-toggle]': button, main: canvas })[selector],
        querySelectorAll: selector => selector === '[data-ed-reveal]' ? [heading] : [canvas, contrast, footer],
        addEventListener(name, callback) { callbacks[name] = callback; },
    };
    const window = { addEventListener(name, callback) { callbacks[name] = callback; } };
    class IntersectionObserver {
        constructor(callback) { this.callback = callback; this.targets = []; intersections.push(this); }
        observe(target) { this.targets.push(target); }
    }
    class MutationObserver {
        constructor(callback) { mutations.push(callback); }
        observe() {}
    }
    class ResizeObserver { observe() {} }
    if (observers) Object.assign(window, { IntersectionObserver, ResizeObserver });
    vm.runInNewContext(source, {
        document, window, matchMedia: () => media,
        getComputedStyle: () => ({ getPropertyValue: () => '' }),
        requestAnimationFrame: callback => { frames.push(callback); return frames.length; },
        IntersectionObserver, MutationObserver, ResizeObserver,
        localStorage: {
            getItem(key) { if (storageFails) throw Error('blocked'); return stored.get(key); },
            setItem(key, value) { if (storageFails) throw Error('blocked'); stored.set(key, value); },
        },
    });
    function flush() { while (frames.length) frames.shift()(); }
    flush();
    return { root, nav, heading, contrast, footer, art, button, media, callbacks, frames, intersections, mutations, classes, document, stored, flush };
}

test('reveal follows viewport progress in both directions, with no temporal fade', () => {
    const f = fixture();
    for (const [top, minimum, maximum] of [[850, .15, .15], [800, .15, .15], [700, .4, .5], [650, .7, .8], [600, 1, 1], [300, 1, 1], [700, .4, .5]]) {
        f.heading.top = top;
        f.callbacks.scroll(); f.flush();
        const opacity = Number(f.heading.style['--ed-reveal-opacity']);
        assert.ok(opacity >= minimum && opacity <= maximum, `${top}: ${opacity}`);
    }
});

test('scroll and resize events coalesce, and idle has no animation frame loop', () => {
    const f = fixture();
    for (let i = 0; i < 25; i++) { f.callbacks.scroll(); f.callbacks.resize(); }
    assert.equal(f.frames.length, 1);
    f.flush(); assert.equal(f.frames.length, 0);
});

test('semantic contrast region follows global theme and footer stays dark', () => {
    const f = fixture();
    assert.equal(f.nav.dataset.surface, 'light');
    f.contrast.top = 50; f.callbacks.scroll(); f.flush();
    assert.equal(f.nav.dataset.surface, 'dark');
    f.classes.add('dark'); f.mutations[0](); f.flush();
    assert.equal(f.nav.dataset.surface, 'light');
    f.footer.top = 50; f.callbacks.scroll(); f.flush();
    assert.equal(f.nav.dataset.surface, 'dark');
});

test('reduced motion clears reveal and stops art, including live preference changes', () => {
    const f = fixture({ reduce: true });
    f.intersections[1].callback([{ isIntersecting: true }]);
    assert.equal(f.art.dataset.motionPlaying, 'false');
    assert.equal(f.heading.style['--ed-reveal-opacity'], undefined);
    f.media.matches = false; f.media.change(); f.flush();
    assert.equal(f.art.dataset.motionPlaying, 'true');
    assert.equal(f.heading.style['--ed-reveal-opacity'], '0.1500');
    f.media.matches = true; f.media.change(); f.flush();
    assert.equal(f.heading.style['--ed-reveal-opacity'], undefined);
    assert.equal(f.art.dataset.motionPlaying, 'false');
});

test('art pauses offscreen, in background, and through a persistent keyboard-accessible button', () => {
    const f = fixture();
    f.intersections[1].callback([{ isIntersecting: true }]);
    assert.equal(f.art.dataset.motionPlaying, 'true');
    f.document.hidden = true; f.callbacks.visibilitychange();
    assert.equal(f.art.dataset.motionPlaying, 'false');
    f.document.hidden = false; f.callbacks.visibilitychange(); f.flush();
    f.button.click();
    assert.equal(f.art.dataset.motionPlaying, 'false');
    assert.equal(f.button.attributes['aria-pressed'], 'true');
    assert.equal(f.stored.get('komuniki-art-paused'), 'true');
    f.button.click(); f.intersections[1].callback([{ isIntersecting: false }]);
    assert.equal(f.art.dataset.motionPlaying, 'false');
});

test('large scroll jumps reset offscreen headings and recompute on reentry', () => {
    const f = fixture();
    f.intersections[0].callback([{ target: f.heading, isIntersecting: false, boundingClientRect: { top: -100 } }]);
    f.flush(); assert.equal(f.heading.style['--ed-reveal-opacity'], '1');
    f.heading.top = 700;
    f.intersections[0].callback([{ target: f.heading, isIntersecting: true }]);
    f.flush(); assert.ok(Number(f.heading.style['--ed-reveal-opacity']) <= .5);
});

test('missing observers and blocked storage keep navigation usable and art static', () => {
    const f = fixture({ observers: false, storageFails: true });
    f.button.click(); f.callbacks.scroll(); f.flush();
    assert.equal(f.art.dataset.motionPlaying, 'false');
    assert.equal(f.nav.dataset.surface, 'light');
});
