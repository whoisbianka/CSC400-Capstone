(() => {
  const status = document.getElementById('auth-status');
  const start = document.getElementById('auth-start');
  const retry = document.getElementById('auth-retry');
  const destination = new URL(document.getElementById('start-choice').dataset.destination, window.location.origin).href;
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
      script.onload = () => {
        window.clearTimeout(timeout);
        resolve();
      };
      script.onerror = () => {
        window.clearTimeout(timeout);
        script.remove();
        reject(new Error('Authentication could not load'));
      };
      document.head.appendChild(script);
    });
  }


  async function initialize() {
    start.disabled = true;
    retry.hidden = true;
    status.hidden = false;
    status.textContent = 'Loading sign-in…';
    try {
      const key = window.CLERK_PUBLISHABLE_KEY;
      if (!key || !/^pk_(test|live)_[A-Za-z0-9+/=]+$/.test(key)) throw new Error('Missing key');
      const decoded = atob(key.split('_')[2]);
      const domain = decoded.slice(0, -1);
      if (!decoded.endsWith('$') || !/^[a-z0-9]+(?:[.-][a-z0-9]+)+$/i.test(domain)) throw new Error('Invalid domain');
      if (!window.Clerk) {
        await loadScript(`https://${domain}/npm/@clerk/ui@1/dist/ui.browser.js`);
        await loadScript(`https://${domain}/npm/@clerk/clerk-js@6/dist/clerk.browser.js`, key);
      }
      const clerk = window.Clerk;
      await clerk.load({
        ui: { ClerkUI: window.__internal_ClerkUICtor },
        signInFallbackRedirectUrl: destination,
        signUpFallbackRedirectUrl: destination
      });
      if (clerk.session?.status === 'active') {
        window.location.assign(destination);
        return;
      }
      clerk.openSignUp({
        forceRedirectUrl: destination, signInForceRedirectUrl: destination,
        appearance: {
          elements: {
            modalBackdrop: { display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' },
            modalContent: { margin: 'auto', maxWidth: '100%' }
          }
        }
      });
      start.disabled = false;
      status.hidden = true;
    } catch {
      status.textContent = 'Sign-in is unavailable right now. Try again or continue without logging in.';
      start.disabled = false;
      retry.hidden = false;
    }
  }
  start.addEventListener('click', initialize);
  retry.addEventListener('click', initialize);
})();
