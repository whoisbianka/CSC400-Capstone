const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
class Element {
  constructor(tag = 'div') { this.tag = tag; this.children = []; this.dataset = {}; this.attributes = {}; this.hidden = false; }
  appendChild(child) { this.children.push(child); return child; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(k, v) { this.attributes[k] = v; }
  addEventListener(event, fn) { this[event] = fn; }
  querySelectorAll(tag) { return this.children.flatMap(c => [...(c.tag === tag ? [c] : []), ...c.querySelectorAll(tag)]); }
}
const ids = {};
for (const id of ['compare-page','account-navigation','compare-favorites','compare-status','selection-count','compare-clear','compare-retry','compare-table-container','compare-table','compare-placeholder','favorite-list-title','comparison-title']) ids[id] = new Element();
ids['compare-page'].dataset.apiUrl = '/api/compare';
ids['account-navigation'].dataset.userId = '42';
ids['compare-table'].tHead = new Element('thead');
ids['compare-table'].tBodies = [new Element('tbody')];
const modes = ['majors','programs'].map(kind => {const e = new Element('button'); e.dataset.compareKind = kind; return e;});
const requests = [];
const context = {
  document: {getElementById: id => ids[id],querySelectorAll: () => modes,createElement: tag => new Element(tag)},
  window: {location:{origin:'https://app.test'}},
  ComparisonValues: require('../degree_path/static/js/comparison-values.js'), URL, AbortController,
  // Deliberately ignore abort to verify the request-generation guard too.
  fetch: (url, options) => new Promise(resolve => requests.push({url,options,resolve})),
};
const flush = () => new Promise(resolve => setImmediate(resolve));
const reply = (index, items) => requests[index].resolve({ok:true,json:async()=>({items,metrics:[{key:'earnings',label:'Earnings',format:'money',direction:'higher'}]})});
(async () => {
  vm.runInNewContext(fs.readFileSync('degree_path/static/js/compare.js','utf8'),context);
  assert.equal(requests.length,1);
  assert.equal(requests[0].options.headers['X-App-User-ID'],'42');
  reply(0,[{id:1,name:'A',earnings:100},{id:2,name:'B',earnings:200},{id:3,name:'C',earnings:300},{id:4,name:'D',earnings:400},{id:5,name:'E',earnings:500}]);
  await flush();
  let inputs=ids['compare-favorites'].querySelectorAll('input');
  assert.equal(inputs.length,5);
  inputs[0].checked=true; inputs[0].change();
  assert.equal(ids['compare-table-container'].hidden,true);
  inputs[1].checked=true; inputs[1].change();
  assert.equal(ids['compare-table-container'].hidden,false);
  assert.equal(inputs[2].disabled,false);
  assert.equal(ids['compare-table'].tHead.children[0].children.length,3);
  inputs[2].checked=true; inputs[2].change();
  assert.equal(ids['compare-table'].tHead.children[0].children.length,4);
  assert.equal(ids['compare-table'].dataset.selections,'3');
  assert.equal(inputs[3].disabled,true);
  assert.equal(inputs[4].disabled,true);
  assert.equal(ids['selection-count'].textContent,'3 of 3 selected');
  // Even a synthetic change cannot add a fourth selection.
  inputs[3].checked=true; inputs[3].change();
  assert.equal(inputs[3].checked,false);
  assert.equal(ids['compare-table'].tHead.children[0].children.length,4);
  assert.equal(ids['compare-table'].tBodies[0].children.length,1);
  inputs[0].checked=false; inputs[0].change();
  assert.equal(ids['compare-table-container'].hidden,false);
  assert.equal(inputs[4].disabled,false);
  inputs[2].checked=false; inputs[2].change();
  assert.equal(ids['compare-table-container'].hidden,true);
  assert.equal(inputs[2].disabled,false);
  ids['compare-clear'].click();
  assert.equal(ids['selection-count'].textContent,'0 of 3 selected');
  modes[0].click(); // older request
  modes[1].click(); // newer request
  assert.equal(ids['compare-table'].tBodies[0].children.length,0);
  reply(2,[{id:9,name:'Program',college:'School',credential:'Bachelor'}]);
  await flush();
  reply(1,[{id:1,name:'Stale major'}]);
  await flush();
  inputs=ids['compare-favorites'].querySelectorAll('input');
  assert.equal(inputs.length,1);
  assert.equal(Number(inputs[0].value),9);
  assert.equal(ids['favorite-list-title'].textContent,'Favorite programs');
  assert.match(ids['compare-status'].textContent,/at least two/);
  // The saved library hands off selections without asking users to select again.
  requests.length=0;
  const persisted={};
  context.window.sessionStorage={getItem:key=>persisted[key]||null,setItem:(key,value)=>{persisted[key]=value;}};
  context.window.location.href='https://app.test/compare?view=favorites&kind=programs&ids=9,10,999,11';
  vm.runInNewContext(fs.readFileSync('degree_path/static/js/compare.js','utf8'),context);
  assert.equal(new URL(requests[0].url).searchParams.get('kind'),'programs');
  reply(0,[{id:9,name:'Program A'},{id:10,name:'Program B'},{id:11,name:'Program C'}]);
  await flush();
  assert.equal(ids['compare-table-container'].hidden,false);
  assert.equal(ids['selection-count'].textContent,'2 of 3 selected');
  inputs=ids['compare-favorites'].querySelectorAll('input');
  assert.equal(inputs[0].checked,true);
  assert.equal(inputs[1].checked,true);
  assert.equal(inputs[2].checked,false,'Ignore unavailable selections and cap URL IDs to three');
  assert.deepEqual(JSON.parse(persisted['saved-comparison:42']).programs,[9,10]);
  ids['compare-clear'].click();
  assert.deepEqual(JSON.parse(persisted['saved-comparison:42']).programs,[]);
  console.log('Comparison UI checks passed: selection limit, reset, empty table and stale-response protection.');
})().catch(error=>{console.error(error);process.exitCode=1;});
