// Run through the documented CUA browser runtime, passing its tab and viewport handles.
// Browser evaluations only read rendered DOM state; actions use real browser controls.
import { appendFile, mkdir, writeFile } from 'node:fs/promises';

export const VIEWPORTS = [
  [280, 653], [320, 568], [360, 640], [375, 667], [390, 844], [412, 915], [430, 932],
  [568, 320], [667, 375], [844, 390], [932, 430],
  [600, 960], [768, 1024], [820, 1180], [1024, 768], [1180, 820],
  [1280, 720], [1366, 768], [1440, 900], [1536, 864], [1920, 1080],
  [2560, 1440], [3440, 1440], [3840, 2160], [4096, 1440],
  [399, 844], [400, 844], [639, 960], [640, 960], [641, 960],
  [767, 1024], [769, 1024], [1023, 768], [1025, 768],
  [1100, 820], [1101, 820], [1599, 900], [1600, 900],
].map(([width, height]) => ({ width, height }));

export async function preferences(tab, dark, language) {
  const state = await tab.playwright.evaluate(() => ({
    dark: document.documentElement.classList.contains('dark'),
    language: document.documentElement.lang,
  }));
  if (state.dark !== dark) {
    await tab.playwright.locator('.ed-nav-controls button[aria-pressed]').click();
  }
  if (state.language !== language) {
    await tab.playwright.locator('.ed-language').click();
  }
}

async function pageState(tab, viewport, dark, language, label) {
  const state = await tab.playwright.evaluate(() => {
    const doc = document.documentElement;
    const brand = document.querySelector('.ed-brand').getBoundingClientRect();
    const controls = document.querySelector('.ed-nav-right').getBoundingClientRect();
    const h1 = document.querySelector('h1');
    return {
      clientWidth: doc.clientWidth,
      scrollWidth: doc.scrollWidth,
      clientHeight: doc.clientHeight,
      dark: doc.classList.contains('dark'),
      language: doc.lang,
      title: h1?.textContent.trim(),
      fontsLoaded: document.fonts.check('700 48px "Barlow Condensed"'),
      horizontalOverflow: doc.scrollWidth > doc.clientWidth + 1,
      navigationOverlap: brand.right > controls.left + 1,
      clippedBrand: document.querySelector('.ed-brand').scrollWidth > document.querySelector('.ed-brand').clientWidth + 2,
      clippedContainers: [...document.querySelectorAll('main .ed-panel,main .ed-card,form')]
        .filter(e => e.clientWidth > 0 && e.scrollWidth > e.clientWidth + 2)
        .map(e => ({ element: e.tagName, classes: e.className, width: e.clientWidth, scrollWidth: e.scrollWidth })),
      inputOverflow: [...document.querySelectorAll('.contact-control')]
        .filter(e => {
          const box = e.getBoundingClientRect();
          return box.right > doc.clientWidth + 1 || box.left < -1;
        }).map(e => e.name),
      mobileMenuVisible: getComputedStyle(document.querySelector('.ed-nav-menu-button')).display !== 'none',
      visibleSocialCards: [...document.querySelectorAll('a[href="http://127.0.0.1:8012/demonstracao-editorial/"]')]
        .filter(e => e.getBoundingClientRect().width > 0).length,
    };
  });
  state.passed = (
    state.clientWidth <= viewport.width && state.clientWidth >= viewport.width - 20
    && !state.horizontalOverflow && !state.navigationOverlap && !state.clippedBrand && !state.clippedContainers.length
    && !state.inputOverflow.length && !!state.title && state.fontsLoaded
    && state.dark === dark && state.language === language
    && state.mobileMenuVisible === (viewport.width < 1024)
  );
  return { label, url: await tab.url(), ...state };
}

async function navigate(tab, path, viewport, results) {
  if (viewport.width < 1024) {
    await tab.playwright.locator('.ed-nav-menu-button').click();
    const expanded = await tab.playwright.locator('.ed-nav-menu-button').getAttribute('aria-expanded');
    await tab.pressKey('Escape');
    const escape = await tab.playwright.evaluate(() => ({
      closed: document.querySelector('.ed-nav-menu-button').getAttribute('aria-expanded') === 'false',
      focused: document.activeElement?.getAttribute('aria-controls') === 'school-mobile-menu',
    }));
    results.push({ check: 'Menu open and keyboard Escape', passed: expanded === 'true' && escape.closed && escape.focused });
    await tab.playwright.locator('.ed-nav-menu-button').click();
    await tab.playwright.locator('#school-mobile-menu a[href="' + path + '"]').click();
  } else {
    await tab.playwright.locator('.ed-nav-links a[href="' + path + '"]').click();
  }
  results.push({ check: 'Navigate ' + path, passed: (await tab.url()).endsWith(path) });
}

