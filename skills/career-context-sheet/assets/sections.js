// All views share one packet. Hashes select a view or an evidence-linked record.
let selectedPeriod=packet.timeline?.[0]?.id||'';
let selectedStory=packet.interview?.stories?.[0]?.id||'';
const storySelect=document.getElementById('prep-story-select');
function sizeHeader(){document.documentElement.style.setProperty('--header-offset',(document.querySelector('.top').getBoundingClientRect().height+24)+'px');}
sizeHeader();
if(typeof ResizeObserver!=='undefined')new ResizeObserver(sizeHeader).observe(document.querySelector('.top'));
else window.addEventListener('resize',sizeHeader);
function routeDocument(scroll=false){
 let id='';try{id=decodeURIComponent(location.hash.slice(1));}catch{}
 const target=document.getElementById(id);
 const view=target?.closest('.document-view')?.id||'work';
 document.querySelectorAll('.document-view').forEach(el=>el.hidden=el.id!==view);
 document.querySelector('.hero').hidden=view!=='work';
 document.querySelectorAll('[data-view]').forEach(link=>{
  if(link.dataset.view===view)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');
 });
 if(id.startsWith('quarter-')&&target?.classList.contains('quarter-reading'))selectedPeriod=id.slice(8);
 if(id.startsWith('prep-story-')&&target?.classList.contains('prep-story'))selectedStory=id.slice(11);
 document.querySelectorAll('.quarter-reading').forEach(el=>el.hidden=el.id!=='quarter-'+selectedPeriod);
 document.querySelectorAll('.period-index a').forEach(link=>{
  if(link.hash==='#quarter-'+selectedPeriod)link.setAttribute('aria-current','true');else link.removeAttribute('aria-current');
 });
 if(view==='timeline'){
  const rail=document.querySelector('.period-index'),active=rail?.querySelector('[aria-current="true"]');
  if(active){
   const r=rail.getBoundingClientRect(),a=active.getBoundingClientRect();
   if(a.left<r.left||a.right>r.right)rail.scrollLeft+=a.left-r.left-(r.width-a.width)/2;
   if(a.top<r.top||a.bottom>r.bottom)rail.scrollTop+=a.top-r.top-(r.height-a.height)/2;
  }
 }
 document.querySelectorAll('.prep-story').forEach(el=>el.hidden=el.id!=='prep-story-'+selectedStory);
 if(storySelect)storySelect.value=selectedStory;
 if(view==='interview'&&id.startsWith('prep-story-'))document.querySelector('.opening').open=false;
 if(view==='interview'&&id==='interview')document.querySelector('.opening')?.setAttribute('open','');
 if(scroll&&target){
  target.scrollIntoView({block:'start'});
  if(target.matches('.quarter-reading,.prep-story,.account')){target.tabIndex=-1;target.focus({preventScroll:true});}
  if(target.matches('details.source,.capability-index')){target.open=true;target.querySelector('summary').focus({preventScroll:true});}
 }
}
window.addEventListener('hashchange',()=>routeDocument(true));
if(storySelect)storySelect.addEventListener('change',()=>location.hash='prep-story-'+storySelect.value);
routeDocument(Boolean(location.hash));

function appendCompanionText(data,lines){
 if(data.timeline?.length){
  lines.push('## Career timeline','');
  for(const p of data.timeline){
   lines.push(`### ${p.period} — ${p.title}`,p.focus,...p.actions.map(x=>'- '+x));
   if(p.tension)lines.push('Pressure & limits: '+p.tension);
   if(p.approach)lines.push('Change in approach: '+p.approach);
   if(p.questions.length)lines.push('Open questions: '+p.questions.join('\n'));
   lines.push('Linked accounts: '+p.accountIds.join(', '),'Source references: '+p.sourceRefs.join(', '),'');
  }
 }
 const prep=data.interview;
 if(!prep)return;
 lines.push('## Interview prep — draft for practice',prep.headline,prep.throughline,'','### Opening',...prep.opening,'');
 if(prep.target)lines.push('Target: '+prep.target,'');
 for(const option of prep.introOptions||[])lines.push('Alternative opening: '+option.title,option.text,'');
 for(const signal of prep.signals)lines.push('Lead story: '+signal.title,signal.reason,'Account ID: '+signal.storyId,'');
 for(const story of prep.stories){
  lines.push('### Story: '+story.id,story.tests,story.takeaway,'');
  for(const chapter of story.chapters)lines.push(chapter.title,chapter.text,'');
  for(const milestone of story.timeline)lines.push(milestone.when+': '+milestone.text);
  if(story.practice)lines.push('Practice guidance: '+story.practice);
  if(data.rehearsal?.notes?.[story.id])lines.push('Private rehearsal note: '+data.rehearsal.notes[story.id]);
  lines.push('');
 }
 for(const q of prep.questions)lines.push(q.question,'What it tests: '+q.tests,'Account ID: '+q.storyId,q.answer,'Why this example: '+q.reason,'');
 if(prep.priorityGap)lines.push('Question to resolve: '+prep.priorityGap.question,prep.priorityGap.why);
}

const prepStatus=document.getElementById('prep-status');
const rehearsalKey='career-rehearsal:'+packet.interview?.contextSha256;
if(packet.interview){
 const storyIds=new Set(packet.interview.stories.map(s=>s.id));
 try{
  const saved=JSON.parse(localStorage.getItem(rehearsalKey)||'null');
  if(saved&&Number.isSafeInteger(saved.updatedAt)&&saved.updatedAt>(packet.rehearsal?.updatedAt||0)&&saved.notes&&
     Object.entries(saved.notes).every(([id,note])=>storyIds.has(id)&&typeof note==='string'&&note.length<=15000))packet.rehearsal=saved;
 }catch{}
 for(const input of document.querySelectorAll('[data-rehearsal]')){
  input.value=packet.rehearsal?.notes?.[input.dataset.rehearsal]??input.value;
  input.addEventListener('input',()=>{
   packet.rehearsal={updatedAt:Date.now(),notes:{...(packet.rehearsal?.notes||{}),[input.dataset.rehearsal]:input.value}};
   try{localStorage.setItem(rehearsalKey,JSON.stringify(packet.rehearsal));prepStatus.textContent='Note saved in this browser. Save full HTML to keep a portable copy.';}
   catch{prepStatus.textContent='Browser storage is unavailable. Save full HTML to keep your note.';}
  });
 }
 document.getElementById('copy-prep').addEventListener('click',async event=>{
  const data={...packet,accounts:packet.accounts.filter(a=>storyIds.has(a.id)),sources:[]};
  delete data.timeline;delete data.collection;
  const text=contextText(data);
  try{await navigator.clipboard.writeText(text);prepStatus.textContent='Interview prep copied.';}
  catch{
   opener=event.currentTarget;document.getElementById('agent-text').value=text;
   document.getElementById('reader-note').textContent='Clipboard access is unavailable. Select and copy the interview prep below.';
   reader.showModal();document.getElementById('agent-text').select();
  }
 });
}
