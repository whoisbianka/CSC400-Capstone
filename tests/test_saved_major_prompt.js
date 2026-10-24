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
  const listeners = {}, requests = [];
  let expire = false;
  vm.runInNewContext(source, {
    document: {
      body, createElement: tag => new Element(tag),
      getElementById: id => ({'account-navigation':nav, 'saved-major-signin':signIn})[id] || null,
      querySelector: () => ({content: 'csrf'}),
      querySelectorAll: selector => selector === '[data-save-major]' ? [major] : [],
      addEventListener: (event, handler) => { listeners[event] = handler; },
    },
    window: {},
    fetch: async (path, options) => {
      requests.push({path, options});
      return {ok: !expire, status: expire ? 401 : 200,
        json: async () => expire ? {error:'Sign in required'} : {favorites:[], favorite:true}};
    },
  });
  const dialog = body.children.find(child => child.tag === 'dialog');
  return {major, program, dialog, requests,
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
  const account = fixture('42');
  await flush();
  await account.click(account.major);
  assert.equal(account.dialog.open, false, 'Signed-in users save without a prompt');
  const saved = account.requests.find(request => request.options.method === 'POST');
  assert.equal(saved.path, '/api/favorites');
  assert.deepEqual(JSON.parse(saved.options.body), {cipcode:1107, favorite:true});
  assert.equal(saved.options.headers['X-CSRF-Token'], 'csrf');
  account.expire();
  await account.click(account.major);
  assert.equal(account.dialog.open, true, 'Expired sessions show the major sign-in prompt');
  assert.match(account.dialog.children[1].textContent, /save this major/);
  console.log('Save prompts passed: guest majors/programs, Cancel, Sign in, authenticated saves, and expired sessions.');
})().catch(error => { console.error(error); process.exitCode = 1; });
