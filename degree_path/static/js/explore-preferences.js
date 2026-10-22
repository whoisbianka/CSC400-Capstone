(() => {
  const form = document.getElementById('degree-filter-form') || document.getElementById('major-filter-form');
  if (!form) return;
  form.querySelectorAll('[data-filter-toggle]').forEach(toggle => {
    const input = document.getElementById(toggle.dataset.filterToggle);
    input.classList.add('optional-filter-value');
    const update = () => { input.disabled = !toggle.checked; };
    toggle.addEventListener('change', update);
    update();
  });
  const nav = document.getElementById('account-navigation');
  const save = form.querySelector('[data-save-preferences]');
  const reset = form.querySelector('[data-reset-preferences]');
  const status = form.querySelector('[data-preferences-status]');
  let busy = false;
  async function update(action) {
    if (busy || (action === 'save' && !form.reportValidity())) return;
    if (action === 'reset' && !window.confirm('Reset saved preferences for both Explore tabs? Your chat and favorites will stay.')) return;
    const fields = new FormData(form);
    const filters = {};
    for (const [key, value] of fields) {
      if (['view', 'preferences_applied'].includes(key)) continue;
      (filters[key] ||= []).push(value);
    }
    busy = true; save.disabled = true; reset.disabled = true;
    status.textContent = action === 'save' ? 'Saving preferences…' : 'Resetting preferences…';
    try {
      const response = await fetch('/api/explore/preferences', {
        method: 'POST', credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': nav.dataset.csrf, 'X-App-User-ID': nav.dataset.userId},
        body: JSON.stringify({action, view: fields.get('view'), filters}),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Unable to update preferences.');
      // Applying the returned URL also resets pagination and displays saved values.
      window.location.assign(result.url);
    } catch (error) {
      status.textContent = error.message;
      busy = false; save.disabled = false; reset.disabled = false;
    }
  }
  save.addEventListener('click', () => update('save'));
  reset.addEventListener('click', () => update('reset'));
})();
