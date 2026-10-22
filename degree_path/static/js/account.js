/* One Clerk instance shared by the profile and saved-major controls. */
(() => {
  let pending;
  let previousUser;
  function script(src, key) {
    return new Promise((resolve, reject) => {
      const element = document.createElement('script');
      const timer = setTimeout(() => { element.remove(); reject(new Error('Sign-in took too long to load. Please retry.')); }, 20000);
      element.src = src; element.async = true; element.crossOrigin = 'anonymous';
      if (key) element.setAttribute('data-clerk-publishable-key', key);
      element.onload = () => { clearTimeout(timer); resolve(); };
      element.onerror = () => { clearTimeout(timer); element.remove(); reject(new Error('Sign-in is unavailable. Please retry.')); };
      document.head.append(element);
    });
  }
  async function load() {
    if (!pending) pending = (async () => {
      const key = window.CLERK_PUBLISHABLE_KEY;
      let decoded;
      try { decoded = atob(key.split('_')[2]); } catch (_) { throw new Error('Sign-in configuration is unavailable.'); }
      const domain = decoded.slice(0, -1);
      if (!decoded.endsWith('$') || !/^[a-z0-9]+(?:[.-][a-z0-9]+)+$/i.test(domain)) throw new Error('Sign-in configuration is unavailable.');
      if (!window.Clerk) {
        await script(`https://${domain}/npm/@clerk/ui@1/dist/ui.browser.js`);
        await script(`https://${domain}/npm/@clerk/clerk-js@6/dist/clerk.browser.js`, key);
      }
      const theme = getComputedStyle(document.documentElement);
      const color = name => theme.getPropertyValue(name).trim();
      await window.Clerk.load({ ui: { ClerkUI: window.__internal_ClerkUICtor }, appearance: { variables: {
        colorPrimary: color('--primary'), colorPrimaryForeground: color('--on-primary'),
        colorBackground: color('--surface'), colorForeground: color('--text'),
        colorMuted: color('--surface-raised'), colorMutedForeground: color('--muted'),
        colorInput: color('--background'), colorInputForeground: color('--text'),
        colorBorder: color('--border'), colorRing: color('--accent'), borderRadius: '0.75rem',
      } } });
      previousUser = window.Clerk.session?.user?.id || window.Clerk.user?.id || null;
      window.Clerk.addListener(({ session, user }) => {
        const id = session ? (user?.id || session.user?.id || null) : null;
        if (id === previousUser) return;
        previousUser = id;
        window.dispatchEvent(new CustomEvent('degree-path-account-change', { detail: { signedIn: Boolean(id) } }));
      });
      return window.Clerk;
    })().catch(error => { pending = undefined; throw error; });
    return pending;
  }
  async function verify() {
    const clerk = await load();
    const token = await clerk.session?.getToken();
    if (!token) return { signedIn: false, clerk };
    const response = await fetch('/api/account', { headers: { Authorization: `Bearer ${token}` }, credentials: 'same-origin' });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Could not verify your sign-in.');
    const user = clerk.user || clerk.session?.user;
    if (!user || user.id !== result.clerk_user_id) throw new Error('Your account changed. Reload and sign in again.');
    return { signedIn: true, clerk, user };
  }
  window.DegreePathAccount = { load, verify };
})();
