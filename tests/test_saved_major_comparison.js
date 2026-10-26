const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag = 'div') { this.tag = tag; this.children = []; this.dataset = {}; this.attributes = {}; this.checked = false; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = [...children]; }
  setAttribute(k, v) { this.attributes[k] = v; }
  addEventListener(k, fn) { this[k] = fn; }
  querySelector() { return null; }
}
const ids = Object.fromEntries(['saved-program-groups','saved-library','saved-empty','saved-major-count','saved-comparison','saved-comparison-results','saved-comparison-prompt','saved-differences','saved-selection-count','saved-comparison-head','saved-comparison-body'].map(id => [id, new Element()]));
const window = {};
vm.runInNewContext(fs.readFileSync('degree_path/static/js/saved-major-comparison.js','utf8'), {
  document: {getElementById: id => ids[id], createElement: tag => new Element(tag), querySelector: () => null}, window, Intl,
});
const program = (id, cost) => ({program_id:id, cipcode:1107, major:'Computer Science', college:`College ${id}`, city:'New Haven', state:'CT', credlev:3, npt4:cost, earnings:80000});
let groups;
const requests = [];
const api = async path => {
  requests.push(path);
  return path.includes('?page=') ? {programs:[program(5,9000)],page:2,has_next:false} : {majors:groups};
};
const select = (id, checked = true) => ids['saved-program-groups'].change({target:{closest:()=>({dataset:{compareProgram:id},checked})}});
const nodes = element => [element,...element.children.flatMap(nodes)];
(async () => {
  groups = [{cipcode:1107,name:'Computer Science',programs:[program(1,10000),program(2,12000),program(3,null),program(4,15000)],page:1,has_next:true}];
  await window.SavedMajors.refresh(api,[{cipcode:1107}]);
  assert.equal(requests[0],'/api/saved-majors/programs');
  select(1); assert.equal(ids['saved-comparison-results'].hidden,true);
  select(2); assert.equal(ids['saved-comparison-results'].hidden,false);
  assert.equal(ids['saved-comparison-head'].children[0].children.length,3);
  assert.ok(nodes(ids['saved-comparison-body']).some(n=>n.textContent==='✓ $2,000 less / year'));
  const allRows = ids['saved-comparison-body'].children.length;
  ids['saved-differences'].checked=true; ids['saved-differences'].change();
  assert.ok(ids['saved-comparison-body'].children.length < allRows);
  select(3); select(4);
  assert.equal(ids['saved-selection-count'].textContent,'3 of 3 programs selected');
  assert.equal(ids['saved-comparison-head'].children[0].children.length,4);
  assert.ok(nodes(ids['saved-program-groups']).filter(n=>n.tag==='input' && !n.checked).every(n=>n.disabled));
  assert.ok(!nodes(ids['saved-comparison-body']).some(n=>n.className==='saved-cell-best' || n.className==='saved-cell-worse'),'Missing cost keeps the row neutral');
  ids['saved-comparison-head'].click({target:{closest:()=>({dataset:{removeComparison:3}})}});
  const more = {dataset:{moreMajor:1107}};
  await ids['saved-program-groups'].click({target:{closest:()=>more}});
  assert.ok(requests.includes('/api/saved-majors/1107/programs?page=2'));
  select(5);
  assert.equal(ids['saved-selection-count'].textContent,'3 of 3 programs selected');
  groups = [];
  await window.SavedMajors.refresh(api,[]);
  assert.equal(ids['saved-library'].hidden,true);
  assert.equal(ids['saved-comparison'].hidden,true);
  assert.equal(ids['saved-selection-count'].textContent,'0 of 3 programs selected');
  console.log('Saved-major comparison passed: selection limit, annual differences, missing values, differences filter, pagination, removal and refresh.');
})().catch(error=>{console.error(error);process.exitCode=1;});
