(() => {
  const status = document.getElementById('profile-status');
  const signedIn = document.getElementById('profile-signed-in');
  const signedOut = document.getElementById('profile-signed-out');
  const retry = document.getElementById('profile-retry');
  let revision = 0;
  async function refresh() {
    const current = ++revision;
    signedIn.hidden = true; signedOut.hidden = true; retry.hidden = true;
    status.textContent = 'Verifying your Clerk sign-in…';
    try {
      const account = await window.DegreePathAccount.verify();
      if (current !== revision) return;
      signedIn.hidden = !account.signedIn; signedOut.hidden = account.signedIn;
      status.textContent = account.signedIn ? 'Your Clerk session has been verified.' : 'You are not signed in.';
      if (account.signedIn) {
        document.getElementById('profile-name').textContent = account.user.fullName || account.user.firstName || account.user.username || 'Your account';
        document.getElementById('profile-email').textContent = account.user.primaryEmailAddress?.emailAddress || '';
      }
    } catch (error) {
      if (current !== revision) return;
      status.textContent = error.message; retry.hidden = false; signedOut.hidden = false;
    }
  }
  document.getElementById('profile-sign-in').addEventListener('click', async event => {
    event.currentTarget.disabled = true;
    try { const clerk = await window.DegreePathAccount.load(); clerk.openSignIn({ forceRedirectUrl: location.href, signUpForceRedirectUrl: location.href }); }
    catch (error) { status.textContent = error.message; }
    finally { event.target.disabled = false; }
  });
  document.getElementById('profile-sign-out').addEventListener('click', async event => {
    event.currentTarget.disabled = true;
    try { const clerk = await window.DegreePathAccount.load(); await clerk.signOut(); await refresh(); }
    catch (error) { status.textContent = error.message; }
    finally { event.target.disabled = false; }
  });
  retry.addEventListener('click', refresh);
  window.addEventListener('degree-path-account-change', refresh);
  void refresh();
})();
