const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor() { this.style = {}; this.children = []; this.dataset = {}; this.attributes = {}; this.listeners = {}; this.value = ''; }
  setAttribute(k,v) { this.attributes[k] = v; }
  append(...items) { this.children.push(...items); }
  appendChild(item) { this.append(item); }
  replaceChildren(...items) { this.children = items; }
  addEventListener(k,v) { this.listeners[k] = v; }
  focus() {}
}
const nodes = Object.fromEntries(['chatMessages','userInput','sendButton','chatStatus','chatStorageNote','reloadChat','recommendationCards','guided-chat'].map(id => [id,new Element()]));
nodes['guided-chat'].dataset.majorUrl = '/majors/0';
nodes['guided-chat'].dataset.exploreUrl = '/explore';
let events = 0;
const recommendation = {cipcode:26,major:'Biology <script>',matching_keywords:2,evidence:[]};
(async () => {
  await vm.runInNewContext(fs.readFileSync('degree_path/static/js/guided-chat.js','utf8'), {
    document: {getElementById:id=>nodes[id], createElement:()=>new Element(), dispatchEvent:e=>{ assert.equal(e.type,'major-controls:render'); events++; }},
    URL,
    Event: class { constructor(type) {this.type=type;} },
    window: {location: {origin:'http://localhost'}, chatApiReady:Promise.resolve({load:async()=>({mode:'guest',messages:[],recommendations:[recommendation]}), send:async()=>({reply:'Tell me more.',mode:'guest',recommendations:[]})})},
  });
  const card = nodes.recommendationCards.children[0];
  const link = card.children[0].children[0].children[0];
  assert.equal(link.href,'/majors/26');
  assert.equal(link.textContent,'Biology <script>');
  const colleges = new URL(card.children[0].children[2].href);
  assert.equal(colleges.pathname, '/explore');
  assert.equal(colleges.searchParams.get('cipcode'), '26');
  assert.equal(colleges.searchParams.get('view'), 'programs');
  assert.equal(card.children[1].dataset.saveMajor,'26');
  assert.equal(card.children[1].dataset.favoriteIcon,'heart');
  assert.equal(card.children[0].children[1].textContent,'2 matching interests');
  nodes.userInput.value='Biology';
  await nodes.sendButton.listeners.click();
  assert.match(nodes.recommendationCards.children[0].textContent,/recommendations will appear/);
  assert.equal(events,2);
  assert.equal(nodes.userInput.disabled,false);
  console.log('Chat sidebar: major links, shared hearts, counts and updated recommendations passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
