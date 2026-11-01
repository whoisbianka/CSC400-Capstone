// Save current form values, including search and sort controls outside the form.
(() => {
  const form = document.getElementById('degree-filter-form');
  if (!form) return;
  const status = document.querySelector('[data-explore-preferences-status]');
  const account = document.getElementById('account-navigation');
  const legacyKey = `degree-path:explore:programs:${account.dataset.userId || 'guest'}`;
  document.querySelector('[data-save-explore-preferences]').addEventListener('click', () => {
    if (!form.reportValidity()) return;
    try {
      const params = new URLSearchParams(new FormData(form));
      params.set('degrees', [...form.querySelectorAll('.degree-choice:checked')].map(input => input.value).join(','));
      const result = window.SavedFilterStore.save(params.toString());
      status.textContent = result.duplicate ? 'These filters are already in Saved filters.' : 'Filters saved. Find them in Saved → Saved filters.';
    } catch (error) {
      status.textContent = error.message.startsWith('You have 50') ? error.message : 'This browser could not save your filters. Your current search is unchanged.';
    }
  });
  document.querySelector('[data-restore-explore-preferences]').addEventListener('click', () => {
    try {
      const latest = window.SavedFilterStore.read()[0];
      const saved = latest?.params || window.sessionStorage.getItem(legacyKey);
      if (!saved) { status.textContent = 'Save preferences first.'; return; }
      window.location.assign(window.SavedFilterStore.url(saved, form.action));
    } catch { status.textContent = 'This browser could not restore your filters.'; }
  });
})();
