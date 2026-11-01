const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = name => fs.readFileSync(`degree_path/static/js/${name}.js`, 'utf8');
function boot(owner, storage, unavailable=false) {
  const window = {location:{origin:'https://app.test'},localStorage:{
    getItem:k=>{if(unavailable)throw Error('Blocked');return storage[k]||null;},
    setItem:(k,v)=>{if(unavailable)throw Error('Blocked');storage[k]=v;},
  }};
  vm.runInNewContext(source('saved-filter-store'),{document:{getElementById:()=>({dataset:{userId:owner}})},window,URL,URLSearchParams});
  return window.SavedFilterStore;
}
const storage = {};
const first = boot('42',storage);
const saved = first.save('state=CT&degrees=3&q=Computer&sort=net_price_asc&net_price_max=20000&page=4&csrf_token=secret&degree=3');
assert.equal(saved.duplicate,false);
const secondTab = boot('42',storage);
assert.equal(secondTab.read().length,1,'Filters survive navigation, a second tab, and browser reopening');
assert.equal(secondTab.save('net_price_max=20000&q=Computer&degrees=3&sort=net_price_asc&state=CT').duplicate,true);
assert.equal(secondTab.read().length,1,'Saving identical values does not create duplicates');
const url = new URL(secondTab.url(secondTab.read()[0].params));
assert.equal(url.pathname,'/explore'); assert.equal(url.searchParams.get('view'),'programs');
assert.equal(url.searchParams.get('q'),'Computer'); assert.equal(url.searchParams.get('degrees'),'3');
assert.equal(url.searchParams.get('sort'),'net_price_asc'); assert.equal(url.searchParams.get('net_price_max'),'20000');
assert.equal(url.searchParams.has('page'),false); assert.equal(url.searchParams.has('csrf_token'),false);
assert.equal(url.searchParams.has('degree'),false);
assert.equal(boot('99',storage).read().length,0,'Accounts must not share filter sets');
assert.equal(boot('',storage).read().length,0,'Guests must not see signed-in filter sets');
first.save('city=New+Haven&favorite_major=1107&favorite_major=4201');
assert.equal(first.read().length,2);
assert.deepEqual([...new URLSearchParams(first.read()[0].params).getAll('favorite_major')],['1107','4201']);
first.remove(saved.item.params);assert.equal(first.read().length,1);
assert.throws(()=>boot('42',storage,true).save('state=NY'),/Blocked/);
storage[first.key]='invalid json'; assert.throws(()=>first.read());
// Tab switching works without waiting for account or database requests.
class Element {
 constructor(){this.dataset={};this.hidden=false;this.handlers={};this.attributes={};}
 addEventListener(name,fn){this.handlers[name]=fn;}
 setAttribute(name,value){this.attributes[name]=value;}
 dispatchEvent(event){this.lastEvent=event;}
}
const ids = Object.fromEntries(['saved-workspace','saved-majors-panel','saved-programs-panel','saved-filters-panel','saved-majors-list','saved-compare-header','saved-compare-guidance','saved-compare-tray'].map(id=>[id,new Element()]));
const tabs=['majors','programs','filters'].map(view=>{const el=new Element();el.dataset.savedView=view;return el;});
ids['saved-workspace'].querySelectorAll=()=>tabs;ids['saved-workspace'].dataset.initialSavedView='filters';
let filterRenders=0;let selectedKind;
const location={origin:'https://app.test',href:'https://app.test/saved-majors?view=filters'};
const window={location,history:{replaceState:(_,__,url)=>{location.href=url;}},addEventListener:()=>{},SavedFilters:{render:()=>filterRenders++},SavedCompare:{setKind:value=>{selectedKind=value;}}};
vm.runInNewContext(source('saved-library-tabs'),{document:{getElementById:id=>ids[id]},window,URL,CustomEvent:class {constructor(type,options){this.type=type;this.detail=options.detail;}}});
assert.equal(ids['saved-filters-panel'].hidden,false);
assert.equal(ids['saved-majors-panel'].hidden,true);assert.equal(ids['saved-programs-panel'].hidden,true);
assert.equal(ids['saved-compare-tray'].hidden,true);assert.equal(filterRenders,1);
assert.equal(tabs[2].attributes['aria-pressed'],'true');
tabs[1].handlers.click();assert.equal(ids['saved-programs-panel'].hidden,false);
assert.equal(ids['saved-filters-panel'].hidden,true);assert.equal(ids['saved-compare-tray'].hidden,false);
assert.equal(selectedKind,'programs');assert.equal(ids['saved-workspace'].lastEvent.detail.view,'programs');
console.log('Saved filters passed: persistence, deduplication, account isolation, safe URLs, removal, storage failures, and independent tabs.');
