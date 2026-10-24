(() => {
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
  // Account prompts belong on Saved Majors; catalog stars open a modal.
  if (list) list.prepend(gate, notice);

  const loginDialog = document.createElement('dialog');
  loginDialog.className = 'favorites-login-dialog';
  loginDialog.setAttribute('aria-labelledby', 'favorites-login-title');
  loginDialog.setAttribute('aria-describedby', 'favorites-login-message');
  const loginTitle = document.createElement('h2');
  loginTitle.id = 'favorites-login-title';
  loginTitle.textContent = 'Sign in to save';
  const loginMessage = document.createElement('p');
  loginMessage.id = 'favorites-login-message';
  loginMessage.textContent = 'Sign in or create an account to save this major.';
  const loginStatus = document.createElement('p');
  loginStatus.className = 'favorites-notice';
  loginStatus.setAttribute('role', 'status');
  const loginActions = document.createElement('div');
  loginActions.className = 'favorites-login-actions';
  const dismissLogin = document.createElement('button');
  dismissLogin.type = 'button';
  dismissLogin.className = 'secondary-button';
  dismissLogin.textContent = 'Cancel';
  const confirmLogin = document.createElement('button');
  confirmLogin.type = 'button';
  confirmLogin.className = 'primary-link';
  confirmLogin.textContent = 'Sign in';
  loginActions.append(dismissLogin, confirmLogin);
  loginDialog.append(loginTitle, loginMessage, loginStatus, loginActions);
  document.body.append(loginDialog);
  dismissLogin.addEventListener('click', () => loginDialog.close());
  confirmLogin.addEventListener('click', async () => {
    confirmLogin.disabled = true;
    loginStatus.textContent = '';
    try {
      const auth = await clerk();
      loginDialog.close();
      openSignIn(auth);
    } catch (error) {
      loginStatus.textContent = error.message;
      if (!loginDialog.open) loginDialog.showModal();
    } finally { confirmLogin.disabled = false; }
  });

  function showSignInPrompt(kind = 'major') {
    loginMessage.textContent = `Sign in or create an account to save this ${kind}.`;
    loginStatus.textContent = '';
    if (!loginDialog.open) loginDialog.showModal();
  }

  // Use prototype1's verified Flask session and existing Clerk sign-in flow.
  async function clerk() {
    const userId = document.getElementById('account-navigation').dataset.userId;
    return {
      session: userId ? { status: 'active' } : null,
      openSignIn: () => document.getElementById('saved-major-signin').click(),
    };
  }
  function openSignIn(auth) { auth.openSignIn(); }

  function accountRequired() {
    gate.hidden = false;
    const error = new Error('Sign in or create an account to save majors.');
    error.requiresSignIn = true;
    return error;
  }

  async function api(path, body) {
    const auth = await clerk();
    if (!auth.session) throw accountRequired();
    const userId = document.getElementById('account-navigation').dataset.userId;
    const cipcode = path.split('/')[3];
    if (body) body = { cipcode: Number(cipcode), favorite: body.saved };
    const isPrograms = path.endsWith('/programs') || path.includes('/programs?');
    const response = await fetch(isPrograms ? path : '/api/favorites', {
      method: body ? 'POST' : 'GET',
      headers: { 'X-App-User-ID': userId, 'Content-Type': 'application/json',
        'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content },
      ...(body ? { body: JSON.stringify(body) } : {})
    });
    const data = await response.json();
    if (response.status === 401) throw accountRequired();
    if (!response.ok) throw new Error(data.error || 'Could not update saved majors. Try again.');
    gate.hidden = true;
    if (data.favorites) data.majors = data.favorites.map(major => ({ ...major, name: major.major }));
    return data;
  }

  function render() {
    if (list && !window.SavedMajors) {
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
      const cardStar = button.closest('.program-card') !== null;
      button.textContent = list ? 'Remove' : cardStar ? (saved ? '★' : '☆') : saved ? '★ Major saved' : '☆ Save major';
      if (cardStar) {
        const label = saved ? 'Remove major from saved majors' : 'Save major';
        button.setAttribute('aria-label', label);
        button.title = label;
      }
    });
  }

  signIn.addEventListener('click', async () => {
    signIn.disabled = true;
    try {
      const auth = await clerk();
      if (auth.session?.status === 'active') { await refresh(); return; }
      openSignIn(auth);
    } catch (error) { notice.textContent = error.message; }
    finally { signIn.disabled = false; }
  });

  async function refresh() {
    notice.textContent = 'Loading saved majors…';
    if (list) list.setAttribute('aria-busy', 'true');
    try {
      favorites = (await api('/api/saved-majors')).majors;
      if (list && window.SavedMajors) await window.SavedMajors.refresh(api, favorites);
      render(); notice.textContent = ''; return true;
    }
    catch (error) { notice.textContent = error.message; return false; }
    finally { if (list) list.setAttribute('aria-busy', 'false'); }
  }

  document.addEventListener('click', async event => {
    const guestSave = event.target.closest('[data-save-requires-signin]');
    if (guestSave && !guestSave.disabled) {
      event.preventDefault();
      showSignInPrompt(guestSave.dataset.saveRequiresSignin === 'program' ? 'program' : 'major');
      return;
    }
    const button = event.target.closest('[data-save-major]');
    if (!button || button.disabled) return;
    if (!document.getElementById('account-navigation').dataset.userId) {
      event.preventDefault();
      showSignInPrompt('major');
      return;
    }
    button.disabled = true;
    if (!list) {
      // Keep feedback beside the clicked star instead of above the catalog.
      (button.closest('.program-card-content') || button.parentElement).append(notice);
      notice.textContent = '';
    }
    const cipcode = button.dataset.saveMajor;
    const majorName = button.dataset.majorName || document.getElementById('page-title')?.textContent || 'This major';
    try {
      // Read current account state before changing it, including after sign-in.
      const current = (await api('/api/saved-majors')).majors;
      const saved = !current.some(major => String(major.cipcode) === cipcode);
      await api(`/api/saved-majors/${cipcode}`, { saved });
      if (await refresh()) {
        notice.textContent = saved ? 'Major saved to your account.' : 'Major removed from your saved majors.';
        if (saved) {
          if (window.MajorSaveFeedback) notice.textContent = '';
          const confirmed = favorites.find(major => String(major.cipcode) === cipcode);
          window.MajorSaveFeedback?.show({
            majorName: confirmed?.name || majorName,
            button: button.isConnected ? button : document.querySelector(`[data-save-major="${cipcode}"]`),
            onUndo: async () => {
              try {
                await api(`/api/saved-majors/${cipcode}`, { saved: false });
                // The write succeeded even if reloading a comparison later fails.
                favorites = favorites.filter(major => String(major.cipcode) !== cipcode);
                render();
                await refresh();
              } catch (error) {
                if (error.requiresSignIn) showSignInPrompt('major');
                throw error;
              }
            },
          });
        }
      }
    } catch (error) {
      if (error.requiresSignIn) {
        notice.textContent = '';
        showSignInPrompt('major');
      } else {
        notice.textContent = error.message;
      }
    }
    finally { button.disabled = false; }
  });

  // Guests can browse immediately; their first save opens the account prompt.
  if (list || document.getElementById('account-navigation').dataset.userId) refresh();
})();
