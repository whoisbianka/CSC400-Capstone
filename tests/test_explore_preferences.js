const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor() { this.children=[]; this.dataset={}; this.value=''; }
  addEventListener(event, fn) { this[event]=fn; }
  setAttribute() {}
  append(...items) { this.children.push(...items); }
  appendChild(item) { this.children.push(item); }
  replaceChildren() { this.children=[]; }
  focus() {}
}
(async () => {
  const save=new Element(), reset=new Element(), status=new Element();
  const toggle=new Element(); toggle.dataset.filterToggle='budget'; toggle.checked=false;
  const budget=new Element(); budget.classList={add(){}};
  const form={querySelectorAll:()=>[toggle],reportValidity:()=>true, querySelector:key=>({'[data-save-preferences]':save,'[data-reset-preferences]':reset,'[data-preferences-status]':status})[key]};
  const nav={dataset:{userId:'42',csrf:'csrf'}};
  const requests=[]; let destination; let fail=true;
  class FormData {
    constructor() {this.items=[['view','programs'],['degree_form','1'],['degree','2'],['degree','3'],['city','Albany'],['net_price_max','0'],['preferences_applied','1']];}
    [Symbol.iterator]() {return this.items[Symbol.iterator]();}
    get(key) {return this.items.find(item=>item[0]===key)?.[1];}
  }
  vm.runInNewContext(fs.readFileSync('degree_path/static/js/explore-preferences.js','utf8'),{
    FormData, document:{getElementById:id=>id==='degree-filter-form'?form:id==='budget'?budget:nav},
    window:{confirm:()=>true,location:{assign:url=>{destination=url;}}},
    fetch:async(path, options)=>{requests.push({path,options});return {ok:!fail,json:async()=>fail?{error:'Try again'}:{url:'/explore?degrees=2,3'}};},
  });
  assert.equal(budget.disabled,true);
  toggle.checked=true; toggle.change();
  assert.equal(budget.disabled,false);
  toggle.checked=false; toggle.change();
  assert.equal(budget.disabled,true);
  await save.click();
  assert.equal(status.textContent,'Try again');
  assert.equal(save.disabled,false);
  const payload=JSON.parse(requests[0].options.body);
  assert.deepEqual(payload.filters.degree,['2','3']);
  assert.deepEqual(payload.filters.net_price_max,['0']);
  assert.equal(payload.filters.preferences_applied,undefined);
  assert.equal(requests[0].options.headers['X-App-User-ID'],'42');
  assert.equal(requests[0].options.headers['X-CSRF-Token'],'csrf');
  fail=false;
  await reset.click();
  assert.equal(JSON.parse(requests[1].options.body).action,'reset');
  assert.equal(destination,'/explore?degrees=2,3');

  // Exercise the actual chat controller's reset flow with a fake API/DOM.
  const ids={};
  for(const id of ['chatMessages','userInput','sendButton','chatStatus','chatStorageNote','reloadChat','recommendationsPanel','recommendationCards','guided-chat','resetAdvisorChat']) ids[id]=new Element();
  ids['guided-chat'].dataset.exploreUrl='/explore';
  let resets=0, confirm=false;
  const api={load:async()=>({mode:'user',messages:[{role:'user',content:'old message'}],recommendations:[]}),
    isSignedIn:()=>true,loadFavorites:async()=>({favorites:[]}),resetChat:async()=>{resets++;}};
  await vm.runInNewContext(fs.readFileSync('degree_path/static/js/guided-chat.js','utf8'),{
    document:{getElementById:id=>ids[id],createElement:()=>{const e=new Element();e.style={};return e;}},
    window:{chatApiReady:Promise.resolve(api),confirm:()=>confirm,location:{origin:'https://app.test',reload(){}}},URL,
  });
  await ids.resetAdvisorChat.click();
  assert.equal(resets,0);
  confirm=true;
  await ids.resetAdvisorChat.click();
  assert.equal(resets,1);
  assert.equal(ids.chatMessages.children.length,1); // Fresh local greeting.
  assert.equal(ids.recommendationCards.children.length,0);
  assert.equal(ids.userInput.disabled,false);
  assert.match(ids.chatStatus.textContent,/Chat reset/);
  console.log('Explore preference controls and chat reset UI tests passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
