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
  for(const id of ['favorites-page','favoriteCards','favoritesStatus','retryFavorites','favorites-heading']) ids[id]=new Element();
  ids['favorites-page'].dataset.exploreUrl='/explore';
  const tabs=['majors','programs'].map(kind=>{const tab=new Element();tab.dataset.favoriteKind=kind;return tab;});
  const requests=[]; const changes=[];
  const request=kind=>{const d=deferred();requests.push({kind,...d});return d.promise;};
  const api={loadFavorites:()=>request('majors'),loadProgramFavorites:()=>request('programs'),
    setProgramFavorite:async(id,value)=>{changes.push([id,value]);},setFavorite:async()=>{throw Error('Wrong favorite API');}};
  vm.runInNewContext(fs.readFileSync('degree_path/static/js/favorites.js','utf8'),{
    document:{getElementById:id=>ids[id],querySelectorAll:()=>tabs,createElement:tag=>new Element(tag)},
    window:{chatApiReady:Promise.resolve(api),location:{origin:'https://app.test'}},URL,
  });
  await flush();
  tabs[1].click();
  requests[1].resolve({favorites:[{program_id:10,major:'Biology',college:'College',credential:'Bachelor',url:'/programs/10'}]});
  await flush();
  requests[0].resolve({favorites:[{cipcode:7,major:'Stale major'}]});
  await flush();
  let cards=ids['favoriteCards'].children;
  assert.equal(cards.length,1);
  assert.equal(cards[0].children[0].textContent,'Biology');
  assert.equal(cards[0].children.find(c=>c.tag==='a').href,'/programs/10');
  await cards[0].children.find(c=>c.tag==='button').click();
  assert.deepEqual(changes,[[10,false]]);
  assert.equal(ids['favoriteCards'].children.length,0);
  assert.match(ids['favoritesStatus'].textContent,/No favorite programs/);

  const buttons=[10,11].map(id=>{const b=new Element();b.dataset.programFavorite=String(id);return b;});
  const status=new Element();const retry=new Element();let loads=0;let fail=false;
  const api2={loadProgramFavorites:async()=>{loads++;return {favorites:[{program_id:10}]};},
    setProgramFavorite:async(id,favorite)=>{if(fail)throw Error('Save failed');return {favorite};}};
  await vm.runInNewContext(fs.readFileSync('degree_path/static/js/program-card-favorites.js','utf8'),{
    document:{querySelectorAll:()=>buttons,getElementById:id=>id==='program-favorites-status'?status:retry},
    window:{chatApiReady:Promise.resolve(api2)},
  });
  assert.equal(loads,1,'Load saved states once for the whole page');
  assert.equal(buttons[0].textContent,'Remove favorite');
  assert.equal(buttons[1].textContent,'Favorite program');
  await buttons[1].click();
  assert.equal(buttons[1].textContent,'Remove favorite');
  fail=true;
  await buttons[1].click();
  assert.equal(buttons[1].textContent,'Remove favorite','Failed requests preserve confirmed state');
  assert.equal(buttons[1].disabled,false);
  assert.equal(status.textContent,'Save failed');
  console.log('Favorites UI passed: tab race protection, program removal, batch card states and failed saves.');
})().catch(error=>{console.error(error);process.exitCode=1;});
