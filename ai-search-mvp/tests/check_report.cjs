// Logic checks only. A mock document is not a rendered browser inspection.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'..','..','AI-SEARCH-MVP.html'),'utf8');
const payload=html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
new vm.Script(script);
const elements=new Map(),docListeners={};
const ids=[...html.split('<script id="data"')[0].matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
assert.equal(new Set(ids).size,ids.length);
let focused=null;
function element(id){
 const item={textContent:'',value:id==='evidence-filter'?'all':'',hidden:false,checked:false,listeners:{},addEventListener(event,fn){this.listeners[event]=fn},focus(){focused=id},scrollIntoView(){this.scrolled=true},querySelector(selector){return element(id+' '+selector)}};
 let markup='';Object.defineProperty(item,'innerHTML',{get(){return markup},set(value){markup=value;for(const m of value.matchAll(/\bid="([^"]+)"/g))elements.set(m[1],element(m[1]))}});return item;
}
for(const id of [...ids,'data'])elements.set(id,element(id));
elements.get('data').textContent=payload;
const context=vm.createContext({document:{getElementById:id=>elements.get(id),addEventListener(event,fn){docListeners[event]=fn}},console});
vm.runInContext(script,context);
assert(elements.get('case-ownership').checked);
assert.match(elements.get('comparison').innerHTML,/Evaluation authors and coverage decisions/);
assert.match(elements.get('comparison').innerHTML,/Saved findings/);
assert.match(elements.get('metrics').innerHTML,/39 \/ 39/);
assert.match(elements.get('metrics').innerHTML,/11 \/ 12/);
assert.match(elements.get('verdict').innerHTML,/not an end-to-end pass/);
assert.match(elements.get('method').textContent,/failed connection launch/);
assert.match(elements.get('comparison').innerHTML,/Draft needs correction/);
assert.match(elements.get('comparison').innerHTML,/Draft structure passed/);
elements.get('case').listeners.change({target:{value:'retention'}});
assert(elements.get('case-retention').checked);
assert.match(elements.get('comparison').innerHTML,/Evidence-linked account/);
assert.match(elements.get('comparison').innerHTML,/Saved findings/);
assert.match(elements.get('comparison').innerHTML,/There is no separate summary/);
elements.get('case').listeners.change({target:{value:'depth'}});
assert(elements.get('case-depth').checked);
assert.match(elements.get('comparison').innerHTML,/Derived evidence links and research choices/);
assert.match(elements.get('comparison').innerHTML,/Open branches are ranked deepest first/);
assert.match(elements.get('queue').innerHTML,/matches the saved final response/);
elements.get('case').listeners.change({target:{value:'completion'}});
assert(elements.get('case-completion').checked);
assert.match(elements.get('metrics').innerHTML,/38 \/ 39/);
assert.match(elements.get('metrics').innerHTML,/10 \/ 12/);
assert.match(elements.get('metrics').innerHTML,/45 \/ 45/);
assert.match(elements.get('metrics').innerHTML,/47 requests/);
assert.match(elements.get('queue').innerHTML,/source_limit/);
assert.match(elements.get('queue').innerHTML,/matches the saved final response/);
assert.match(elements.get('queue').innerHTML,/1 unfinished contexts/);
assert.match(elements.get('attachments').innerHTML,/not checked by researcher/);
assert.match(elements.get('comparison').innerHTML,/Quotation provenance/);
assert.match(elements.get('verdict').innerHTML,/not an end-to-end pass/);
elements.get('theme-select').listeners.change({target:{value:'2'}});
assert(!elements.get('theme-detail').innerHTML.includes('Exact quotation check failed'));
docListeners.click({target:{closest(selector){return selector==='[data-attachment]'?{dataset:{attachment:'att:export-sample'}}:null}},preventDefault(){}});
assert(elements.get('record-att-export-sample').open);
elements.get('return-review').listeners.click();
elements.get('case').listeners.change({target:{value:'attribution'}});

assert(elements.get('case-attribution').checked);
assert.match(elements.get('metrics').innerHTML,/35 \/ 38/);
assert.match(elements.get('metrics').innerHTML,/9 \/ 11/);
assert.match(elements.get('metrics').innerHTML,/41 \/ 45/);
assert.match(elements.get('metrics').innerHTML,/44 requests · 3 cache replays/);
assert.match(elements.get('comparison').innerHTML,/7 contribution chains/);
assert.match(elements.get('queue').innerHTML,/0 unfinished window sweeps/);
assert.match(elements.get('verdict').innerHTML,/not a clean pass/);
elements.get('theme-select').listeners.change({target:{value:'5'}});
assert.match(elements.get('theme-detail').innerHTML,/Exact quotation check failed/);
docListeners.click({target:{closest(selector){return selector==='[data-attachment]'?{dataset:{attachment:'attachment:raw-lane-export'}}:null}},preventDefault(){}});
assert(elements.get('record-attachment-raw-lane-export').open);
assert.match(elements.get('attachments').innerHTML,/Unavailable/);
elements.get('return-review').listeners.click();
elements.get('case').listeners.change({target:{value:'followup'}});

assert(elements.get('case-followup').checked);
assert.match(elements.get('metrics').innerHTML,/33 \/ 37/);
assert.match(elements.get('metrics').innerHTML,/9 \/ 11/);
assert.match(elements.get('metrics').innerHTML,/45 \/ 45/);
assert.match(elements.get('queue').innerHTML,/0 unfinished contexts/);
assert.match(elements.get('queue').innerHTML,/1 unread references/);
assert.match(elements.get('theme-detail').innerHTML,/correction’s origin/);
assert.match(elements.get('comparison').innerHTML,/What changed in the planner/);
assert.match(elements.get('method').textContent,/followup.gold.json/);
elements.get('theme-select').listeners.change({target:{value:'10'}});
assert.match(elements.get('theme-detail').innerHTML,/Missed/);
docListeners.click({target:{closest(){return {dataset:{record:'chat:001'}}}},preventDefault(){}});
assert(elements.get('record-chat-001').open);
assert.match(elements.get('evidence').innerHTML,/Not surfaced during research/);
elements.get('return-review').listeners.click();
elements.get('case').listeners.change({target:{value:'autonomous'}});

assert.match(elements.get('metrics').innerHTML,/31 \/ 41/);
assert.match(elements.get('metrics').innerHTML,/9 \/ 12/);
assert.match(elements.get('metrics').innerHTML,/45 \/ 45/);
assert(elements.get('case-autonomous').checked);
assert.match(elements.get('comparison').innerHTML,/45 model-chosen calls/);
assert.match(elements.get('evidence').innerHTML,/Evaluator copy · not read in full by researcher/);
// Missing context can be inspected without claiming the model saw it.
docListeners.click({target:{closest(){return {dataset:{record:'chat:016'}}}},preventDefault(){}});
assert(elements.get('record-chat-016').open);
assert.match(elements.get('evidence').innerHTML,/Not surfaced during research/);
elements.get('return-review').listeners.click();
elements.get('case').listeners.change({target:{value:'semantic'}});
assert.match(elements.get('metrics').innerHTML,/22 \/ 22/);
assert.match(elements.get('metrics').innerHTML,/11 \/ 12/);
assert.match(elements.get('headline').textContent,/causal claim/);
assert.match(elements.get('theme-detail').innerHTML,/c13/);
assert.match(elements.get('theme-detail').innerHTML,/Partly met/);
assert.equal(elements.get('theme-select').value,'7');
assert(elements.get('case-semantic').checked);
assert.equal((elements.get('metrics').innerHTML.match(/metric-source/g)||[]).length,3);
assert.equal((elements.get('themes').innerHTML.match(/name="theme"/g)||[]).length,12);
// Selection updates the actual judgement and evidence, not just control styling.
elements.get('theme-select').listeners.change({target:{value:'0'}});
assert.match(elements.get('theme-detail').innerHTML,/Self-initiated origin/);
assert.match(elements.get('theme-detail').innerHTML,/chat:s01/);
assert.equal((elements.get('metrics').innerHTML.match(/metric-source/g)||[]).length,3);
// A source visit clears obstructing filters; return restores them and focus.
elements.get('record-search').value='unlikely search text';
elements.get('record-search').listeners.input();
assert.match(elements.get('record-count').textContent,/0 of 22/);
docListeners.click({target:{closest(){return {dataset:{record:'chat:s01'}}}},preventDefault(){}});
assert.equal(elements.get('record-search').value,'');
assert(elements.get('record-chat-s01').open);
assert.equal(focused,'record-chat-s01 summary');
elements.get('return-review').listeners.click();
assert.equal(elements.get('record-search').value,'unlikely search text');
assert.equal(focused,'theme-title');
elements.get('record-search').value='';
elements.get('evidence-filter').value='missed';
elements.get('evidence-filter').listeners.change();
assert.match(elements.get('record-count').textContent,/2 of 22/);
elements.get('case').listeners.change({target:{value:'challenge'}});
assert.match(elements.get('metrics').innerHTML,/20 \/ 20/);
assert.match(elements.get('metrics').innerHTML,/5 \/ 10/);
assert.equal((elements.get('themes').innerHTML.match(/Retrieved, meaning missed/g)||[]).length,5);
elements.get('evidence-filter').value='missed';
elements.get('evidence-filter').listeners.change();
assert.match(elements.get('record-count').textContent,/5 of 20/);
elements.get('case').listeners.change({target:{value:'training'}});
assert.match(elements.get('metrics').innerHTML,/24 \/ 24/);
assert.match(elements.get('metrics').innerHTML,/10 \/ 10/);
elements.get('case').listeners.change({target:{value:'search_only'}});
assert.match(elements.get('verdict').innerHTML,/cannot establish/);
assert.match(elements.get('metrics').innerHTML,/Not scored/);
elements.get('case').listeners.change({target:{value:'challenge'}});
assert.equal(elements.get('evidence-filter').value,'missed');
assert.match(elements.get('record-count').textContent,/5 of 20/);
vm.runInContext("data.challenge.result.records[0].body='<img src=x onerror=alert(1)>';drawEvidence()",context);
assert(!elements.get('evidence').innerHTML.includes('<img src=x'));
assert(elements.get('evidence').innerHTML.includes('&lt;img src=x'));
elements.get('case').listeners.change({target:{value:'semantic'}});
assert.equal(elements.get('theme-select').value,'0');
assert.match(elements.get('theme-detail').innerHTML,/Self-initiated origin/);
vm.runInContext("data.semantic.evaluation.themes[0].assessment='<img src=x onerror=alert(1)>';renderReader()",context);
assert(!elements.get('theme-detail').innerHTML.includes('<img src=x'));
assert(elements.get('theme-detail').innerHTML.includes('&lt;img src=x'));
assert.equal((html.match(/Synthetic demo data/g)||[]).length,1);
assert(html.includes('prefers-reduced-motion:reduce'));
assert(html.includes('@media(max-width:374px)'));
assert(html.includes('@media(max-width:767px)'));
assert(!html.includes('__STYLES__'));
// Every theme's source action resolves within its own retained fixture.
const saved=JSON.parse(payload);
for(const key of Object.keys(saved)){
 const packet=saved[key];
 assert.equal(packet.result.synthetic,true);
 assert.deepEqual(packet.result,JSON.parse(fs.readFileSync(path.join(__dirname,'..','runs',key,'result.json'),'utf8')));
 elements.get('case').listeners.change({target:{value:key}});
 const themes=packet.evaluation?.themes||[];
 for(let i=0;i<themes.length;i++){
  elements.get('theme-select').listeners.change({target:{value:String(i)}});
  for(const link of elements.get('theme-detail').innerHTML.matchAll(/data-record="([^"]+)"/g))assert([...packet.result.records,...(packet.audit_records||[])].some(r=>r.id===link[1]),'Missing source '+link[1]);
 }
}
assert.deepEqual(saved.semantic.review,JSON.parse(fs.readFileSync(path.join(__dirname,'..','runs','semantic','model','review.json'),'utf8')));
assert.deepEqual(saved.semantic.evaluation,JSON.parse(fs.readFileSync(path.join(__dirname,'..','runs','semantic','assessment.json'),'utf8')));
assert.deepEqual(saved.autonomous.review,JSON.parse(fs.readFileSync(path.join(__dirname,'..','runs','autonomous','researcher','response.json'),'utf8')));
assert.deepEqual(saved.autonomous.evaluation,JSON.parse(fs.readFileSync(path.join(__dirname,'..','runs','autonomous','assessment.json'),'utf8')));
for(const key of ['autonomous','followup','attribution']){
 assert.deepEqual(saved[key].review,JSON.parse(fs.readFileSync(path.join(__dirname,'..','runs',key,'researcher','response.json'),'utf8')));
 assert.deepEqual(saved[key].evaluation,JSON.parse(fs.readFileSync(path.join(__dirname,'..','runs',key,'assessment.json'),'utf8')));
}
const ownershipRaw=JSON.parse(fs.readFileSync(path.join(__dirname,'..','runs','ownership','researcher','response.json'),'utf8'));
assert.deepEqual(saved.ownership.review,JSON.parse(fs.readFileSync(path.join(__dirname,'..','runs','ownership','researcher','review.json'),'utf8')));
assert.deepEqual(saved.ownership.review.coverage_notes,ownershipRaw.coverage_notes);
assert.equal(saved.ownership.provenance.valid,true);
assert.equal(saved.ownership.provenance.quote_count,70);
assert.equal(saved.ownership.review.evidence_notes.length,39);
assert.equal(saved.ownership.provenance.source_credit_records,6);
assert.equal(saved.ownership.trace.requests,67);
assert.equal(saved.ownership.evaluation.research_launches,2);
assert.equal(saved.ownership.evaluation.summary_counts.partial,1);
assert.equal(saved.ownership.review.omitted_material.length,7);
for(const c of saved.ownership.review.claims){
 const raw=ownershipRaw.claims.find(x=>x.id===c.id);
 assert.equal(c.statement,raw.statement);assert.equal(c.limits,raw.limits);
 assert(saved.ownership.review.account.includes(c.statement+' '+c.limits));
 for(const a of c.evidence){const record=saved.ownership.result.records.find(r=>r.id===a.record_id);assert(record.body.includes(a.quote));}
 for(const ref of raw.roles){
  const note=saved.ownership.review.evidence_notes.find(n=>n.record_id===ref.record_id);
  const role=note.attributions[ref.attribution_index];
  assert(saved.ownership.review.attribution_chains.some(chain=>chain.claim_ids.includes(c.id)&&chain.roles.some(r=>r.actor===role.actor&&r.role===role.state+': '+role.action)));
 }
}
for(const credits of Object.values(saved.ownership.review.source_credits))for(const credit of credits){
 assert.equal(credit.author,saved.ownership.result.records.find(r=>r.id===credit.record_id).author);
 assert(saved.ownership.review.account.includes(credit.author));
}
const usedOwnership=new Set(saved.ownership.review.claims.flatMap(c=>c.evidence.map(a=>a.record_id)));
assert(saved.ownership.review.omitted_material.every(n=>!usedOwnership.has(n.record_id)));
const retentionRaw=JSON.parse(fs.readFileSync(path.join(__dirname,'..','runs','retention','researcher','response.json'),'utf8'));
assert.deepEqual(saved.retention.review,JSON.parse(fs.readFileSync(path.join(__dirname,'..','runs','retention','researcher','review.json'),'utf8')));
const retainedClaims=new Map(retentionRaw.claims.map(c=>[c.id,c]));
assert.equal(saved.retention.review.account,retentionRaw.story_order.map(id=>retainedClaims.get(id).statement+' '+retainedClaims.get(id).limits).join('\n\n'));
for(const key of ['unknowns','rejected_conclusions','research_choices','stop_receipt_id','story_order','omitted_material'])assert.deepEqual(saved.retention.review[key],retentionRaw[key]);
assert.equal(saved.retention.provenance.narrative_compiled,true);
assert.equal(saved.retention.provenance.valid,false);
assert.deepEqual(saved.retention.provenance.errors,['Invalid material omission: docs:010']);
assert.equal(saved.retention.provenance.quote_count,80);
assert.equal(saved.retention.result.records.length,41);
assert.equal(saved.retention.audit_records.length,0);
assert.equal(saved.retention.review.evidence_notes.length,41);
assert.equal(saved.retention.evaluation.summary_counts.fully_met,10);
assert.equal(saved.retention.evaluation.summary_counts.partial,1);
assert.equal(saved.retention.evaluation.summary_counts.writing_packet_calls,9);
assert.equal(saved.retention.trace.requests,65);
assert.equal(saved.retention.provenance.rejection_only_records.length,0);
for(const c of saved.retention.review.claims){
 const raw=retainedClaims.get(c.id);
 assert.equal(c.statement,raw.statement);assert.equal(c.limits,raw.limits);
 for(const a of c.evidence){const record=saved.retention.result.records.find(r=>r.id===a.record_id);assert(record.body.includes(a.quote));}
 for(const role of raw.roles)assert(saved.retention.review.attribution_chains.some(chain=>chain.claim_ids.includes(c.id)&&chain.roles.some(r=>r.actor===role.actor&&r.role===role.role)));
}
const depthRaw=JSON.parse(fs.readFileSync(path.join(__dirname,'..','runs','depth','researcher','response.json'),'utf8'));
assert.deepEqual(saved.depth.review,JSON.parse(fs.readFileSync(path.join(__dirname,'..','runs','depth','researcher','review.json'),'utf8')));
for(const key of ['account','unknowns','rejected_conclusions','research_choices','stop_receipt_id'])assert.deepEqual(saved.depth.review[key],depthRaw[key]);
assert.equal(saved.depth.provenance.bookkeeping_derived,true);
assert.equal(saved.depth.provenance.valid,false);
assert.equal(saved.depth.provenance.errors.length,1);
assert.equal(saved.depth.provenance.quote_count,30);
assert.equal(saved.depth.trace.planning.unopened_contexts.length,0);
assert.equal(saved.depth.result.records.length,41);
assert.equal(saved.depth.audit_records.length,6);
assert.equal(saved.depth.evaluation.summary_counts.fully_met,3);
assert.equal(saved.depth.evaluation.summary_counts.partial,5);
assert.equal(saved.depth.evaluation.summary_counts.missed,2);
assert.equal(saved.depth.review.attachment_dispositions.length,0);
assert(saved.depth.attachments.every(a=>a.read_by_researcher===false));
for(const c of saved.depth.review.claims){
 const raw=depthRaw.claims.find(x=>x.id===c.id);
 assert.equal(c.statement,raw.statement);assert.equal(c.limits,raw.limits);
 for(const a of c.evidence){const record=saved.depth.result.records.find(r=>r.id===a.record_id);assert(record.body.includes(a.quote));}
}
assert.equal(new Set(saved.depth.review.evidence_dispositions.flatMap(x=>x.record_ids)).size,saved.depth.result.records.length);
for(const d of saved.depth.review.evidence_dispositions.filter(x=>x.disposition==='used')){
 for(const id of d.record_ids)assert(d.claim_ids.some(cid=>saved.depth.review.claims.find(c=>c.id===cid).evidence.some(a=>a.record_id===id)));
}
const completionRaw=JSON.parse(fs.readFileSync(path.join(__dirname,'..','runs','completion','researcher','response.json'),'utf8'));
assert.deepEqual(saved.completion.review,JSON.parse(fs.readFileSync(path.join(__dirname,'..','runs','completion','researcher','review.json'),'utf8')));
assert.deepEqual(saved.completion.evaluation,JSON.parse(fs.readFileSync(path.join(__dirname,'..','runs','completion','assessment.json'),'utf8')));
for(const key of ['account','unknowns','rejected_conclusions','attribution_chains','evidence_dispositions','attachment_dispositions','stop_receipt_id'])assert.deepEqual(saved.completion.review[key],completionRaw[key]);
assert.equal(saved.completion.provenance.quote_count,43);
assert.equal(saved.completion.provenance.valid,false);
assert.equal(saved.completion.provenance.completion_receipt_valid,true);
assert.equal(saved.completion.provenance.errors.length,4);
assert.equal(saved.completion.trace.completion_receipt.status,'source_limit');
assert.equal(saved.completion.audit_records.length,1);
for(const c of saved.completion.review.claims){
 const raw=completionRaw.claims.find(x=>x.id===c.id);
 assert.equal(c.statement,raw.statement);assert.equal(c.limits,raw.limits);
 for(const a of c.evidence){const record=saved.completion.result.records.find(r=>r.id===a.record_id);assert(record.body.includes(a.quote));}
}
assert.equal(saved.attribution.provenance.valid,false);
assert.equal(saved.attribution.provenance.quote_count,32);
assert.equal(saved.attribution.provenance.errors.length,3);
assert.equal(saved.attribution.audit_records.length,3);
assert.equal(saved.attribution.attachments.length,2);
assert.equal(saved.attribution.evaluation.summary_counts.remaining_source_calls,4);
assert.equal(saved.followup.audit_records.length,4);
assert.equal(saved.followup.trace.planning.unopened_contexts.length,0);
assert.equal(saved.followup.trace.planning.unfinished_window_sweeps.length,0);
assert.equal(saved.followup.evaluation.summary_counts.redundant_full_reads,3);
assert.equal(saved.autonomous.audit_records.length,10);
assert(saved.autonomous.audit_records.every(a=>!saved.autonomous.result.records.some(r=>r.id===a.id)));
assert(html.includes("connect-src 'none'"));
assert(!/<(?:script|link|iframe)[^>]+(?:src|href)\s*=/.test(html));
console.log(JSON.stringify({script_syntax:'pass',case_selection:'pass',theme_selection:'pass',filter_restoration:'pass',source_return_and_focus:'pass',empty_search:'pass',source_text_escaping:'pass',external_assets:0,rendered_inspection:false}));
