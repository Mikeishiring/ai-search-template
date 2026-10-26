// Optional rendered check: requires Playwright and an installed Chromium browser.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

async function main() {
  const root = path.resolve(__dirname, '..');
  const output = process.env.CAREER_CONTEXT_QA_DIR || await fs.mkdtemp(path.join(os.tmpdir(), 'career-context-qa-'));
  const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {}) });
  const receipt = { widths: [], checks: [], externalRequests: [], errors: [] };
  const url = pathToFileURL(process.env.CAREER_CONTEXT_HTML || path.join(root, 'CAREER-CONTEXT.html')).href;
  try {
    const context = await browser.newContext({ acceptDownloads: true, viewport: { width: 1440, height: 1100 } });
    const page = await context.newPage();
    page.on('pageerror', error => receipt.errors.push(error.message));
    page.on('request', request => { if (/^https?:/.test(request.url())) receipt.externalRequests.push(request.url()); });
    await page.goto(url);
    const packet = await page.locator('#career-context-data').textContent().then(JSON.parse);
    assert.equal(packet.synthetic, true);
    assert.ok(packet.accounts.length && packet.accounts[0].sourceRefs.length, 'Use a fictional sheet with an account and source reference for interaction checks');
    assert.equal(await page.locator('.account').count(), packet.accounts.length);
    const firstSourceId = packet.accounts[0].sourceRefs[0];
    for (const width of [1440, 768, 375, 320]) {
      await page.setViewportSize({ width, height: width < 500 ? 900 : 1100 });
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
      assert.equal(overflow, false, `Horizontal overflow at ${width}`);
      await page.screenshot({ path: path.join(output, `sheet-${width}.png`), fullPage: width < 500 });
      receipt.widths.push(width);
    }
    await page.setViewportSize({ width: 1440, height: 1100 });
    await page.getByRole('button', { name: 'View agent text', exact: true }).click();
    const agentText = await page.locator('#agent-text').inputValue();
    assert.match(agentText, /Synthetic demo data/);
    for (const account of packet.accounts) {
      for (const key of ['summary', 'contribution', 'sharedCredit', 'outcome']) assert.ok(agentText.includes(account[key]), `Text export missing ${key}`);
      for (const limit of account.limits) assert.ok(agentText.includes(limit));
    }
    const unquotedAgentText = agentText.replace(/^> /gm, '');
    for (const source of packet.sources) assert.ok(unquotedAgentText.includes(source.content));
    await page.keyboard.press('Escape');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'view-context');
    receipt.checks.push('agent text retains account and source content; dialog Escape restores focus');

    await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async text => { window.copiedContext = text; } } }));
    await page.getByRole('button', { name: 'Copy for an agent', exact: true }).click();
    assert.equal(await page.evaluate(() => window.copiedContext), agentText);
    await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async () => { throw new Error('Clipboard denied'); } } }));
    await page.getByRole('button', { name: 'Copy for an agent', exact: true }).click();
    await page.locator('#context-reader[open]').waitFor();
    assert.match(await page.locator('#reader-note').textContent(), /Clipboard access is unavailable/);
    assert.equal(await page.locator('#agent-text').evaluate(el => el.selectionEnd - el.selectionStart), agentText.length);
    await page.getByRole('button', { name: 'Close', exact: true }).click();
    receipt.checks.push('clipboard success and denied-access fallback');

    // Closing queues a "close" event. A later handler must not steal focus
    // after the user has already moved to another control.
    await page.getByRole('button', { name: 'View agent text', exact: true }).click();
    const focusPreserved = await page.evaluate(() => new Promise(resolve => {
      const dialog = document.querySelector('#context-reader');
      const nextControl = document.querySelector('.context-details summary');
      dialog.addEventListener('close', () => resolve(document.activeElement === nextControl), { once: true });
      dialog.close();
      nextControl.focus();
    }));
    assert.equal(focusPreserved, true, 'Closing the reader stole focus from the next control');
    receipt.checks.push('dialog close preserves a subsequent keyboard focus choice');

    const summary = page.locator('.context-details summary').first();
    await summary.focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('.context-details').first().getAttribute('open'), '');
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('.context-details').first().getAttribute('open'), null);
    await page.keyboard.press('Space');
    await page.locator('.references a').first().click();
    assert.equal(await page.locator('#source-' + firstSourceId).getAttribute('open'), '');
    assert.equal(await page.evaluate(() => document.activeElement.parentElement.id), 'source-' + firstSourceId);
    receipt.checks.push('keyboard disclosures and source navigation');

    const jsonEvent = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download structured context' }).click();
    const jsonDownload = await jsonEvent;
    assert.deepEqual(JSON.parse(await fs.readFile(await jsonDownload.path(), 'utf8')), packet);
    const htmlEvent = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Save HTML', exact: true }).click();
    const htmlDownload = await htmlEvent;
    const saved = path.join(output, 'downloaded-context.html');
    await htmlDownload.saveAs(saved);
    const reopened = await context.newPage();
    await reopened.goto(pathToFileURL(saved).href);
    assert.deepEqual(JSON.parse(await reopened.locator('#career-context-data').textContent()), packet);
    assert.equal(await reopened.locator('#context-reader').getAttribute('open'), null);
    await reopened.getByRole('button', { name: 'View agent text', exact: true }).click();
    assert.equal(await reopened.locator('#agent-text').inputValue(), agentText);
    await reopened.close();
    receipt.checks.push('JSON download matches packet; saved HTML reopens with working controls');

    await page.goto(url + '#source-%');
    await page.emulateMedia({ reducedMotion: 'reduce' });
    assert.equal(await page.locator('.arrow').first().evaluate(el => getComputedStyle(el).transitionDuration), '0s');
    await page.setViewportSize({ width: 320, height: 900 });
    await page.evaluate(() => {
      document.querySelector('.name').textContent = 'Contributor with a very long display name';
      document.querySelector('.account-heading h3').textContent = 'UnbrokenProjectName'.repeat(12);
      const sourceLabel = document.querySelector('.source-meta') || document.querySelector('.scope');
      sourceLabel.textContent = 'SourceLocator'.repeat(30);
    });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    receipt.checks.push('reduced motion; malformed anchor; long-content layout at 320px');

    const noScript = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 375, height: 900 } });
    const staticPage = await noScript.newPage();
    await staticPage.goto(url);
    assert.equal(await staticPage.locator('.account').count(), packet.accounts.length);
    await staticPage.locator('.context-details summary').first().click();
    assert.ok(await staticPage.locator('.detail-grid').first().isVisible());
    receipt.checks.push('readable accounts and native disclosures without JavaScript');
    await noScript.close();

    await page.goto(url);
    await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
    assert.equal(await page.locator('details:not([open])').count(), 0);
    await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
    assert.equal(await page.locator('details[open]').count(), 0);
    receipt.checks.push('print reveals source details and restores disclosure state');
    assert.deepEqual(receipt.externalRequests, []);
    assert.deepEqual(receipt.errors, []);
    await fs.writeFile(path.join(output, 'sheet-checks.json'), JSON.stringify(receipt, null, 2));
    console.log(JSON.stringify(receipt));
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
