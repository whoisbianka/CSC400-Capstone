// Apply filters explicitly, synchronize degree values, and restore state on Back.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const handlers = {};
const choices = [{value:'2',checked:false},{value:'3',checked:true}];
let valid = true;
let submissions = 0;
const form = {
  querySelectorAll: () => choices,
  addEventListener: (event, handler) => { (handlers[event] ||= []).push(handler); },
  reportValidity: () => valid,
  requestSubmit: () => { submissions++; handlers.submit.forEach(handler => handler()); },
};
const values = {value:''};
const loading = {hidden:true};
const results = {setAttribute:(name,value) => { results[name]=value; },removeAttribute:name => { delete results[name]; }};
let pageshow;
let click;
vm.runInNewContext(fs.readFileSync('degree_path/static/js/explore.js','utf8'),{
  document:{
    getElementById:id=>({'degree-filter-form':form,'degree-values':values,'explore-loading':loading})[id],
    querySelector:()=>results,
    querySelectorAll:()=>[{addEventListener:(_,handler)=>{click=handler;}}],
  },
  window:{addEventListener:(_,handler)=>{pageshow=handler;}},
});
assert.equal(handlers.change, undefined, 'Editing filters must not submit before Apply filters');
form.requestSubmit();
assert.equal(submissions,1);
assert.equal(values.value,'3');
assert.equal(loading.hidden,false);
assert.equal(results['aria-busy'],'true');
pageshow();
assert.equal(loading.hidden,true);
assert.equal(results['aria-busy'],undefined);
click({button:0,ctrlKey:true});
assert.equal(loading.hidden,true,'Opening another tab must not leave this page loading');
click({button:0});
assert.equal(loading.hidden,false);
console.log('Explicit filter submission, degree synchronization, loading feedback, and Back restoration passed.');
