const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor() { this.style = {}; this.children = []; this.dataset = {}; this.attributes = {}; this.listeners = {}; this.value = ''; this.scrollHeight = 46; }
  setAttribute(k,v) { this.attributes[k] = v; }
  append(...items) { items.forEach(item => { item.parent = this; }); this.children.push(...items); }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter(item => item !== this); }
  appendChild(item) { this.append(item); }
  replaceChildren(...items) { this.children = items; }
  addEventListener(k,v) { this.listeners[k] = v; }
  focus() {}
}
const nodes = Object.fromEntries(['chatMessages','userInput','sendButton','chatStatus','chatStorageNote','reloadChat','recommendationCards','guided-chat'].map(id => [id,new Element()]));
nodes['guided-chat'].dataset.majorUrl = '/majors/0';
nodes['guided-chat'].dataset.exploreUrl = '/explore';
let events = 0;
let resolveSend, rejectSend;
let sends = 0;
const recommendation = {cipcode:26,major:'Biology <script>',matching_keywords:2,evidence:[]};
(async () => {
  await vm.runInNewContext(fs.readFileSync('degree_path/static/js/guided-chat.js','utf8'), {
    document: {getElementById:id=>nodes[id], createElement:tag=>Object.assign(new Element(), {tagName:tag}), createTextNode:text=>({textContent:text}), dispatchEvent:e=>{ assert.equal(e.type,'major-controls:render'); events++; }},
    URL,
    Event: class { constructor(type) {this.type=type;} },
    window: {addEventListener:()=>{}, location: {origin:'http://localhost'}, chatApiReady:Promise.resolve({load:async()=>({mode:'guest',messages:[{role:'assistant',content:'Compare **Biology** and **<img src=x onerror=alert(1)>**.\nUnmatched **marker',search_card:{label:'Explore programs',summary:'MA · small',url:'/explore?school_size=small&state=MA'}}],recommendations:[recommendation]}), send:()=>{ sends++; return new Promise((resolve,reject)=>{resolveSend=resolve;rejectSend=reject;}); }})},
  });
  const formatted = nodes.chatMessages.children[0].children[2];
  assert.equal(formatted.children[1].tagName, 'strong');
  assert.equal(formatted.children[1].textContent, 'Biology');
  assert.equal(formatted.children[3].tagName, 'strong');
  assert.equal(formatted.children[3].textContent, '<img src=x onerror=alert(1)>');
  assert.equal(formatted.children[3].children.length, 0);
  assert.equal(formatted.children[4].textContent, '.\nUnmatched **marker');
  const restoredSearch = nodes.chatMessages.children.find(item=>item.className==='chat-search-card');
  assert.equal(new URL(restoredSearch.href).searchParams.get('school_size'), 'small');
  assert.equal(restoredSearch.tagName, 'a');
  assert.equal(restoredSearch.children.length, 2);
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
  assert.equal(nodes.userInput.style.height, '48px');
  nodes.userInput.value='Biology\nResearch';
  nodes.userInput.scrollHeight=94;
  nodes.userInput.listeners.input();
  assert.equal(nodes.userInput.style.height, '96px');
  nodes.userInput.scrollHeight=300;
  nodes.userInput.listeners.input();
  assert.equal(nodes.userInput.style.height, '140px');
  assert.equal(nodes.userInput.style.overflowY, 'auto');
  let prevented = 0;
  await nodes.userInput.listeners.keydown({key:'Enter',shiftKey:true,isComposing:false,preventDefault:()=>prevented++});
  await nodes.userInput.listeners.keydown({key:'Enter',shiftKey:false,isComposing:true,preventDefault:()=>prevented++});
  assert.equal(sends, 0);
  assert.equal(prevented, 0);
  const sending = nodes.userInput.listeners.keydown({key:'Enter',shiftKey:false,isComposing:false,preventDefault:()=>prevented++});
  assert.equal(prevented, 1);
  assert.equal(nodes.chatMessages.children.at(-2).children[2].textContent, 'Biology\nResearch');
  assert.equal(nodes.chatMessages.children.at(-1).children[2].textContent, 'Typing…');
  assert.equal(nodes.userInput.value, '');
  assert.equal(nodes.userInput.style.height, '48px');
  assert.equal(nodes.userInput.disabled, true);
  assert.equal(nodes.chatStatus.textContent, "");
  await nodes.sendButton.listeners.click();
  assert.equal(sends, 1);
  resolveSend({reply:'Tell me more.',mode:'guest',recommendations:[],search_card:{label:'Explore programs',summary:'NY · large',url:'/explore?school_size=large&state=NY'}});
  await sending;
  assert.equal(nodes.chatMessages.children.at(-2).children[2].textContent, 'Tell me more.');
  assert.equal(new URL(nodes.chatMessages.children.at(-1).href).searchParams.get('state'),'NY');
  assert.equal(nodes.chatMessages.children.filter(item=>item.className==='user-message').length, 1);
  assert.equal(nodes.chatMessages.children.some(item=>item.children[2]?.textContent==='Typing…'), false);
  const countBeforeFailure = nodes.chatMessages.children.length;
  nodes.userInput.value = 'My next\nmessage';
  const failing = nodes.sendButton.listeners.click();
  rejectSend(new Error('Network failed'));
  await failing;
  assert.equal(nodes.chatMessages.children.length, countBeforeFailure);
  assert.equal(nodes.userInput.value, 'My next\nmessage');
  assert.equal(nodes.userInput.style.height, '140px');
  assert.equal(nodes.reloadChat.hidden, false);
  assert.match(nodes.recommendationCards.children[0].textContent,/recommendations will appear/);
  assert.equal(events,2);
  assert.equal(nodes.userInput.disabled,false);
  console.log('Chat sidebar: major links, shared hearts, counts and updated recommendations passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
