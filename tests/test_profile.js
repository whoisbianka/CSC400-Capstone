// Run: node tests/test_profile.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
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
  const ids = Object.fromEntries(['profile-account', 'profile-edit', 'profile-editor', 'profile-save', 'profile-cancel', 'profile-save-status', 'profile-name', 'profile-goal', 'profile-avatar', 'profile-interests'].map(id => [id, element()]));
  ids['profile-account'].dataset = {clerkUserId: 'user_expected'};
  ids['profile-editor'].elements = {namedItem: key => controls[key]};
  ids['profile-editor'].reportValidity = () => true;
  global.document = {getElementById: id => ids[id], createElement: () => element()};
  const calls = [];
  const clerk = {session: {}, user: {id: 'user_expected', unsafeMetadata: metadata,
    async update(params) { calls.push(params); this.unsafeMetadata = params.unsafeMetadata; }}};
  mount(clerk, 'Account Name');
  return {ids, controls, calls, clerk};
}
const submit = f => f.ids['profile-editor'].submit({preventDefault() {}});

async function checkDeletion() {
  const ids = Object.fromEntries(['profile-delete', 'profile-delete-dialog', 'profile-delete-cancel', 'profile-delete-confirm', 'profile-delete-status'].map(id => [id, element()]));
  ids['account-navigation'] = element({dataset: {userId: '42', csrf: 'test-csrf'}});
  const [trigger, dialog, cancel, confirm, status] = Object.values(ids);
  dialog.dataset = {deleteUrl: '/api/account'};
  dialog.showModal = () => { dialog.open = true; };
  dialog.close = () => { dialog.open = false; };
  let requests = 0;
  let reloads = 0;
  vm.runInNewContext(fs.readFileSync(require.resolve('../degree_path/static/js/profile.js'), 'utf8'), {
    document: {getElementById: id => ids[id]},
    window: {location: {reload() { reloads++; }}},
    async fetch(path, {method, headers}) {
      assert.equal(path, '/api/account');
      assert.equal(method, 'DELETE');
      assert.equal(headers['X-App-User-ID'], '42');
      assert.equal(headers['X-CSRF-Token'], 'test-csrf');
      return ++requests === 1
        ? {ok: false, json: async () => ({error: 'Please try again.'})}
        : {ok: true, json: async () => ({ok: true})};
    },
  });
  trigger.click();
  assert.equal(dialog.open, true);
  cancel.click();
  assert.equal(requests, 0);
  trigger.click();
  await confirm.click();
  assert.equal(dialog.open, true);
  assert.equal(status.textContent, 'Please try again.');
  assert.equal(confirm.disabled, false);
  await confirm.click();
  assert.equal(requests, 2);
  assert.equal(reloads, 1);
}

(async () => {
  assert.equal(normalize({interests: 42}).interests, '');
  assert.equal(normalize({goal: 'x'.repeat(600)}).goal.length, 500);
  let f = fixture({otherFeature: {keep: true}, pathfinderProfile: {school: 'Example School', major: 'Design', graduation: '2027', interests: 'Design, Design, Tech'}});
  assert.equal(f.ids['profile-interests'].children.length, 2);
  assert.equal(f.ids['profile-edit'].disabled, false);
  f.ids['profile-edit'].click();
  f.controls.interests.value = 'Art';
  f.controls.displayName.value = 'Alex Student';
  f.controls.goal.value = '<img src=x onerror=alert(1)>';
  await submit(f);
  assert.deepEqual(f.calls[0].unsafeMetadata.otherFeature, {keep: true});
  assert.deepEqual(f.calls[0].unsafeMetadata.pathfinderProfile, {displayName: 'Alex Student', interests: 'Art', goal: '<img src=x onerror=alert(1)>'});
  assert.equal(f.ids['profile-goal'].textContent, '<img src=x onerror=alert(1)>');
  assert.equal(f.ids['profile-name'].textContent, 'Alex Student');
  assert.equal(f.ids['profile-avatar'].textContent, 'AS');
  assert.equal(f.ids['profile-editor'].hidden, true);
  // A fresh page reads the saved account data.
  f = fixture(f.calls[0].unsafeMetadata);
  assert.equal(f.ids['profile-interests'].children[0].textContent, 'Art');
  f.ids['profile-edit'].click();
  f.controls.interests.value = 'Cancelled';
  f.ids['profile-cancel'].click();
  f.ids['profile-edit'].click();
  assert.equal(f.controls.interests.value, 'Art');
  f.clerk.user.update = async () => { throw Error('Offline'); };
  f.controls.interests.value = 'Unsaved';
  await submit(f);
  assert.equal(f.ids['profile-interests'].children[0].textContent, 'Art');
  assert.equal(f.ids['profile-editor'].hidden, false);
  assert.equal(f.ids['profile-save-status'].textContent, 'Offline');
  assert.equal(f.ids['profile-save'].disabled, false);
  f.clerk.user.id = 'user_other';
  await submit(f);
  assert.match(f.ids['profile-save-status'].textContent, /sign-in changed/);
  assert.equal(f.calls.length, 0, 'An account switch must not save to another user');
  f = fixture();
  assert.equal(f.ids['profile-goal'].textContent, 'Not added yet');
  assert.equal(f.ids['profile-name'].textContent, 'Account Name');
  await checkDeletion();
  console.log('Profile checks passed: account persistence, cancellation, safe text, account switches, and deletion confirmation and retry.');
})().catch(error => { console.error(error); process.exitCode = 1; });
