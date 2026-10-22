/* Saved majors stay account-owned; comparison is a local selection of real programs. */
(() => {
  if (!document.getElementById('saved-program-groups')) return;
  const byId = id => document.getElementById(id);
  const degrees = { 1: 'Undergraduate certificate', 2: 'Associate degree', 3: 'Bachelor’s degree',
    4: 'Post-baccalaureate certificate', 5: 'Master’s degree', 6: 'Doctoral degree',
    7: 'First professional degree', 8: 'Graduate certificate' };
  let groups = [];
  let selected = [];
  let api;
  let loadingMore = new Set();
  const money = value => Number.isFinite(value) ? new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value) : 'Not reported';
  const degree = p => degrees[p.credlev] || 'Degree level not reported';
  const location = p => [p.city, p.state].filter(Boolean).join(', ') || 'Location not reported';
  const range = (p, key) => Number.isFinite(p[key + '25']) && Number.isFinite(p[key + '75'])
    && p[key + '25'] > 0 && p[key + '25'] <= p[key + '75']
    ? `${p[key + '25']}–${p[key + '75']}` : 'Not reported';
  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }
  function link(text, href, className) {
    const element = node('a', className, text);
    element.href = href;
    return element;
  }
  function announce(text) {
    const notice = document.querySelector('#saved-majors-list .favorites-notice');
    if (notice) notice.textContent = text;
  }
  function card(program) {
    const active = selected.some(p => p.program_id === program.program_id);
    const article = node('article', 'saved-program-card');
    article.dataset.selected = String(active);
    const top = node('div', 'saved-card-top');
    top.append(node('span', 'saved-card-kicker', 'SAVED MAJOR'), node('span', 'saved-card-degree', degree(program)));
    const title = node('h4');
    title.append(link(program.major, `/programs/${program.program_id}`));
    const college = node('p', 'saved-card-college', program.college);
    college.append(node('span', 'saved-card-location', location(program)));
    const cost = node('div', 'saved-card-cost');
    cost.append(node('span', 'saved-card-label', 'Yearly cost after aid'));
    const price = node('div', 'saved-card-price', money(program.npt4));
    if (Number.isFinite(program.npt4)) price.append(node('small', '', ' / year'));
    cost.append(price);
    const earnings = node('p', 'saved-card-earnings', 'Median annual earnings ');
    earnings.append(node('strong', '', money(program.earnings)));
    const controls = node('div', 'saved-card-controls');
    const label = node('label', 'saved-card-check');
    const input = node('input');
    input.type = 'checkbox';
    input.checked = active;
    input.disabled = !active && selected.length === 3;
    input.dataset.compareProgram = program.program_id;
    input.setAttribute('aria-label', `Compare ${program.major} at ${program.college}, ${degree(program)}`);
    label.append(input, node('span', '', active ? 'Added to comparison' : 'Add to compare'));
    controls.append(label, link('Details →', `/programs/${program.program_id}`));
    article.append(top, title, college, cost, earnings, controls);
    return article;
  }
  function renderGroups() {
    const container = byId('saved-program-groups');
    container.replaceChildren();
    groups.forEach(group => {
      const section = node('section', 'saved-major-group');
      const heading = node('div', 'saved-group-heading');
      const title = node('h3', '', group.name);
      title.id = `saved-major-${group.cipcode}`;
      section.setAttribute('aria-labelledby', title.id);
      const actions = node('div', 'saved-group-actions');
      const remove = node('button', 'save-major-button', 'Remove major');
      remove.type = 'button';
      remove.dataset.saveMajor = group.cipcode;
      remove.setAttribute('aria-label', `Remove ${group.name} from saved majors`);
      actions.append(link('All colleges →', `/explore?cipcode=${group.cipcode}`), remove);
      heading.append(title, actions);
      section.append(heading);
      if (!group.programs.length) {
        section.append(node('p', 'saved-context', 'No college programs are currently available for this saved major.'));
      } else {
        const grid = node('div', 'saved-program-grid');
        group.programs.forEach(program => grid.append(card(program)));
        section.append(grid);
      }
      if (group.has_next) {
        const more = node('button', 'secondary-button saved-load-more', loadingMore.has(group.cipcode) ? 'Loading…' : 'Show more colleges');
        more.type = 'button';
        more.dataset.moreMajor = group.cipcode;
        more.disabled = loadingMore.has(group.cipcode);
        section.append(more);
      }
      container.append(section);
    });
  }
  const rows = [
    { section: 'Cost & value' },
    { label: 'Yearly cost after aid', hint: 'College-wide average · lower is better', key: 'npt4', best: 'min' },
    { label: 'In-state tuition & fees', hint: 'Before aid · lower is better', key: 'tuitionfee_in', best: 'min' },
    { label: 'Out-of-state tuition & fees', hint: 'Before aid · lower is better', key: 'tuitionfee_out', best: 'min' },
    { label: 'Cost at your income level', hint: 'Household income $48,001–75,000', key: 'npt43', best: 'min' },
    { label: 'Median annual earnings', hint: '4 years after completion · higher is better', key: 'earnings', best: 'max' },
    { section: 'College & admissions' },
    { label: 'Location', value: location },
    { label: 'Degree level', value: degree },
    { label: 'Acceptance rate', hint: 'College-wide · no advantage assigned', value: p => Number.isFinite(p.adm_rate) ? `${(p.adm_rate * 100).toFixed(1)}%` : 'Not reported' },
    ...[['satmt', 'SAT Math'], ['satvr', 'SAT Reading'], ['actmt', 'ACT Math'], ['acten', 'ACT English']].map(([key, label]) => ({ label, hint: 'Middle 50% of reported scores', value: p => range(p, key) })),
  ];
  function renderComparison() {
    const hasSaved = groups.length > 0;
    const enough = selected.length >= 2;
    byId('saved-comparison').hidden = !hasSaved;
    byId('saved-comparison-results').hidden = !enough;
    byId('saved-comparison-prompt').hidden = enough;
    byId('saved-differences').disabled = !enough;
    byId('saved-selection-count').textContent = `${selected.length} of 3 programs selected`;
    const head = byId('saved-comparison-head');
    const body = byId('saved-comparison-body');
    head.replaceChildren(); body.replaceChildren();
    if (!enough) return;
    const header = node('tr');
    const corner = node('th', 'saved-corner', 'What matters to you');
    corner.scope = 'col';
    header.append(corner);
    selected.forEach(p => {
      const cell = node('th'); cell.scope = 'col';
      const top = node('div', 'saved-column-top');
      const remove = node('button', 'saved-comparison-remove', '×');
      remove.type = 'button'; remove.dataset.removeComparison = p.program_id;
      remove.setAttribute('aria-label', `Remove ${p.major} at ${p.college} from comparison`);
      top.append(node('span', 'saved-card-kicker', 'PROGRAM'), remove);
      cell.append(top, link(p.major, `/programs/${p.program_id}`, 'saved-column-major'),
        node('span', 'saved-column-college', p.college), node('span', 'saved-column-degree', degree(p)));
      header.append(cell);
    });
    head.append(header);
    const differences = byId('saved-differences').checked;
    let pendingSection;
    let rendered = 0;
    rows.forEach(row => {
      if (row.section) { pendingSection = row.section; return; }
      const values = selected.map(p => row.value ? row.value(p) : p[row.key]);
      if (differences && new Set(values).size <= 1) return;
      if (pendingSection) {
        const section = node('tr', 'saved-table-section');
        const title = node('th', '', pendingSection);
        title.colSpan = selected.length + 1;
        title.scope = 'colgroup';
        section.append(title); body.append(section); pendingSection = null;
      }
      const tr = node('tr');
      const label = node('th', '', row.label); label.scope = 'row';
      if (row.hint) label.append(node('span', 'saved-table-hint', row.hint));
      tr.append(label);
      // Compare only complete numeric rows. An unavailable amount is never a loss.
      const comparable = row.best && values.every(Number.isFinite) && new Set(values).size > 1;
      const best = comparable ? (row.best === 'min' ? Math.min(...values) : Math.max(...values)) : null;
      values.forEach(value => {
        const cell = node('td');
        cell.append(node('span', row.best ? 'saved-table-value' : 'saved-table-text', row.best ? money(value) : value));
        if (comparable) {
          const winner = value === best;
          // Tied best values remain neutral; uniquely best values are green.
          const tiedBest = winner && values.filter(v => v === best).length > 1;
          if (!tiedBest) {
            cell.className = winner ? 'saved-cell-best' : 'saved-cell-worse';
            const other = values.filter(v => v !== best);
            const delta = winner ? Math.min(...other.map(v => Math.abs(v - best))) : Math.abs(value - best);
            const direction = row.best === 'min' ? (winner ? 'less' : 'more') : (winner ? 'more' : 'less');
            cell.append(node('span', 'saved-table-delta', `${winner ? '✓' : '↓'} ${money(delta)} ${direction} / year${selected.length === 3 ? (winner ? ' than next closest' : ' than best') : ''}`));
          } else cell.append(node('span', 'saved-table-hint', 'Tied for best'));
        }
        tr.append(cell);
      });
      body.append(tr); rendered++;
    });
    if (!rendered) {
      const tr = node('tr'); const cell = node('td', '', 'No differences in the reported information.');
      cell.colSpan = selected.length + 1; tr.append(cell); body.append(tr);
    }
  }
  function render() {
    byId('saved-library').hidden = groups.length === 0;
    byId('saved-empty').hidden = groups.length !== 0;
    byId('saved-major-count').textContent = `${groups.length} saved`;
    const canCompare = groups.flatMap(group => group.programs).length >= 2;
    byId('saved-open-comparison').hidden = !canCompare;
    byId('saved-open-help').hidden = !canCompare;
    renderGroups(); renderComparison();
  }
  byId('saved-open-comparison').addEventListener('click', () => {
    if (selected.length < 2) {
      const examples = groups.filter(group => group.programs.length).map(group => group.programs[0]);
      const all = [...examples, ...groups.flatMap(group => group.programs)];
      for (const program of all) {
        if (!selected.some(p => p.program_id === program.program_id)) selected.push(program);
        if (selected.length >= 2) break;
      }
      render();
    }
    if (selected.length < 2) return;
    byId('saved-comparison').scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' });
    announce('Comparison opened. Change the selected programs using the card checkboxes.');
  });
  byId('saved-program-groups').addEventListener('change', event => {
    const input = event.target.closest('[data-compare-program]');
    if (!input) return;
    const id = Number(input.dataset.compareProgram);
    if (input.checked && selected.length < 3) {
      const program = groups.flatMap(group => group.programs).find(p => p.program_id === id);
      if (program && !selected.some(p => p.program_id === id)) selected.push(program);
    } else selected = selected.filter(p => p.program_id !== id);
    render();
    byId('saved-program-groups').querySelector(`[data-compare-program="${id}"]`)?.focus();
    announce(selected.length === 3 ? '3 programs selected. Uncheck a program to compare another.' : `${selected.length} programs selected for comparison.`);
  });
  byId('saved-program-groups').addEventListener('click', async event => {
    const button = event.target.closest('[data-more-major]');
    if (!button || button.disabled) return;
    const cipcode = Number(button.dataset.moreMajor);
    const group = groups.find(g => g.cipcode === cipcode);
    if (!group || loadingMore.has(cipcode)) return;
    loadingMore.add(cipcode); button.disabled = true; button.textContent = 'Loading…';
    try {
      const next = await api(`/api/saved-majors/${cipcode}/programs?page=${group.page + 1}`);
      // A removal or refresh during the request must not restore stale cards.
      if (!groups.includes(group)) return;
      const ids = new Set(group.programs.map(p => p.program_id));
      group.programs.push(...next.programs.filter(p => !ids.has(p.program_id)));
      group.page = next.page; group.has_next = next.has_next;
      render();
      announce(`More college programs loaded for ${group.name}.`);
    } catch (error) { announce(error.message); }
    finally {
      loadingMore.delete(cipcode);
      const current = byId('saved-program-groups').querySelector(`[data-more-major="${cipcode}"]`);
      if (current) { current.disabled = false; current.textContent = 'Show more colleges'; }
    }
  });
  byId('saved-comparison-head').addEventListener('click', event => {
    const button = event.target.closest('[data-remove-comparison]');
    if (!button) return;
    const id = Number(button.dataset.removeComparison);
    selected = selected.filter(p => p.program_id !== id);
    render();
    byId('saved-program-groups').querySelector(`[data-compare-program="${id}"]`)?.focus();
    announce('Program removed from comparison. Your saved majors are unchanged.');
  });
  byId('saved-differences').addEventListener('change', renderComparison);
  window.SavedMajors = {
    reset() {
      groups = []; selected = [];
      ['saved-library', 'saved-empty', 'saved-comparison', 'saved-open-comparison', 'saved-open-help'].forEach(id => { byId(id).hidden = true; });
      byId('saved-program-groups').replaceChildren();
      byId('saved-comparison-head').replaceChildren(); byId('saved-comparison-body').replaceChildren();
      byId('saved-account-status').textContent = 'Sign in to view your saved majors.';
    },
    async refresh(request, favorites) {
      api = request;
      const data = favorites.length ? await api('/api/saved-majors/programs') : { majors: [] };
      groups = data.majors;
      const available = new Map(groups.flatMap(g => g.programs).map(p => [p.program_id, p]));
      const saved = new Set(groups.map(g => g.cipcode));
      selected = selected.filter(p => saved.has(p.cipcode)).map(p => available.get(p.program_id) || p);
      // Keep already-selected later pages visible after removing another major.
      selected.forEach(p => { const group = groups.find(g => g.cipcode === p.cipcode); if (!group.programs.some(item => item.program_id === p.program_id)) group.programs.push(p); });
      render();
    },
  };
})();
