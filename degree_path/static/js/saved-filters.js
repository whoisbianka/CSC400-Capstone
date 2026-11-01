(() => {
  const panel = document.getElementById('saved-filters-panel');
  if (!panel) return;
  const list = document.getElementById('saved-filter-cards');
  const status = document.getElementById('saved-filters-status');
  const count = document.getElementById('saved-filters-tab-count');
  const labels = {q:'Search', major_filter:'Major selection', major_name:'Major', cipcode:'Major code', favorite_major:'Saved major code', degrees:'Degree', school_name:'College', state:'State', city:'City', net_price_max:'Maximum yearly cost after aid', tuition_in_max:'Maximum in-state tuition', tuition_out_max:'Maximum out-of-state tuition', acceptance_min:'Minimum acceptance rate', acceptance_max:'Maximum acceptance rate', sort:'Sort by'};
  const sorts = {school_asc:'School name A–Z', school_desc:'School name Z–A', earnings_desc:'Highest program earnings', net_price_asc:'Lowest cost after aid', tuition_in_asc:'Lowest in-state tuition', tuition_out_asc:'Lowest out-of-state tuition'};
  function node(tag, className, text) {
    const el = document.createElement(tag); el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  }
  function render() {
    try {
      const items = window.SavedFilterStore.read();
      count.textContent = String(items.length); list.replaceChildren();
      status.textContent = items.length ? '' : 'No saved filters yet. Choose filters in Explore, then press Save preferences.';
      for (const item of items) {
        const params = new URLSearchParams(item.params);
        const card = node('article', 'saved-filter-card');
        const title = params.get('q') || params.get('major_name') || params.get('school_name') || [params.get('city'), params.get('state')].filter(Boolean).join(', ') || 'College program filters';
        card.append(node('h3', '', title));
        const facts = node('dl', 'saved-filter-facts');
        for (const [name, value] of params) {
          if (!labels[name]) continue;
          let display = value;
          if (name === 'major_filter') display = {all:'All majors', name:'Specific major', favorites:'My saved majors'}[value] || value;
          if (name === 'degrees') display = value.split(',').map(degree => degree === '2' ? 'Associate degree' : degree === '3' ? 'Bachelor’s degree' : degree).join(', ');
          if (name === 'sort') display = sorts[value] || value;
          if (name.endsWith('_max') && !name.startsWith('acceptance')) display = Number.isFinite(Number(value)) ? new Intl.NumberFormat('en-US', {style:'currency', currency:'USD', maximumFractionDigits:0}).format(Number(value)) : value;
          if (name.startsWith('acceptance')) display += '%';
          const fact = node('div', ''); fact.append(node('dt', '', labels[name]), node('dd', '', display)); facts.append(fact);
        }
        card.append(facts);
        const actions = node('div', 'saved-filter-actions');
        const apply = node('a', 'primary-link', 'Apply filters →');
        apply.href = window.SavedFilterStore.url(item.params, panel.dataset.exploreUrl);
        const remove = node('button', 'secondary-button', 'Remove'); remove.type = 'button';
        remove.setAttribute('aria-label', `Remove saved filters: ${title}`);
        remove.addEventListener('click', () => {
          try {
            window.SavedFilterStore.remove(item.params); render(); status.textContent = 'Saved filters removed.';
            (list.querySelector('button') || document.getElementById('saved-filters-tab')).focus();
          } catch { status.textContent = 'This browser could not remove these filters. Try again.'; }
        });
        actions.append(apply, remove); card.append(actions); list.append(card);
      }
    } catch {
      status.textContent = 'This browser could not load saved filters. Check that browser storage is available and try again.';
      count.textContent = '—';
    }
  }
  window.SavedFilters = {render};
  window.addEventListener('storage', event => { if (event.key === window.SavedFilterStore.key || event.key === null) render(); });
  render();
})();
