// Exercise the shipped notebook's route/menu/source handlers without a browser.
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(root,'CAREER-NOTEBOOK.html'),'utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];new vm.Script(script);
const draft=JSON.parse(html.match(/<script[^>]*id="career-draft-data"[^>]*>([\s\S]*?)<\/script>/)[1]);
const originalIntro=draft.profile.intro;
draft.profile.introOptions=Array.from({length:6},(_,i)=>({id:'angle-'+i,title:'Angle '+i,text:'Fictional proposal '+i+' <script>inert</script>\n\nAnother paragraph.'}));
const copied=[];
const elements={},listeners={},storage=new Map();
function element(id){return elements[id]??={textContent:'',hidden:false,open:false,dataset:{},attrs:{},classList:{add(){},remove(){}},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this.attrs[k];},focus(){this.focused=true;},scrollIntoView(){this.scrolled=true;},showModal(){this.open=true;},close(){this.open=false;this.events?.close?.({});},addEventListener(type,fn){(this.events??={})[type]=fn;}};}
element('career-draft-data').textContent=JSON.stringify(draft);
const links=['overview','work','arc','prep','directions','build'].map(id=>Object.assign(element('link-'+id),{dataset:{navView:id}}));
const sandbox=vm.createContext({document:{getElementById:element,querySelectorAll:()=>links,addEventListener:(type,fn)=>listeners[type]=fn},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},person:{id:'own',role:'Contributor 01'},view:'work',location:{href:'https://example.invalid/notebook.html?view=work&quarter=2030-Q1'},URL,URLSearchParams,structuredClone,Date,$:element,route(){},render(){},editorialArt(){return '';},navigator:{clipboard:{writeText:async text=>copied.push(text)}},setTimeout(){},window:{scrollTo(){}}});
const nbSource=script.match(/const notebook=\(\(\)=>\{[\s\S]*?\n\}\)\(\);/)[0];
const navSource=script.match(/const notebookNavigation=\(\(\)=>\{[\s\S]*?\n\}\)\(\);/)[0];
vm.runInContext(nbSource.replace('return {views,bind,','return {work,arc,prep,sourceReader,coachText,workingFallback,views,bind,')+'\nglobalThis.nb=notebook;',sandbox);
vm.runInContext(navSource+'\nglobalThis.nav=notebookNavigation;',sandbox);
const {nb,nav}=sandbox;
nb.restoreRoute(new URLSearchParams('account=request-handoffs&quarter=2030-Q1'));
assert(nb.coachText().includes('Fictional example'));assert(nb.coachText().includes('Quarter: 2030 Q1'));assert(nb.publicHtml().includes('Fictional example'));nb.current().responsibility='A saved answer with $1,000 and <markup>.';assert(nb.workingFallback().includes('A saved answer with $1,000 and &lt;markup&gt;.'));assert.equal(nb.currentQuarter().id,'2030-Q1');assert.equal(nb.quarterList().length,3);
assert(nb.arc().includes('data-quarter="2030-Q2"'));assert(nb.arc().includes('Linked account: January'));assert(nb.arc().includes('Change in approach'));
const route=new URL('https://example.invalid/');nb.query(route);assert.equal(route.searchParams.get('quarter'),'2030-Q1');
nb.bind();const button=dataset=>({dataset,hasAttribute:()=>false});
function click(b){listeners.click({target:{closest:selector=>selector==='button'?b:null}});}
click(button({nbAction:'quarter-sources'}));assert(elements.evidence.open);assert(elements['evidence-body'].innerHTML.includes('context-record-0'));assert(!elements['evidence-body'].innerHTML.includes('data-followup'));
click(button({nbAction:'quarter-story'}));assert(!elements.evidence.open);assert.equal(nb.current().id,'request-handoffs');assert(nb.prep().includes('Back to 2030 Q1'));
click(button({nbAction:'return-quarter'}));assert.equal(nb.currentQuarter().id,'2030-Q1');
const recordButton=button({sourceTarget:'context-record-0'});click(recordButton);assert(elements['context-record-0'].focused);assert(elements['context-record-0'].scrolled);
// Comparing and copying do not adopt an option or expose it in the selected portfolio.
click(button({nbAction:'compare-intros'}));
assert(nb.ownOverview().includes('Alternative introductions'));
assert(nb.ownOverview().includes('&lt;script&gt;inert&lt;/script&gt;'));
nb.query(route);assert.equal(route.searchParams.get('compare'),'intros');
assert.equal(route.searchParams.get('quarter'),'2030-Q1');
assert.equal(route.searchParams.get('fromQuarter'),'2030-Q1');
for(const [i,option] of draft.profile.introOptions.entries()){
 click(button({nbCopy:'intro-option',introIndex:String(i)}));
 assert.equal(copied[i],'Fictional example\n\n'+option.text);
 assert(nb.coachText().includes(option.text));
}
assert(nb.workingFallback().includes('Alternative introductions'));
assert(!JSON.stringify(nb.publicProjection()).includes('introOptions'));
assert(!nb.publicHtml().includes('Fictional proposal'));
assert.equal(storage.size,0);
click(button({nbAction:'close-intro-comparison'}));
nb.query(route);assert(!route.searchParams.has('compare'));
assert(nb.ownOverview().includes(originalIntro));
nb.restoreRoute(new URLSearchParams('compare=intros&quarter=2030-Q1'));
assert(nb.ownOverview().includes('Alternative introductions'));
nb.restoreRoute(new URLSearchParams('view=arc&quarter=2030-Q1'));sandbox.view='arc';
// Explicit source fields remain text; unsafe destinations never become links.
const unsafe=nb.sourceReader({title:'<script>bad</script>',sources:[{title:'Unsafe',text:'<img onerror=bad>',url:'javascript:alert(1)'}]},false);assert(!unsafe.includes('<script>'));assert(!unsafe.includes('href="javascript:'));
nav.bind();nav.update();assert.equal(element('notebook-status').hidden,false);assert.equal(element('link-arc').attrs['aria-current'],'page');
element('notebook-menu-button').events.click();assert(element('notebook-menu-dialog').open);assert.equal(element('notebook-menu-button').attrs['aria-expanded'],'true');assert(element('notebook-menu-close').focused);
element('notebook-menu-dialog').events.click({target:element('notebook-menu-dialog')});assert(!element('notebook-menu-dialog').open);assert.equal(element('notebook-menu-button').attrs['aria-expanded'],'false');
element('notebook-menu-button').events.click();element('notebook-menu-dialog').close();assert.equal(element('notebook-menu-button').attrs['aria-expanded'],'false');
let prevented=false;listeners.click({target:{closest:()=>element('link-work')},preventDefault(){prevented=true;}});assert(prevented);assert.equal(sandbox.view,'work');nav.update();assert.equal(element('link-work').attrs['aria-current'],'page');assert(!element('link-arc').attrs['aria-current']);
assert(element('link-work').href.includes('quarter=2030-Q1'));
console.log('PASS: shipped script compilation, explicit quarter routes and return, indexed evidence, safe links, current-page navigation, menu open/close and isolated storage. Rendered layout and native keyboard behaviour need browser verification.');
