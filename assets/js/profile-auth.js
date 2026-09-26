(() => {
  const status = document.getElementById('auth-status');
  const container = document.getElementById('auth-component');
  const signOut = document.getElementById('auth-sign-out');
  const retry = document.getElementById('auth-retry');
  const profileUrl = new URL('profile.html', window.location.href).href;
  let mounted = null;

  function loadScript(src, key) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      const timeout = window.setTimeout(() => {
        script.remove();
        reject(new Error('Authentication loading timed out'));
      }, 20000);
      script.src = src;
      script.async = true;
      script.crossOrigin = 'anonymous';
      if (key) script.setAttribute('data-clerk-publishable-key', key);
      script.onload = () => { window.clearTimeout(timeout); resolve(); };
      script.onerror = () => {
        window.clearTimeout(timeout);
        script.remove();
        reject(new Error('Authentication could not load'));
      };
      document.head.appendChild(script);
    });
  }

  function showError() {
    status.hidden = false;
    status.textContent = 'We couldn’t load your account. Please try again. You can still explore colleges.';
    retry.hidden = false;
  }

  retry.addEventListener('click', () => window.location.reload());

  async function initialize() {
    const key = window.CLERK_PUBLISHABLE_KEY;
    if (!key) {
      status.textContent = 'Accounts are not available yet. You can still explore colleges without signing in.';
      return;
    }

    try {
      if (!/^pk_(test|live)_[A-Za-z0-9+/=]+$/.test(key)) throw new Error('Invalid publishable key');
      const decoded = atob(key.split('_')[2]);
      const domain = decoded.slice(0, -1);
      if (!decoded.endsWith('$') || !/^[a-z0-9]+(?:[.-][a-z0-9]+)+$/i.test(domain)) {
        throw new Error('Invalid Clerk domain');
      }
      if (!/^https?:$/.test(window.location.protocol)) throw new Error('Serve the site over HTTP');
      await loadScript(`https://${domain}/npm/@clerk/ui@1/dist/ui.browser.js`);
      await loadScript(`https://${domain}/npm/@clerk/clerk-js@6/dist/clerk.browser.js`, key);
      const clerk = window.Clerk;
      await clerk.load({
        ui: { ClerkUI: window.__internal_ClerkUICtor },
        signInFallbackRedirectUrl: profileUrl,
        signUpFallbackRedirectUrl: profileUrl,
      });

      function render() {
        // A pending session still needs Clerk's sign-in UI to complete session tasks.
        const next = clerk.session?.status === 'active' ? 'profile' : 'sign-in';
        if (mounted === next) return;
        if (mounted === 'profile') clerk.unmountUserProfile(container);
        if (mounted === 'sign-in') clerk.unmountSignIn(container);
        container.replaceChildren();
        signOut.hidden = next !== 'profile';
        if (next === 'profile') {
          clerk.mountUserProfile(container, { routing: 'hash' });
        } else {
          clerk.mountSignIn(container, {
            routing: 'hash',
            withSignUp: true,
            forceRedirectUrl: profileUrl,
            signUpForceRedirectUrl: profileUrl,
          });
        }
        mounted = next;
        status.hidden = true;
      }

      signOut.addEventListener('click', async () => {
        signOut.disabled = true;
        try {
          await clerk.signOut({ redirectUrl: profileUrl });
        } catch {
          status.hidden = false;
          status.textContent = 'We couldn’t sign you out. Please try again.';
        } finally {
          signOut.disabled = false;
        }
      });
      render();
      clerk.addListener(() => {
        try { render(); } catch { showError(); }
      });
    } catch {
      showError();
    }
  }

  initialize();
})();