export async function runFlow(tab, viewportControl, viewport, dark, language, outputDirectory, runName) {
  const record = { viewport, dark, language, pages: [], interactions: [], runName };
  try {
    await viewportControl.set(viewport);
    await tab.goto('http://127.0.0.1:8011/');
    await preferences(tab, dark, language);
    await tab.reload();
    record.pages.push(await pageState(tab, viewport, dark, language, 'Home current'));
    await tab.playwright.locator('.ed-brand').press('Tab');
    const keyboard = await tab.playwright.evaluate(() => ({
      focusedElement: document.activeElement?.tagName,
      outline: getComputedStyle(document.activeElement).outlineStyle,
    }));
    record.interactions.push({ check: 'Keyboard focus visible', ...keyboard, passed: keyboard.outline !== 'none' });

    await navigate(tab, '/sobre/', viewport, record.interactions);
    record.pages.push(await pageState(tab, viewport, dark, language, 'About current'));
    await navigate(tab, '/cursos/', viewport, record.interactions);
    record.pages.push(await pageState(tab, viewport, dark, language, 'Courses current'));
    await tab.playwright.locator('a[href="#grade-cursos"]').click();
    const catalog = await tab.playwright.evaluate(() => ({
      top: document.querySelector('#grade-cursos').getBoundingClientRect().top,
      cards: document.querySelectorAll('#grade-cursos article').length,
    }));
    record.interactions.push({
      check: 'Catalog anchor and six courses', ...catalog,
      passed: (await tab.url()).endsWith('#grade-cursos') && catalog.cards === 6
        && catalog.top >= 100 && catalog.top < viewport.height - 24,
    });
    // Course CTA is a real internal link; the fixed header does not intercept it.
    await tab.playwright.locator('main a[href="/contact/"]').first().click();
    record.pages.push(await pageState(tab, viewport, dark, language, 'Contact current'));
    await tab.playwright.locator('.contact-form button[type="submit"]').click();
    const required = await tab.playwright.evaluate(() => ({
      focused: document.activeElement?.id,
      invalid: [...document.querySelectorAll('.contact-control:invalid')].map(e => e.name),
    }));
    record.interactions.push({
      check: 'Required fields', ...required,
      passed: required.focused === 'id_name'
        && ['name', 'email', 'message'].every(name => required.invalid.includes(name)),
    });
    await tab.playwright.locator('#id_name').fill('E2E local - invalid form');
    await tab.playwright.locator('#id_email').fill('not-an-email');
    await tab.playwright.locator('#id_message').fill('This invalid submission must stay in the browser.');
    await tab.playwright.locator('.contact-form button[type="submit"]').click();
    const invalidEmail = await tab.playwright.evaluate(() => ({
      focused: document.activeElement?.id,
      invalid: document.querySelector('#id_email').matches(':invalid'),
    }));
    record.interactions.push({
      check: 'Invalid email prevents submission', ...invalidEmail,
      passed: invalidEmail.focused === 'id_email' && invalidEmail.invalid,
    });
    await tab.playwright.locator('.ed-footer a[href="/privacidade/"]').click();
    record.pages.push(await pageState(tab, viewport, dark, language, 'Privacy current'));
    await tab.playwright.locator('.ed-footer-brand').click();
    record.interactions.push({ check: 'Footer returns home', passed: (await tab.url()) === 'http://127.0.0.1:8011/' });

    await tab.goto('http://127.0.0.1:8012/');
    await preferences(tab, dark, language);
    const demo = await pageState(tab, viewport, dark, language, 'Home demo');
    record.pages.push(demo);
    record.interactions.push({
      check: 'Demo post visibility limit',
      actual: demo.visibleSocialCards,
      passed: demo.visibleSocialCards === (viewport.width < 640 ? 3 : 6),
    });
    await tab.goto('http://127.0.0.1:8012/demonstracao-editorial/');
    record.pages.push(await pageState(tab, viewport, dark, language, 'CMS long title demo'));
  } catch (error) {
    record.error = String(error).slice(0, 1000);
  }
  record.passed = !record.error && record.pages.length === 7
    && record.pages.every(page => page.passed) && record.interactions.every(check => check.passed);
  await mkdir(outputDirectory, { recursive: true });
  if (!record.passed) {
    const filename = runName + '-' + viewport.width + 'x' + viewport.height + '-' + dark + '-' + language + '.png';
    try {
      await writeFile(outputDirectory + '/' + filename, await tab.getScreenshot({ emit: false }));
      record.failureScreenshot = filename;
    } catch (error) {
      record.screenshotError = String(error).slice(0, 1000);
    }
  }
  await appendFile(outputDirectory + '/' + runName + '.jsonl', JSON.stringify(record) + '\n');
  return record;
}
