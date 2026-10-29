// Rendered integration check for the single career document. Works with private inputs locally.
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');
async function main(){
 const root=path.resolve(__dirname,'..');
 const output=process.env.CAREER_CONTEXT_QA_DIR;
 assert.ok(output,'Set CAREER_CONTEXT_QA_DIR to a private verification folder');
 const url=pathToFileURL(process.env.CAREER_CONTEXT_HTML||path.join(root,'CAREER-CONTEXT.html')).href;
 const browser=await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHANNEL||'msedge'});
 const result={widths:[],errors:[],externalRequests:[],checks:[]};
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
  const page=await context.newPage();
  page.on('pageerror',e=>result.errors.push(e.message));
  page.on('request',r=>{if(/^https?:/.test(r.url()))result.externalRequests.push(r.url());});
  await page.goto(url);
  const data=await page.locator('#career-context-data').textContent().then(JSON.parse);
  assert.ok(data.timeline.length&&data.interview.stories.length);
  result.accounts=data.accounts.length;result.periods=data.timeline.length;result.stories=data.interview.stories.length;
  const first=data.timeline[0],last=data.timeline.at(-1),story=data.interview.stories[0];
  assert.equal(await page.locator('#work').isVisible(),true);
  await page.locator('[data-view="timeline"]').click();
  assert.equal(await page.locator('.quarter-reading:visible').count(),1);
  assert.equal(await page.locator('#quarter-'+first.id).isVisible(),true);
  await page.locator('.period-index a[href="#quarter-'+last.id+'"]').click();
  await page.reload();assert.equal(await page.locator('#quarter-'+last.id).isVisible(),true);
  await page.goBack();assert.equal(await page.locator('#timeline').isVisible(),true);
  await page.locator('[data-view="interview"]').click();
  assert.equal(await page.locator('#interview').isVisible(),true);
  await page.locator('#prep-story-select').selectOption(story.id);
  assert.equal(await page.locator('#prep-story-'+story.id).isVisible(),true);
  await page.locator('#prep-story-'+story.id+' .related-work a').click();
  assert.equal(await page.locator('#account-'+story.id).isVisible(),true);
  await page.goBack();assert.equal(await page.locator('#prep-story-'+story.id).isVisible(),true);
  const note=page.locator('[data-rehearsal="'+story.id+'"]');
  await note.locator('..').locator('..').evaluate(el=>el.open=true);
  await note.fill('Portable rehearsal check: keep shared credit.');
  await page.reload();assert.equal(await note.inputValue(),'Portable rehearsal check: keep shared credit.');
  await page.evaluate(()=>Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw Error('denied');}}}));
  await page.locator('#copy-prep').click();
  const prepText=await page.locator('#agent-text').inputValue();
  assert.ok(prepText.includes('Portable rehearsal check'));
  for(const s of data.interview.stories){assert.ok(prepText.includes(s.takeaway));assert.ok(prepText.includes(s.chapters[0].text));}
  await page.locator('#reader-copy').click();
  assert.equal(await page.locator('#agent-text').inputValue(),prepText,'Fallback must keep the interview text');
  await page.keyboard.press('Escape');
  result.checks.push('cross-view routes, refresh, back, rehearsal persistence and clipboard fallback');
  for(const width of [1440,768,375,320]){
   await page.setViewportSize({width,height:1000});
   for(const view of ['work','timeline','interview']){
    await page.locator('[data-view="'+view+'"]').click();
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,view+' overflow '+width);
    if(width===1440||width===375)await page.screenshot({path:path.join(output,'complete-'+view+'-'+width+'.png')});
   }
   await page.goto(url+'#quarter-'+last.id);
   const periodGeometry=await page.evaluate(()=>{
    const top=document.querySelector('.top').getBoundingClientRect();
    const article=document.querySelector('.quarter-reading:not([hidden])').getBoundingClientRect();
    const rail=document.querySelector('.period-index').getBoundingClientRect();
    const active=document.querySelector('.period-index [aria-current="true"]').getBoundingClientRect();
    return {uncovered:article.top>=top.bottom,visible:active.left>=rail.left-1&&active.right<=rail.right+1&&active.top>=rail.top-1&&active.bottom<=rail.bottom+1};
   });
   assert.ok(periodGeometry.uncovered,'Sticky header covers period at '+width);
   assert.ok(periodGeometry.visible,'Selected period is outside its index at '+width);
   await page.goto(url+'#prep-story-'+story.id);
   assert.equal(await page.evaluate(()=>document.querySelector('.prep-story:not([hidden])').getBoundingClientRect().top>=document.querySelector('.top').getBoundingClientRect().bottom),true,'Sticky header covers story at '+width);
   result.widths.push(width);
  }
  await page.setViewportSize({width:1440,height:1000});
  await page.locator('[data-view="work"]').click();
  await page.locator('#view-context').click();
  const allText=await page.locator('#agent-text').inputValue();
  assert.ok(allText.includes('## Career timeline')&&allText.includes('## Interview prep'));
  await page.keyboard.press('Escape');
  await page.locator('.export-options').evaluate(el=>el.open=true);
  await page.locator('#export-account').selectOption(data.accounts[0].id);
  await page.locator('#view-context').click();
  const scopedText=await page.locator('#agent-text').inputValue();
  assert.ok(!scopedText.includes('## Career timeline')&&!scopedText.includes('## Interview prep'));
  await page.keyboard.press('Escape');
  const waiting=page.waitForEvent('download');await page.locator('#save-html').click();
  const download=await waiting,file=path.join(output,'complete-downloaded.html');await download.saveAs(file);
  const reopened=await context.newPage();await reopened.goto(pathToFileURL(file).href);
  const saved=await reopened.locator('#career-context-data').textContent().then(JSON.parse);
  assert.deepEqual(saved.timeline,data.timeline);assert.deepEqual(saved.interview,data.interview);
  assert.equal(saved.rehearsal.notes[story.id],'Portable rehearsal check: keep shared credit.');
  await reopened.locator('[data-view="timeline"]').click();assert.equal(await reopened.locator('.quarter-reading:visible').count(),1);
  await reopened.evaluate(()=>dispatchEvent(new Event('beforeprint')));
  assert.equal(await reopened.locator('.quarter-reading:visible').count(),data.timeline.length);
  assert.equal(await reopened.locator('.prep-story:visible').count(),data.interview.stories.length);
  await reopened.evaluate(()=>dispatchEvent(new Event('afterprint')));
  assert.equal(await reopened.locator('.quarter-reading:visible').count(),1);
  const plain=await browser.newContext({javaScriptEnabled:false});const offline=await plain.newPage();await offline.goto(pathToFileURL(file).href);
  assert.equal(await offline.locator('.quarter-reading:visible').count(),data.timeline.length);
  assert.equal(await offline.locator('.prep-story:visible').count(),data.interview.stories.length);
  assert.equal(await offline.locator('.account:visible').count(),data.accounts.length);
  assert.equal(await offline.locator('.js-only:visible').count(),0);
  assert.ok((await offline.locator('[data-rehearsal-display="'+story.id+'"]').textContent()).includes('Portable rehearsal check'));
  result.checks.push('complete and scoped copy, portable save/reopen, print/restore, no-JavaScript reading');
  assert.deepEqual(result.errors,[]);assert.deepEqual(result.externalRequests,[]);
  await fs.writeFile(path.join(output,'complete-checks.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify(result));
 }finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
