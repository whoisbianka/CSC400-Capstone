// Undo remains available without a timer, and disappearing controls retain keyboard focus.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
let document;
class Element {
  constructor() { this.children = []; this.listeners = {}; this.hidden = false; this.isConnected = true; this.textContent = ''; this.classList = {add() {}, remove() {}}; }
  append(...items) { this.children.push(...items); }
  setAttribute() {}
  addEventListener(type, handler) { this.listeners[type] = handler; }
  contains(element) { return this === element || this.children.some(child => child.contains(element)); }
  focus() { document.activeElement = this; }
  getBoundingClientRect() { return {height: 100}; }
}
document = {body: new Element(), documentElement: {style: {setProperty() {}}}, createElement: () => new Element()};
const window = {};
let timers = 0;
vm.runInNewContext(fs.readFileSync('degree_path/static/js/saved-major-feedback.js', 'utf8'), {document, window, setTimeout() { timers++; }, clearTimeout() {}});
(async () => {
  const origin = new Element();
  const toast = document.body.children[0];
  const content = toast.children[1];
  const undo = content.children[1].children[1];
  const dismiss = toast.children[2];
  window.MajorSaveFeedback.show({majorName: 'Computer Science', button: origin, onUndo: async () => {}});
  assert.equal(toast.hidden, false);
  assert.equal(undo.hidden, false);
  assert.equal(timers, 0, 'Saving must not schedule expiration of the Undo action');
  undo.focus();
  await undo.listeners.click();
  assert.equal(undo.hidden, true);
  assert.equal(document.activeElement, dismiss, 'Focus must leave the hidden Undo control');
  dismiss.listeners.click();
  assert.equal(toast.hidden, true);
  assert.equal(document.activeElement, origin, 'Dismissal returns focus to the save button');
  console.log('Accessible save feedback passed: persistent Undo and focus restoration.');
})().catch(error => { console.error(error); process.exitCode = 1; });
