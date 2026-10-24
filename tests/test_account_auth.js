// Offline browser-controller checks. Run with: node tests/test_account_auth.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('degree_path/static/js/account-auth.js', 'utf8');

function fixture({userId = '', active = false, pending = {}, failLogout = false, profile = false, profileUser = null} = {}) {
  const calls = [];
  const storage = new Map(Object.entries(pending));
  const element = (dataset = {}) => ({dataset, hidden: true, disabled: false,
    addEventListener(event, fn) { this[event] = fn; }});
  const nav = element({userId, csrf: 'csrf', clerkKey: 'pk_test_' + Buffer.from('example.com$').toString('base64')});
  const button = element({authAction: userId ? 'logout' : 'login'});
  const status = element();
  const retry = element();
  const profileElements = Object.fromEntries(['profile-name','profile-email','profile-name-value','profile-email-value','profile-avatar','profile-identity-status'].map(id => [id, element()]));
  if (profile) profileElements['profile-account'] = element({clerkUserId:'user_expected'});
  const clerk = {
    user: profileUser,
    session: active ? {getToken: async () => 'token'} : null,
    load: async () => calls.push('load'),
    openSignIn: options => { calls.push('modal'); assert.equal(options.forceRedirectUrl, 'https://app.test/favorites'); },
    closeSignIn: () => calls.push('close'),
    addListener: fn => { clerk.listener = fn; return () => {}; },
    signOut: async () => { calls.push('clerk-logout'); if (failLogout) throw Error('offline'); },
  };
  const context = {
    document: {
      getElementById: id => ({'account-navigation':nav,'account-status':status,'account-retry-logout':retry,...profileElements})[id],
      querySelectorAll: () => [button],
    },
    window: {Clerk:clerk, __internal_ClerkUICtor:{}, location:{href:'https://app.test/favorites',reload:()=>calls.push('reload')}},
    sessionStorage: {getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
    atob: s=>Buffer.from(s,'base64').toString(),
    fetch: async (path, options) => {
      calls.push(path);
      assert.equal(options.headers['X-CSRF-Token'], 'csrf');
      assert.equal(options.credentials, 'same-origin');
      if (path === '/api/auth/session') assert.equal(options.headers.Authorization, 'Bearer token');
      return {ok:true,json:async()=>({})};
    },
  };
  vm.runInNewContext(source, context);
  return {calls, storage, button, retry, clerk, status, profileElements};
}
const flush = () => new Promise(resolve=>setImmediate(resolve));
(async () => {
  let f = fixture();
  assert.deepEqual(f.calls, [], 'Guest visits must not load Clerk or open sign-in');
  await f.button.click();
  assert.deepEqual(f.calls, ['load', 'modal']);
  f.clerk.session = {getToken: async () => 'token'};
  f.clerk.listener({session:f.clerk.session});
  await flush();
  assert.deepEqual(f.calls, ['load','modal','/api/auth/session','close','reload']);
  assert.equal(f.storage.has('degree-path-login-pending'), false);

  f = fixture({active:true,pending:{'degree-path-login-pending':'1'}});
  await flush();
  assert.deepEqual(f.calls, ['load','/api/auth/session','close','reload']);

  f = fixture({userId:'42',active:true});
  assert.deepEqual(f.calls, [], 'Signed-in visits must not load Clerk');
  await f.button.click();
  assert.deepEqual(f.calls, ['/logout','load','clerk-logout','reload']);
  assert.equal(f.storage.has('degree-path-logout-pending'), false);

  f = fixture({userId:'42',active:true,failLogout:true});
  await f.button.click();
  assert.equal(f.calls[0], '/logout', 'Flask access must be cleared even if Clerk fails');
  assert.equal(f.calls.at(-1), 'reload');
  assert.equal(f.storage.get('degree-path-logout-pending'), '1');

  f = fixture({pending:{'degree-path-logout-pending':'1'}});
  assert.equal(f.retry.hidden, false);
  await f.retry.click();
  assert.equal(f.retry.hidden, true);
  assert.equal(f.storage.has('degree-path-logout-pending'), false);
  f = fixture({userId:'42', active:true, profile:true, profileUser:{id:'user_expected', fullName:'Test Student', primaryEmailAddress:{emailAddress:'student@example.com'}}});
  await flush();
  assert.equal(f.profileElements['profile-name'].textContent, 'Test Student');
  assert.equal(f.profileElements['profile-email-value'].textContent, 'student@example.com');
  assert.equal(f.profileElements['profile-avatar'].textContent, 'TS');
  assert.deepEqual(f.calls, ['load'], 'Profile loads details without opening a sign-in prompt');
  await f.button.click();
  assert.equal(f.calls.includes('/logout'), true);

  f = fixture({userId:'42', active:true, profile:true, profileUser:{id:'user_other', fullName:'Wrong Account', primaryEmailAddress:{emailAddress:'wrong@example.com'}}});
  await flush();
  assert.equal(f.profileElements['profile-name'].textContent, undefined, 'Never display another Clerk account');
  assert.equal(f.profileElements['profile-email-value'].textContent, 'Unavailable');
  assert.match(f.profileElements['profile-identity-status'].textContent, /sign-in changed/);

  f = fixture({userId:'42', active:true, profile:true, profileUser:{id:'user_expected'}});
  await flush();
  assert.equal(f.profileElements['profile-name-value'].textContent, 'Not provided');
  assert.equal(f.profileElements['profile-email-value'].textContent, 'Not provided');

  f = fixture({profile:true});
  await flush();
  assert.deepEqual(f.calls, [], 'Signed-out profiles must not load Clerk or open sign-in');
  console.log('Account UI checks passed: login/logout, profile identity, account mismatch protection, missing details, and guest visits.');
})().catch(error=>{console.error(error);process.exitCode=1;});
