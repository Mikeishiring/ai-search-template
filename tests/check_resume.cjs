// Optional offline browser validation. Set CAREER_RESUME_HTML to a synthetic resume.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

async function main() {
  assert.ok(process.env.CAREER_RESUME_HTML && process.env.CAREER_CONTEXT_QA_DIR, 'Set the synthetic input and QA folder');
  const output = process.env.CAREER_CONTEXT_QA_DIR;
  const browser = await chromium.launch({headless:true, ...(process.env.PLAYWRIGHT_CHANNEL ? {channel:process.env.PLAYWRIGHT_CHANNEL} : {})});
  const receipt = {widths:[], checks:[], requests:[], errors:[]};
  try {
    const context = await browser.newContext({acceptDownloads:true});
    const page = await context.newPage();
    page.on('pageerror', e=>receipt.errors.push(e.message));
    page.on('request', r=>{if(/^https?:/.test(r.url())) receipt.requests.push(r.url());});
    const url = pathToFileURL(process.env.CAREER_RESUME_HTML).href;
    await page.goto(url);
    const packet = JSON.parse(await page.locator('#resume-data').textContent());
    assert.equal(packet.synthetic,true);
    for(const width of [1440,768,375,320]) {
      await page.setViewportSize({width,height:1000});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      await page.screenshot({path:path.join(output,`resume-${width}.png`),fullPage:true});
      receipt.widths.push(width);
    }
    const plain = await page.locator('#resume-text').inputValue();
    for(const section of packet.sections) for(const entry of section.entries) {
      assert.ok(plain.includes(entry.heading));
      for(const bullet of entry.bullets) assert.ok(plain.includes(bullet));
    }
    await page.evaluate(()=>Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async t=>{window.copied=t;}}}));
    await page.getByRole('button',{name:'Copy resume text',exact:true}).click();
    assert.equal(await page.evaluate(()=>window.copied),plain);
    await page.evaluate(()=>Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw Error('denied');}}}));
    await page.getByRole('button',{name:'Copy resume text',exact:true}).click();
    assert.equal(await page.locator('#text').getAttribute('open'),'');
    assert.equal(await page.locator('#resume-text').evaluate(e=>e.selectionEnd-e.selectionStart),plain.length);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#text').getAttribute('open'),null);
    const downloadEvent=page.waitForEvent('download');
    await page.getByRole('button',{name:'Download text',exact:true}).click();
    const download=await downloadEvent;
    assert.equal(await fs.readFile(await download.path(),'utf8'),plain);
    await page.locator('.entry-sources a').first().click();
    assert.equal(await page.locator('#evidence').getAttribute('open'),'');
    assert.ok(await page.locator('.original-account').first().isVisible());
    receipt.checks.push('supported text parity, copy success/fallback, keyboard recovery, text download, evidence navigation');
    await page.setViewportSize({width:900,height:1200});
    await page.emulateMedia({media:'print',reducedMotion:'reduce'});
    assert.equal(await page.locator('.entry-sources').first().isVisible(),false);
    assert.equal(await page.locator('.review-tools').isVisible(),false);
    assert.match(await page.locator('.print-state').innerText(),/Synthetic demo data/);
    await page.screenshot({path:path.join(output,'resume-print.png'),fullPage:true});
    receipt.checks.push('print retains fictional and draft labels; private evidence omitted');
    const noScript=await browser.newContext({javaScriptEnabled:false,viewport:{width:320,height:900}});
    const staticPage=await noScript.newPage();await staticPage.goto(url);
    assert.equal(await staticPage.locator('main h1').innerText(),packet.person);
    await staticPage.locator('#text summary').click();
    assert.equal(await staticPage.locator('#resume-text').inputValue(),plain);
    assert.equal(await staticPage.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    receipt.checks.push('no-JavaScript resume and text access');
    await noScript.close();
    assert.deepEqual(receipt.requests,[]);assert.deepEqual(receipt.errors,[]);
    await fs.writeFile(path.join(output,'resume-checks.json'),JSON.stringify(receipt,null,2));
    console.log(JSON.stringify(receipt));
  }finally{await browser.close();}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
