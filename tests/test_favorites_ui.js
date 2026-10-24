const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag = 'div') {this.tag=tag;this.dataset={};this.children=[];this.attributes={};}
  appendChild(child) {child.parent=this;this.children.push(child);}
  append(...children) {children.forEach(child=>this.appendChild(child));}
  replaceChildren(...children) {this.children=[];this.append(...children);}
  remove() {this.parent.children=this.parent.children.filter(child=>child!==this);}
  setAttribute(key,value) {this.attributes[key]=value;}
  addEventListener(event,handler) {this[event]=handler;}
}
const deferred = () => {let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const flush = () => new Promise(resolve=>setImmediate(resolve));
(async () => {
  const ids={};
  for(const id of ['saved-workspace','saved-majors-panel','saved-programs-panel','favorited-program-cards','saved-programs-status','saved-program-count','saved-programs-retry']) ids[id]=new Element();
  ids['saved-workspace'].dataset.initialSavedView='programs';
  const tabs=['majors','programs'].map(kind=>{const tab=new Element();tab.dataset.savedView=kind;return tab;});
  const requests=[], changes=[];
  const api={loadProgramFavorites:()=>{const d=deferred();requests.push(d);return d.promise;},setProgramFavorite:async(id,value)=>{changes.push([id,value]);}};
  vm.runInNewContext(fs.readFileSync('degree_path/static/js/saved-programs.js','utf8'),{
    document:{getElementById:id=>ids[id],querySelectorAll:()=>tabs,createElement:tag=>new Element(tag)},
    window:{chatApiReady:Promise.resolve(api)},
  });
  await flush();
  tabs[0].click();
  tabs[1].click();
  requests[1].resolve({favorites:[{program_id:10,major:'Biology',college:'College',credential:'Bachelor',city:'City',state:'CT'}]});
  await flush();
  requests[0].resolve({favorites:[{program_id:99,major:'Stale program'}]});
  await flush();
  const cards=ids['favorited-program-cards'].children;
  assert.equal(cards.length,1,'Old tab requests must not replace current saved programs');
  assert.equal(cards[0].children[0].textContent,'Biology');
  const controls=cards[0].children[3];
  assert.equal(controls.children[0].href,'/programs/10');
  assert.equal(controls.children[0].target,'_blank');
  await controls.children[1].click();
  assert.deepEqual(changes,[[10,false]]);
  assert.equal(ids['favorited-program-cards'].children.length,0);
  assert.match(ids['saved-programs-status'].textContent,/No favorite programs/);
  assert.equal(tabs[1].attributes['aria-pressed'],'true');

  const buttons=[10,11].map(id=>{const b=new Element();b.dataset.programFavorite=String(id);return b;});
  const status=new Element();const retry=new Element();let loads=0;let fail=false;const notifications=[];
  const api2={loadProgramFavorites:async()=>{loads++;return {favorites:[{program_id:10}]};},
    setProgramFavorite:async(id,favorite)=>{if(fail)throw Error('Save failed');return {favorite};}};
  await vm.runInNewContext(fs.readFileSync('degree_path/static/js/program-card-favorites.js','utf8'),{
    document:{querySelectorAll:()=>buttons,getElementById:id=>id==='program-favorites-status'?status:retry},
    window:{chatApiReady:Promise.resolve(api2),MajorSaveFeedback:{show:options=>notifications.push(options)}},
  });
  assert.equal(loads,1,'Load saved states once for the whole page');
  assert.equal(buttons[0].textContent,'♥');
  assert.equal(buttons[1].textContent,'♡');
  assert.equal(buttons[0].attributes['aria-pressed'],'true');
  assert.equal(buttons[1].attributes['aria-label'],'Favorite this program');
  await buttons[1].click();
  assert.equal(buttons[1].textContent,'♥');
  assert.equal(notifications.length,1,'A confirmed program save shows feedback');
  assert.equal(notifications[0].programName,'This program');
  fail=true;
  await assert.rejects(notifications[0].onUndo(),/Save failed/);
  assert.equal(buttons[1].textContent,'♥','Failed Undo preserves the saved heart');
  assert.equal(buttons[1].disabled,false);
  fail=false;
  await notifications[0].onUndo();
  assert.equal(buttons[1].textContent,'♡','Undo clears the heart after the server confirms removal');
  assert.equal(notifications.length,1);
  fail=true;
  await buttons[1].click();
  assert.equal(buttons[1].textContent,'♡','Failed requests preserve confirmed state');
  assert.equal(notifications.length,1,'Failed saves must not show a new success notification');
  assert.equal(buttons[1].disabled,false);
  assert.equal(status.textContent,'Save failed');
  console.log('Favorites UI passed: shared saved library, program feedback, Undo, failed saves and tab race protection.');
})().catch(error=>{console.error(error);process.exitCode=1;});
