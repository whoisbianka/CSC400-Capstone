(() => {
  const group = document.getElementById('state-filter');
  if (!group) return;
  const search = document.getElementById('state-search');
  const any = document.getElementById('state-any');
  const status = document.getElementById('state-selection-status');
  const empty = document.getElementById('state-no-results');
  const rows = [...group.querySelectorAll('[data-state-label]')];
  const choices = rows.map(row => row.querySelector('input[name="state"]'));
  function updateSelection() {
    const count = choices.filter(input => input.checked).length;
    any.checked = count === choices.length && count > 0;
    any.indeterminate = count > 0 && count < choices.length;
    status.textContent = count === 0 ? 'No state restriction' : any.checked ? 'All states and territories selected' : `${count} selected`;
  }
  function filterOptions() {
    const words = search.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    let visible = 0;
    for (const row of rows) {
      row.hidden = !words.every(word => row.dataset.stateLabel.toLocaleLowerCase().includes(word));
      if (!row.hidden) visible++;
    }
    empty.hidden = visible > 0;
  }
  search.addEventListener('input', filterOptions);
  search.addEventListener('keydown', event => {
    // Searching the checklist should not submit the entire Explore form.
    if (event.key === 'Enter') event.preventDefault();
  });
  any.addEventListener('change', () => {
    // Always toggle the complete list, including options hidden by the search.
    choices.forEach(input => { input.checked = any.checked; });
    updateSelection();
  });
  choices.forEach(input => input.addEventListener('change', updateSelection));
  window.addEventListener('pageshow', () => { updateSelection(); filterOptions(); });
  updateSelection();
  filterOptions();
})();
