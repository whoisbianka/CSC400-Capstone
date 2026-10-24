// Save prompts must work for guests without loading Clerk or writing favorites.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('degree_path/static/js/saved-major-controls.js', 'utf8');
class Element {
  constructor(tag = 'div') {
    this.tag = tag; this.dataset = {}; this.attributes = {}; this.children = [];
    this.listeners = {}; this.hidden = false; this.disabled = false; this.open = false;
  }
  append(...children) { for (const child of children) { child.parentElement = this; this.children.push(child); } }
  prepend(...children) { this.children.unshift(...children); }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener(event, handler) { this.listeners[event] = handler; }
  showModal() { this.open = true; }
  close() { this.open = false; }
  click() { return this.listeners.click?.({target: this, preventDefault() {}}); }
  querySelectorAll() { return []; }
  closest(selector) {
    if (selector === '[data-save-major]' && this.dataset.saveMajor) return this;
    if (selector === '[data-save-requires-signin]' && this.dataset.saveRequiresSignin) return this;
    return null;
  }
}
function fixture(userId = '') {
  const body = new Element('body'), nav = new Element('header');
  nav.dataset.userId = userId;
  const signIn = new Element('button');
  let signIns = 0;
  signIn.listeners.click = () => { signIns++; };
  const major = new Element('button'); major.dataset.saveMajor = '1107'; major.parentElement = new Element();
  const program = new Element('button'); program.dataset.saveRequiresSignin = 'program';
  const listeners = {}, requests = [], notifications = [];
  let expire = false, failSave = false, favorites = [];
  vm.runInNewContext(source, {
    document: {
      body, createElement: tag => new Element(tag),
      getElementById: id => ({'account-navigation':nav, 'saved-major-signin':signIn})[id] || null,
      querySelector: () => ({content: 'csrf'}),
      querySelectorAll: selector => selector === '[data-save-major]' ? [major] : [],
      addEventListener: (event, handler) => { listeners[event] = handler; },
    },
    window: {MajorSaveFeedback:{show:options=>notifications.push(options)}},
    fetch: async (path, options) => {
      requests.push({path, options});
      if (expire) return {ok:false,status:401,json:async()=>({error:'Sign in required'})};
      if (options.method === 'POST') {
        if (failSave) return {ok:false,status:503,json:async()=>({error:'Save unavailable'})};
        const value = JSON.parse(options.body);
        favorites = value.favorite ? [{cipcode:value.cipcode,major:'Computer Science'}] : [];
        return {ok:true,status:200,json:async()=>({favorite:value.favorite})};
      }
      return {ok:true,status:200,json:async()=>({favorites})};
    },
  });
  const dialog = body.children.find(child => child.tag === 'dialog');
  return {major, program, dialog, requests, notifications,
    failSave() { failSave = true; },
    get signIns() { return signIns; },
    expire() { expire = true; },
    click: target => listeners.click({target, preventDefault() {}}),
  };
}
const flush = () => new Promise(resolve => setImmediate(resolve));
(async () => {
  const guest = fixture();
  assert.equal(guest.dialog.open, false, 'Browsing must not open the prompt');
  await guest.click(guest.major);
  assert.equal(guest.dialog.open, true);
  assert.match(guest.dialog.children[1].textContent, /save this major/);
  assert.equal(guest.requests.length, 0, 'Guests must not send a save request');
  assert.equal(guest.signIns, 0, 'Confirmation must come before loading sign-in');
  const actions = guest.dialog.children[3].children;
  await actions[0].click();
  assert.equal(guest.dialog.open, false, 'Cancel closes the dialog');
  await guest.click(guest.program);
  assert.equal(guest.dialog.open, true);
  assert.match(guest.dialog.children[1].textContent, /save this program/);
  await actions[1].click();
  assert.equal(guest.dialog.open, false);
  assert.equal(guest.signIns, 1, 'Sign in forwards to the existing account action');
  assert.equal(guest.requests.length, 0);
  assert.equal(guest.notifications.length, 0, 'Guest attempts must never announce a successful save');
  const account = fixture('42');
  await flush();
  await account.click(account.major);
  assert.equal(account.dialog.open, false, 'Signed-in users save without a prompt');
  const saved = account.requests.find(request => request.options.method === 'POST');
  assert.equal(saved.path, '/api/favorites');
  assert.deepEqual(JSON.parse(saved.options.body), {cipcode:1107, favorite:true});
  assert.equal(saved.options.headers['X-CSRF-Token'], 'csrf');
  assert.equal(account.notifications.length, 1);
  assert.equal(account.notifications[0].majorName, 'Computer Science');
  await account.notifications[0].onUndo();
  const undo = account.requests.filter(r => r.options.method === 'POST').at(-1);
  assert.deepEqual(JSON.parse(undo.options.body), {cipcode:1107,favorite:false});
  assert.equal(account.major.attributes['aria-pressed'], 'false');
  const failed = fixture('42');
  await flush();
  failed.failSave();
  await failed.click(failed.major);
  assert.equal(failed.notifications.length, 0, 'Failed saves must never show a success notification');
  assert.equal(failed.major.attributes['aria-pressed'], 'false');

  account.expire();
  await account.click(account.major);
  assert.equal(account.dialog.open, true, 'Expired sessions show the major sign-in prompt');
  assert.match(account.dialog.children[1].textContent, /save this major/);
  assert.equal(account.notifications.length, 1, 'Expired sessions must not add success notifications');
  console.log('Save prompts and feedback passed: guests, authenticated saves, Undo, failed saves, and expired sessions.');
})().catch(error => { console.error(error); process.exitCode = 1; });
