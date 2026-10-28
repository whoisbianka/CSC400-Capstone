const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('degree_path/static/js/saved-compare-tray.js', 'utf8');
class Element {
  constructor() { this.children = []; this.dataset = {}; this.attributes = {}; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  setAttribute(k, v) { this.attributes[k] = v; }
  addEventListener(k, handler) { this[k] = handler; }
  closest() { return this.article; }
}
function boot(owner, storage) {
  const ids = Object.fromEntries(['saved-workspace','saved-compare-tray','account-navigation','saved-tray-title','saved-tray-hint','saved-tray-items','saved-tray-clear','saved-tray-compare','saved-compare-header','saved-compare-guidance'].map(id=>[id,new Element()]));
  ids['account-navigation'].dataset.userId = owner;
  ids['saved-workspace'].dataset.compareUrl = '/compare';
  const buttons = [];
  ids['saved-workspace'].querySelectorAll = () => buttons;
  const window = {sessionStorage:{getItem:k=>storage[k]||null,setItem:(k,v)=>{storage[k]=v;}},location:{origin:'https://app.test',assign:url=>{window.destination=url;}}};
  vm.runInNewContext(source,{document:{getElementById:id=>ids[id],createElement:()=>new Element()},window,URL});
  function items(kind, count=4) {
    const data = Array.from({length:count},(_,i)=>({id:i+1,label:`${kind} ${i+1}`}));
    const result = data.map(item=>{
      const button = window.SavedCompare.button(kind,item);
      button.article = new Element(); buttons.push(button); return button;
    });
    window.SavedCompare.sync(kind,data);
    return result;
  }
  return {ids,window,items};
}
const storage = {};
const a = boot('42',storage);
const majors = a.items('majors');
majors[0].click();
assert.equal(a.ids['saved-tray-compare'].disabled,true);
majors[1].click();majors[2].click();majors[3].click();
assert.match(a.ids['saved-tray-title'].textContent,/3 of 3 majors/);
assert.equal(majors[3].disabled,true);
assert.equal(majors[0].article.dataset.selected,'true');
const programs = a.items('programs');
a.window.SavedCompare.setKind('programs');
assert.equal(a.ids['saved-tray-compare'].disabled,true,'Majors cannot be mixed with programs');
programs[0].click();programs[1].click();
a.ids['saved-tray-compare'].click();
let destination = new URL(a.window.destination);
assert.equal(destination.searchParams.get('kind'),'programs');
assert.equal(destination.searchParams.get('ids'),'1,2');
assert.equal(destination.hash,'#compare-table-container');
a.window.SavedCompare.setKind('majors');
assert.match(a.ids['saved-tray-title'].textContent,/3 of 3 majors/);
a.ids['saved-tray-items'].children[0].children[1].click();
assert.equal(majors[3].disabled,false);
a.ids['saved-tray-compare'].click();
destination = new URL(a.window.destination);
assert.equal(destination.searchParams.get('kind'),'majors');
assert.equal(destination.searchParams.get('ids'),'2,3');
const restored = boot('42',storage);
restored.items('majors');
assert.match(restored.ids['saved-tray-title'].textContent,/2 of 3 majors/);
restored.window.SavedCompare.sync('majors',[{id:3,label:'Remaining major'}]);
assert.match(restored.ids['saved-tray-title'].textContent,/1 of 3 majors/,'Unfavorited items leave the shortlist');
assert.equal(restored.ids['saved-tray-compare'].disabled,true);
const other = boot('99',storage);
other.items('majors');
assert.equal(other.ids['saved-tray-compare'].disabled,true,'Selections must be scoped to the account');
a.ids['saved-tray-clear'].click();
assert.equal(a.ids['saved-tray-compare'].disabled,true);
assert.equal(a.ids['saved-tray-items'].children.length,0);
console.log('Saved comparison tray passed: limits, separate types, chips, direct table links, restore, pruning, and account isolation.');
