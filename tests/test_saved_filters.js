const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = name => fs.readFileSync(`degree_path/static/js/${name}.js`, 'utf8');
async function testDatabaseStore() {
 const calls=[];const window={};let response={created:true,id:4};let ok=true;
 vm.runInNewContext(source('saved-filter-store'),{window,URLSearchParams,document:{getElementById:()=>({dataset:{userId:'42',csrf:'token'}})},fetch:async(path,options)=>{calls.push({path,options});return {ok,json:async()=>response};}});
 const store=window.SavedFilterStore;
 await store.save('view=programs&major_filter=favorites&favorite_major=7&favorite_major=7&favorite_major=8&school_name=College&state=ct&degree_form=1&degree=3&net_price_max=0&q=bio&sort=net_price_asc');
 let body=JSON.parse(calls[0].options.body);
 assert.deepEqual(body.majors,['7','8']);assert.deepEqual(body.states,['CT']);assert.equal(body.degrees,'3');assert.equal(body.net_price_max,0);
 assert.equal(body.search_text,'bio');assert.equal(body.sort_order,'net_price_asc');assert.equal(body.user_id,undefined);
 assert.equal(calls[0].options.headers['X-CSRF-Token'],'token');assert.equal(calls[0].options.headers['X-App-User-ID'],'42');
 await store.save('view=majors&saved=1&recs=1&majors=7&earnings_min=0&q=biology&sort=name_desc');
 body=JSON.parse(calls.at(-1).options.body);assert.equal(body.saved,true);assert.equal(body.recs,true);assert.equal(body.earnings_min,0);assert.equal(body.search_text,'biology');
 assert.equal(store.url({kind:'majors',id:4}),'/saved-searches/majors/4/apply');
 response={searches:[{id:4}]};assert.equal((await store.read()).length,2);
 response={deleted:true};await store.remove({kind:'majors',id:4});assert.equal(calls.at(-1).options.method,'DELETE');
 response={created:false,id:null};assert.equal((await store.save('')).duplicate,true);
 ok=false;response={error:'Expired session'};await assert.rejects(store.read(),/Expired session/);
 const guest={};vm.runInNewContext(source('saved-filter-store'),{window:guest,URLSearchParams,document:{getElementById:()=>null}});
 await assert.rejects(guest.SavedFilterStore.save(''),/Sign in/);
 assert.throws(()=>store.bodyFor('major_filter=favorites'),/Select at least one major/);
 console.log('Database saved-search payloads, account/CSRF headers, guest errors, duplicate reporting, and restore URLs passed.');
}
testDatabaseStore().catch(error=>{console.error(error);process.exitCode=1;});
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
console.log('Independent Saved tabs passed.');
