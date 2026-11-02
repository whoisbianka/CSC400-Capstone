// Run: node tests/test_profile.js
const assert = require('node:assert/strict');
const {normalize, mount} = require('../degree_path/static/js/profile.js');
function element(extra = {}) {
  return {hidden: false, disabled: false, textContent: '', children: [], ...extra,
    addEventListener(type, handler) { this[type] = handler; },
    setAttribute(key, value) { this[key] = value; },
    focus() { this.focused = true; },
    replaceChildren() { this.children = []; this.textContent = ''; },
    appendChild(child) { this.children.push(child); }};
}
function fixture(metadata = {}) {
  const profile = normalize(metadata.pathfinderProfile);
  const controls = Object.fromEntries(Object.keys(profile).map(key => [key, element({value: ''})]));
  const ids = Object.fromEntries(['profile-account', 'profile-edit', 'profile-editor', 'profile-save', 'profile-cancel', 'profile-save-status', 'profile-name', 'profile-name-value', 'profile-avatar', 'profile-interests'].map(id => [id, element()]));
  ids['profile-account'].dataset = {clerkUserId: 'user_expected'};
  ids['profile-editor'].elements = {namedItem: key => controls[key]};
  ids['profile-editor'].reportValidity = () => true;
  const fields = ['school', 'major', 'graduation', 'goal'].map(key => element({dataset: {profileField: key}}));
  global.document = {getElementById: id => ids[id], querySelectorAll: () => fields, createElement: () => element()};
  const calls = [];
  const clerk = {session: {}, user: {id: 'user_expected', unsafeMetadata: metadata,
    async update(params) { calls.push(params); this.unsafeMetadata = params.unsafeMetadata; }}};
  mount(clerk, 'Account Name');
  return {ids, controls, fields, calls, clerk};
}
const submit = f => f.ids['profile-editor'].submit({preventDefault() {}});
(async () => {
  assert.equal(normalize({school: 42}).school, '');
  assert.equal(normalize({goal: 'x'.repeat(600)}).goal.length, 500);
  let f = fixture({otherFeature: {keep: true}, pathfinderProfile: {school: 'Example School', interests: 'Design, Design, Tech'}});
  assert.equal(f.fields[0].textContent, 'Example School');
  assert.equal(f.ids['profile-interests'].children.length, 2);
  assert.equal(f.ids['profile-edit'].disabled, false);
  f.ids['profile-edit'].click();
  f.controls.school.value = 'New School';
  f.controls.displayName.value = 'Alex Student';
  f.controls.goal.value = '<img src=x onerror=alert(1)>';
  await submit(f);
  assert.deepEqual(f.calls[0].unsafeMetadata.otherFeature, {keep: true});
  assert.equal(f.fields[0].textContent, 'New School');
  assert.equal(f.fields[3].textContent, '<img src=x onerror=alert(1)>');
  assert.equal(f.ids['profile-name'].textContent, 'Alex Student');
  assert.equal(f.ids['profile-avatar'].textContent, 'AS');
  assert.equal(f.ids['profile-editor'].hidden, true);
  // A fresh page reads the saved account data.
  f = fixture(f.calls[0].unsafeMetadata);
  assert.equal(f.fields[0].textContent, 'New School');
  f.ids['profile-edit'].click();
  f.controls.school.value = 'Cancelled';
  f.ids['profile-cancel'].click();
  f.ids['profile-edit'].click();
  assert.equal(f.controls.school.value, 'New School');
  f.clerk.user.update = async () => { throw Error('Offline'); };
  f.controls.school.value = 'Unsaved';
  await submit(f);
  assert.equal(f.fields[0].textContent, 'New School');
  assert.equal(f.ids['profile-editor'].hidden, false);
  assert.equal(f.ids['profile-save-status'].textContent, 'Offline');
  assert.equal(f.ids['profile-save'].disabled, false);
  f.clerk.user.id = 'user_other';
  await submit(f);
  assert.match(f.ids['profile-save-status'].textContent, /sign-in changed/);
  assert.equal(f.calls.length, 0, 'An account switch must not save to another user');
  f = fixture();
  assert.equal(f.fields[0].textContent, 'Not added yet');
  assert.equal(f.ids['profile-name'].textContent, 'Account Name');
  console.log('Profile checks passed: account persistence, metadata preservation, cancel, safe text, failures, and account switches.');
})().catch(error => { console.error(error); process.exitCode = 1; });
