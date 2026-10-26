// Optional browser verification using only the fictional automatic preparation.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

async function main() {
  const input = process.env.CAREER_INTERVIEW_HTML;
  if (!input) throw Error('Set CAREER_INTERVIEW_HTML to a generated fictional preparation.');
  const output = process.env.CAREER_CONTEXT_QA_DIR || await fs.mkdtemp(path.join(os.tmpdir(), 'career-interview-qa-'));
  await fs.mkdir(output, { recursive: true });
  const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {}) });
  const receipt = { widths: [], checks: [], externalRequests: [], errors: [] };
  function observe(page) {
    page.on('pageerror', error => receipt.errors.push(error.message));
    page.on('request', request => { if (/^https?:/.test(request.url())) receipt.externalRequests.push(request.url()); });
  }
  const url = pathToFileURL(path.resolve(input)).href;
  async function navigate(page, step, id) {
    await page.evaluate(hash => { location.hash = hash; }, '#' + step + (id ? '/' + id : ''));
    await page.locator('#' + step).waitFor({ state: 'visible' });
    if (id) await page.waitForFunction(value => document.querySelector('.section.current select').value === value, id);
  }
  try {
    const context = await browser.newContext({ reducedMotion: 'reduce' });
    // No persistence API is required for a fully prepared portable file.
    await context.addInitScript(() => Object.defineProperty(window, 'localStorage', { get() { throw Error('Unavailable storage'); } }));
    const page = await context.newPage();
    observe(page);
    await page.goto(url);
    const seed = JSON.parse(await page.locator('#interview-preparation-data').textContent());
    assert.equal(seed.synthetic, true, 'Use only fictional input for this check');
    assert.equal(seed.reviewStatus, 'draft');
    assert.equal(await page.locator('#synthetic-note').isVisible(), true);
    assert.equal(await page.locator('input,form,[data-field]').count(), 0);
    assert.equal(await page.locator('.top,.eyebrow,.lede').count(), 0);
    assert.equal(await page.locator('.signals h3 a').count(), seed.signals.length);
    assert.equal(await page.locator('.selection-notes').getAttribute('open'), null);
    assert.equal(await page.locator('#story-picker').inputValue(), seed.leadStoryIds[0]);
    for (const width of [1440, 768, 375, 320]) {
      await page.setViewportSize({ width, height: width < 500 ? 900 : 1100 });
      for (const step of ['signal', 'stories', 'opening', 'decode', 'chapters', 'pace']) {
        await navigate(page, step);
        assert.equal(await page.locator('.section:visible').count(), 1);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, 'Overflow: ' + width + '/' + step);
      }
      await navigate(page, 'signal');
      await page.screenshot({ path: path.join(output, 'automatic-' + width + '.png'), fullPage: true });
      await navigate(page, 'decode');
      await page.screenshot({ path: path.join(output, 'answers-' + width + '.png'), fullPage: true });
      receipt.widths.push(width);
    }
    receipt.checks.push('All six sections start populated at desktop, tablet and mobile widths; no manual intake or storage dependency');
    await page.setViewportSize({ width: 1440, height: 1100 });
    for (const story of seed.stories) {
      await navigate(page, 'stories', story.id);
      const panel = page.locator('#stories [data-story-panel="' + story.id + '"]');
      for (const key of ['contribution', 'sharedCredit', 'outcome']) {
        assert((await panel.innerText()).includes(story.account[key]));
      }
      await panel.locator('[data-sources]').click();
      await page.locator('#reader').waitFor({ state: 'visible' });
      assert.equal(await page.locator('#reader .source').count(), story.evidence.length);
      for (const source of story.evidence) {
        assert((await page.locator('#reader-body').innerText()).includes(source.content));
        assert((await page.locator('#reader-body').innerText()).includes(source.scope));
      }
      await page.keyboard.press('Escape');
      assert(await panel.locator('[data-sources]').evaluate(e => e === document.activeElement));
      await panel.locator('a[href^="#chapters/"]').click();
      await page.locator('#chapters').waitFor({ state: 'visible' });
      assert.equal(await page.locator('#chapter-picker').inputValue(), story.id);
      // A delayed dialog close event must not steal focus after navigation.
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      assert(await page.locator('#content').evaluate(e => e === document.activeElement));
      assert.equal(await page.locator('#chapters .is-selected .chapters>li').count(), story.chapters.length);
      await page.locator('#chapters .is-selected a[href^="#pace/"]').click();
      await page.locator('#pace').waitFor({ state: 'visible' });
      assert.equal(await page.locator('#pace-picker').inputValue(), story.id);
      assert.equal(await page.locator('#pace .is-selected .pace>li').count(), story.timeline.length);
      await page.reload();
      assert.equal(await page.locator('#pace-picker').inputValue(), story.id);
      await page.goBack();
      await page.locator('#chapters').waitFor({ state: 'visible' });
      assert.equal(await page.locator('#chapter-picker').inputValue(), story.id);
    }
    receipt.checks.push('Original contribution, shared credit, outcome and source text are intact; sources, chapters, timelines, focus, reload and Back remain connected');
    for (const question of seed.questions) {
      await navigate(page, 'decode', question.id);
      assert((await page.locator('#decode .is-selected .answer').innerText()).includes(question.answer));
      await page.locator('#decode [data-selected-route=chapters]').click();
      await page.locator('#chapters').waitFor({ state: 'visible' });
      assert.equal(await page.locator('#chapter-picker').inputValue(), question.storyId);
    }
    await navigate(page, 'decode', seed.questions[0].id);
    await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: () => Promise.reject(Error('Clipboard unavailable')) } }));
    await page.locator('#decode .is-selected [data-copy=answer]').click();
    const copiedAnswer = await page.locator('#manual-copy').inputValue();
    assert(copiedAnswer.startsWith('Fictional example.'));
    assert(copiedAnswer.includes(seed.questions[0].question));
    assert(copiedAnswer.includes(seed.questions[0].answer));
    for (const limit of seed.stories.find(s => s.id === seed.questions[0].storyId).account.limits) assert(copiedAnswer.includes(limit));
    await page.keyboard.press('Escape');
    await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async text => { window.copiedText = text; } } }));
    await page.locator('#decode .is-selected [data-copy=answer]').click();
    assert.equal(await page.evaluate(() => window.copiedText), copiedAnswer);
    await navigate(page, 'opening');
    await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: () => Promise.reject(Error('Clipboard unavailable')) } }));
    await page.locator('[data-copy=opening]').click();
    const opening = await page.locator('#manual-copy').inputValue();
    assert(opening.startsWith('Fictional example.'));
    assert(opening.endsWith(seed.opening.join('\n\n')));
    await page.keyboard.press('Escape');
    await page.locator('#coach-copy').click();
    const handoff = await page.locator('#manual-copy').inputValue();
    assert(handoff.startsWith('Fictional example.'));
    assert(handoff.includes('Do not ask me to fill in a worksheet'));
    assert.deepEqual(JSON.parse(handoff.slice(handoff.indexOf('{'))), seed);
    await page.keyboard.press('Escape');
    await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async text => { window.copiedText = text; } } }));
    await page.locator('[data-copy=opening]').click();
    assert.equal(await page.evaluate(() => window.copiedText), opening);
    receipt.checks.push('Drafted answers map to their stories; copy success and fallback preserve the exact prepared packet and fictional label');
    await page.screenshot({ path: path.join(output, 'opening-desktop.png'), fullPage: true });
    await page.setViewportSize({ width: 320, height: 900 });
    await page.selectOption('#view-select', 'stories');
    await page.locator('#stories').waitFor({ state: 'visible' });
    await page.selectOption('#story-picker', seed.stories.at(-1).id);
    await page.waitForURL(new RegExp('#stories/' + seed.stories.at(-1).id + '$'));
    await page.locator('#stories .is-selected .story-heading h2').evaluate(e => { e.textContent = 'LongTitle'.repeat(100); });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false);
    await page.locator('.skip').focus();
    await page.keyboard.press('Enter');
    assert(await page.locator('#content').evaluate(e => e === document.activeElement));
    assert.equal(await page.locator('.arrow').first().evaluate(e => getComputedStyle(e).transitionDuration), '0s');
    await page.reload();
    await page.emulateMedia({ media: 'print' });
    assert.equal(await page.locator('.section:visible').count(), 6);
    assert(await page.locator('#synthetic-note').isVisible());
    assert(await page.locator('.heading').isVisible());
    assert(await page.locator('#decode .answer-notes').first().evaluate(e => e.open));
    assert(await page.locator('#chapters .evidence-limits').first().evaluate(e => e.open));
    for (const question of seed.questions) {
      const title = page.locator('[data-question-panel="' + question.id + '"] .question-title');
      assert(await title.isVisible());
      assert.equal(await title.innerText(), question.question);
    }
    await page.emulateMedia({ media: 'screen' });
    const staticContext = await browser.newContext({ javaScriptEnabled: false });
    const staticPage = await staticContext.newPage();
    observe(staticPage);
    await staticPage.goto(url);
    assert.equal(await staticPage.locator('.section:visible').count(), 6);
    for (const question of seed.questions) {
      const title = staticPage.locator('[data-question-panel="' + question.id + '"] .question-title');
      assert(await title.isVisible());
      assert.equal(await title.innerText(), question.question);
    }
    assert((await staticPage.locator('#opening').innerText()).includes(seed.opening[0]));
    await staticPage.locator('#stories details.original-account').first().locator('summary').click();
    assert((await staticPage.locator('#stories details.original-account').first().innerText()).includes(seed.stories[0].evidence[0].content));
    await staticContext.close();
    // Copy the standalone file to an unrelated location and open in a fresh context.
    const relocated = path.join(output, 'relocated-preparation.html');
    await fs.copyFile(input, relocated);
    const freshContext = await browser.newContext();
    const freshPage = await freshContext.newPage();
    observe(freshPage);
    await freshPage.goto(pathToFileURL(relocated).href);
    assert.deepEqual(JSON.parse(await freshPage.locator('#interview-preparation-data').textContent()), seed);
    assert(await freshPage.locator('#signal').isVisible());
    await freshContext.close();
    receipt.checks.push('Long titles, mobile selectors, keyboard, reduced motion, print labels, no-JavaScript sources and independent file reopening pass');
    assert.deepEqual(receipt.errors, []);
    assert.deepEqual(receipt.externalRequests, []);
    receipt.passed = true;
    await fs.writeFile(path.join(output, 'automatic-interview-checks.json'), JSON.stringify(receipt, null, 2) + '\n');
    console.log(JSON.stringify(receipt, null, 2));
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
