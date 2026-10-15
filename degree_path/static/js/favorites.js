(() => {
  let clerkPromise;
  let favorites = [];
  const list = document.getElementById('saved-majors-list');
  const notice = document.createElement('p');
  notice.className = 'favorites-notice';
  notice.setAttribute('role', 'status');
  notice.setAttribute('aria-live', 'polite');
  const gate = document.createElement('div');
  gate.className = 'favorites-account';
  gate.hidden = true;
  const explanation = document.createElement('p');
  explanation.textContent = 'Sign in or create an account to save majors and view your favorites.';
  const signIn = document.createElement('button');
  signIn.type = 'button';
  signIn.className = 'primary-link';
  signIn.textContent = 'Sign in / Create account';
  gate.append(explanation, signIn);
  (list || document.querySelector('.page-workspace')).prepend(gate, notice);

  function loadScript(src, key) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      const timer = setTimeout(() => { script.remove(); reject(new Error('Sign-in loading timed out. Try again.')); }, 20000);
      script.src = src;
      script.async = true;
      script.crossOrigin = 'anonymous';
      if (key) script.setAttribute('data-clerk-publishable-key', key);
      script.onload = () => { clearTimeout(timer); resolve(); };
      script.onerror = () => { clearTimeout(timer); script.remove(); reject(new Error('Sign-in is unavailable. Try again shortly.')); };
      document.head.append(script);
    });
  }

  function clerk() {
    if (!clerkPromise) clerkPromise = (async () => {
      const key = window.CLERK_PUBLISHABLE_KEY;
      const decoded = atob(key.split('_')[2]);
      const domain = decoded.slice(0, -1);
      if (!decoded.endsWith('$') || !/^[a-z0-9]+(?:[.-][a-z0-9]+)+$/i.test(domain)) throw new Error('Sign-in configuration is unavailable.');
      if (!window.Clerk) {
        await loadScript(`https://${domain}/npm/@clerk/ui@1/dist/ui.browser.js`);
        await loadScript(`https://${domain}/npm/@clerk/clerk-js@6/dist/clerk.browser.js`, key);
      }
      // Read the shared palette so sign-in dialogs match every application page.
      // https://clerk.com/docs/js-frontend/guides/customizing-clerk/appearance-prop/variables
      const theme = getComputedStyle(document.documentElement);
      const color = name => theme.getPropertyValue(name).trim();
      await window.Clerk.load({
        ui: { ClerkUI: window.__internal_ClerkUICtor },
        appearance: {
          variables: {
            colorPrimary: color('--primary'),
            colorPrimaryForeground: color('--on-primary'),
            colorBackground: color('--surface'),
            colorForeground: color('--text'),
            colorMuted: color('--surface-raised'),
            colorMutedForeground: color('--muted'),
            colorInput: color('--background'),
            colorInputForeground: color('--text'),
            colorNeutral: color('--text'),
            colorBorder: color('--border'),
            colorRing: color('--accent'),
            borderRadius: '0.75rem',
            fontFamily: theme.fontFamily,
          },
        },
      });
      return window.Clerk;
    })().catch(error => { clerkPromise = undefined; throw error; });
    return clerkPromise;
  }

  async function api(path, body) {
    const auth = await clerk();
    const token = await auth.session?.getToken();
    if (!token) { gate.hidden = false; throw new Error('Sign in or create an account to save majors.'); }
    const response = await fetch(path, {
      method: body ? 'POST' : 'GET',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json',
        'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content },
      ...(body ? { body: JSON.stringify(body) } : {})
    });
    const data = await response.json();
    if (!response.ok) { if (response.status === 401) gate.hidden = false; throw new Error(data.error || 'Could not update saved majors. Try again.'); }
    gate.hidden = true;
    return data;
  }

  function render() {
    if (list) {
      // Preserve the account prompt and status nodes.
      list.querySelectorAll('.saved-major-row, .saved-majors-empty').forEach(node => node.remove());
      if (!favorites.length) {
        const empty = document.createElement('p');
        empty.className = 'saved-majors-empty';
        empty.textContent = 'No saved majors yet. Choose Save major while exploring.';
        list.append(empty);
      }
      favorites.forEach(major => {
        const row = document.createElement('div');
        row.className = 'saved-major-row';
        const link = document.createElement('a');
        link.href = `/explore?cipcode=${major.cipcode}`;
        link.textContent = major.name;
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'save-major-button';
        remove.dataset.saveMajor = major.cipcode;
        remove.setAttribute('aria-label', `Remove ${major.name} from saved majors`);
        row.append(link, remove);
        list.append(row);
      });
    }
    document.querySelectorAll('[data-save-major]').forEach(button => {
      const saved = favorites.some(major => String(major.cipcode) === button.dataset.saveMajor);
      button.setAttribute('aria-pressed', String(saved));
      button.textContent = list ? 'Remove' : saved ? '★ Major saved' : '☆ Save major';
    });
  }

  signIn.addEventListener('click', async () => {
    signIn.disabled = true;
    try {
      const auth = await clerk();
      if (auth.session?.status === 'active') { await refresh(); return; }
      auth.openSignUp({ forceRedirectUrl: location.href, signInForceRedirectUrl: location.href });
    } catch (error) { notice.textContent = error.message; }
    finally { signIn.disabled = false; }
  });

  async function refresh() {
    notice.textContent = 'Loading saved majors…';
    try { favorites = (await api('/api/saved-majors')).majors; render(); notice.textContent = ''; return true; }
    catch (error) { notice.textContent = error.message; return false; }
  }

  document.addEventListener('click', async event => {
    const button = event.target.closest('[data-save-major]');
    if (!button || button.disabled) return;
    button.disabled = true;
    const cipcode = button.dataset.saveMajor;
    try {
      // Read current account state before changing it, including after sign-in.
      const current = (await api('/api/saved-majors')).majors;
      const saved = !current.some(major => String(major.cipcode) === cipcode);
      await api(`/api/saved-majors/${cipcode}`, { saved });
      if (await refresh()) notice.textContent = saved ? 'Major saved to your account.' : 'Major removed from your saved majors.';
    } catch (error) { notice.textContent = error.message; gate.scrollIntoView({ block: 'nearest' }); }
    finally { button.disabled = false; }
  });

  // Guests can browse immediately; their first save opens the account prompt.
  if (list || document.cookie.split(';').some(cookie => cookie.trim().startsWith('__session='))) refresh();
})();
