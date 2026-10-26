// The general-major library must never request or render individual college programs.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag='div') { this.tag=tag;this.className='';this.children=[];this.dataset={};this.attributes={}; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children=[...children]; }
  setAttribute(name,value) { this.attributes[name]=value; }
}
(async()=>{
  const ids=Object.fromEntries(['saved-major-cards','saved-library','saved-empty','saved-major-count'].map(id=>[id,new Element()]));
  const synced=[];
  const window={SavedCompare:{
    button:(kind,item)=>{const b=new Element('button');b.textContent='Add to compare';b.dataset.compareKind=kind;b.dataset.libraryCompare=item.id;return b;},
    sync:(kind,items)=>synced.push({kind,items}),
  }};
  vm.runInNewContext(fs.readFileSync('degree_path/static/js/saved-majors.js','utf8'),{
    document:{getElementById:id=>ids[id],createElement:tag=>new Element(tag)},window,Intl,
  });
  const requests=[];
  const rows=[{cipcode:1107,major:'Computer Science',description:'Study computing.',description_source:'Catalog',earnings:65000,program_count:3,school_count:2},
    {cipcode:4201,major:'Psychology',description:null,earnings:null,program_count:0,school_count:0}];
  await window.SavedMajors.refresh(async path=>{requests.push(path);return {majors:rows};},[{cipcode:1107},{cipcode:4201}]);
  assert.deepEqual(requests,['/api/saved-majors/summary']);
  assert.equal(ids['saved-major-cards'].children.length,2);
  const card=ids['saved-major-cards'].children[0];
  assert.equal(card.className,'major-catalog-card');
  const body=card.children[0],heading=body.children[1];
  assert.equal(heading.children[0].textContent,'Computer Science');
  assert.equal(heading.children[1].dataset.saveMajor,'1107');
  assert.equal(body.children[2].textContent,'Study computing.');
  assert.equal(card.children[1].children[1].href,'/explore?view=programs&cipcode=1107');
  assert.equal(card.children[1].children[0].textContent,'Add to compare');
  assert.equal(card.children[1].children[0].dataset.compareKind,'majors');
  assert.equal(card.children[1].children[0].dataset.libraryCompare,1107);
  assert.equal(synced[0].kind,'majors');
  assert.equal(synced[0].items.length,2);
  const nodes=[];function collect(n){nodes.push(n);n.children.forEach(collect);}collect(ids['saved-major-cards']);
  assert.equal(nodes.some(n=>n.className==='saved-program-card'),false);
  assert.equal(nodes.some(n=>n.tag==='input'),false,'No comparison checkboxes in general-major cards');
  assert.equal(ids['saved-empty'].hidden,true);
  await window.SavedMajors.refresh(()=>{throw Error('Empty library should not fetch');},[]);
  assert.equal(ids['saved-major-cards'].children.length,0);
  assert.equal(ids['saved-library'].hidden,true);
  assert.equal(ids['saved-empty'].hidden,false);
  console.log('General saved-major cards passed: summary-only data, matching Explore cards, no college programs, and empty state.');
})().catch(error=>{console.error(error);process.exitCode=1;});
