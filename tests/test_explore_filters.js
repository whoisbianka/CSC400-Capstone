const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor() {this.dataset={};this.children=[];this.handlers={};this.value='';}
  addEventListener(event, handler) {this.handlers[event]=handler;}
  replaceChildren() {this.children=[];}
  appendChild(child) {this.children.push(child);}
  setAttribute() {}
  removeAttribute() {}
}
const ids={};
for(const id of ['degree-filter-form','major-filter','major-name','major-name-fields','major-favorite-fields','major-name-options','major-search-status','degree-values','explore-loading']) ids[id]=new Element();
const favorites=[new Element(),new Element()];
ids['major-favorite-fields'].querySelectorAll=()=>favorites;
ids['degree-filter-form'].querySelectorAll=()=>[{value:'3'}];
ids['major-filter'].value='all';
ids['major-name'].dataset.suggestionsUrl='/api/major-names';
let timer;
const requests=[];
vm.runInNewContext(fs.readFileSync('degree_path/static/js/explore.js','utf8'),{
  document:{getElementById:id=>ids[id],querySelectorAll:()=>[],querySelector:()=>new Element(),createElement:()=>new Element()},
  window:{location:{origin:'https://app.test'},addEventListener(){}},URL,
  setTimeout:fn=>{timer=fn;return 1;},clearTimeout:()=>{},
  fetch:url=>new Promise(resolve=>requests.push({url,resolve})),
});
(async()=>{
  assert.equal(ids['major-name'].disabled,true);
  ids['major-filter'].value='favorites';ids['major-filter'].handlers.change();
  assert.equal(ids['major-favorite-fields'].hidden,false);
  assert.equal(favorites[0].disabled,false);
  // No form-level change handler: users can select multiple favorites before applying.
  assert.equal(ids['degree-filter-form'].handlers.change,undefined);
  ids['degree-filter-form'].handlers.submit();
  ids['major-filter'].value='name';ids['major-filter'].handlers.change();
  assert.equal(ids['major-name'].required,true);
  assert.equal(favorites[0].disabled,true);
  ids['major-name'].value='bio';ids['major-name'].handlers.input();
  const first=timer();
  ids['major-name'].value='art';ids['major-name'].handlers.input();
  const second=timer();
  requests[1].resolve({ok:true,json:async()=>({majors:[{name:'Art'}]})});await second;
  requests[0].resolve({ok:true,json:async()=>({majors:[{name:'Biology'}]})});await first;
  assert.equal(ids['major-name-options'].children.length,1);
  assert.equal(ids['major-name-options'].children[0].value,'Art');
  console.log('Explore filter controls and stale suggestion protection passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
