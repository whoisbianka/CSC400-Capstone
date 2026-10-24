// Explicitly save/restore this tab's program search without changing account preferences.
(() => {
  const form = document.getElementById('degree-filter-form');
  if (!form) return;
  const status = document.querySelector('[data-explore-preferences-status]');
  const account = document.getElementById('account-navigation');
  const key = `degree-path:explore:programs:${account.dataset.userId || 'guest'}`;
  document.querySelector('[data-save-explore-preferences]').addEventListener('click', () => {
    if (!form.reportValidity()) return;
    try {
      const params = new URLSearchParams(new FormData(form));
      params.set('degrees', [...form.querySelectorAll('.degree-choice:checked')].map(input => input.value).join(','));
      sessionStorage.setItem(key, params.toString());
      status.textContent = 'Preferences saved in this browser tab.';
    } catch {
      status.textContent = 'This browser could not save your preferences. Your current search is unchanged.';
    }
  });
  document.querySelector('[data-restore-explore-preferences]').addEventListener('click', () => {
    try {
      const saved = sessionStorage.getItem(key);
      if (!saved) { status.textContent = 'Save preferences first.'; return; }
      const params = new URLSearchParams(saved);
      params.set('view', 'programs');
      params.delete('page');
      window.location.assign(`${form.action.split('?')[0]}?${params.toString()}`);
    } catch {
      status.textContent = 'This browser could not restore your preferences.';
    }
  });
})();
