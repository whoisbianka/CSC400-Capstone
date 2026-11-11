(() => {
  const form = document.getElementById('degree-filter-form') || document.getElementById('major-filter-form');
  if (!form) return;
  const status = document.querySelector('[data-explore-preferences-status]');
  const save = document.querySelector('[data-save-explore-preferences]');
  const restore = document.querySelector('[data-restore-explore-preferences]');
  let busy = false;
  async function run(callback) {
    if (busy) return;
    busy = true; save.disabled = true; restore.disabled = true;
    try { await callback(); }
    catch (error) { status.textContent = error.message || 'Unable to access saved searches. Please retry.'; }
    finally { busy = false; save.disabled = false; restore.disabled = false; }
  }
  save.addEventListener('click', () => run(async () => {
    if (!form.reportValidity()) return;
    status.textContent = 'Saving search…';
    const result = await window.SavedFilterStore.save(new URLSearchParams(new FormData(form)).toString());
    status.textContent = result.duplicate ? 'This search is already saved.' : 'Search saved to your account. Find it in Saved → Saved filters.';
  }));
  restore.addEventListener('click', () => run(async () => {
    status.textContent = 'Loading saved searches…';
    const kind = new FormData(form).get('view') || 'programs';
    const item = (await window.SavedFilterStore.read()).find(row=>row.kind === kind);
    if (!item) { status.textContent = 'No saved searches for this view yet.'; return; }
    window.location.assign(window.SavedFilterStore.url(item));
  }));
})();
