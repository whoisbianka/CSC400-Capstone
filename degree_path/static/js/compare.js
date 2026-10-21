(() => {
  const page = document.getElementById('compare-page');
  const nav = document.getElementById('account-navigation');
  const choices = document.getElementById('compare-favorites');
  const status = document.getElementById('compare-status');
  const count = document.getElementById('selection-count');
  const clear = document.getElementById('compare-clear');
  const retry = document.getElementById('compare-retry');
  const container = document.getElementById('compare-table-container');
  const table = document.getElementById('compare-table');
  const placeholder = document.getElementById('compare-placeholder');
  const modes = document.querySelectorAll('[data-compare-kind]');
  const maxSelections = 3;
  let kind = 'majors';
  let items = [];
  let metrics = [];
  let selected = [];
  let requestNumber = 0;
  let controller;

  function title(item) {
    return kind === 'majors' ? item.name : `${item.name} · ${item.college} · ${item.credential}`;
  }
  function renderTable() {
    table.tHead.replaceChildren();
    table.tBodies[0].replaceChildren();
    container.hidden = selected.length < 2;
    placeholder.hidden = selected.length >= 2;
    placeholder.textContent = `Choose two or three favorite ${kind} to compare.`;
    count.textContent = `${selected.length} of ${maxSelections} selected`;
    clear.disabled = selected.length === 0;
    if (selected.length < 2) return;
    table.dataset.selections = String(selected.length);
    const records = selected.map(id => items.find(item => item.id === id));
    const header = document.createElement('tr');
    for (const label of ['Statistic', ...records.map(title)]) {
      const th = document.createElement('th');
      th.scope = 'col'; th.textContent = label; header.appendChild(th);
    }
    table.tHead.appendChild(header);
    for (const metric of metrics) {
      const row = document.createElement('tr');
      const heading = document.createElement('th');
      heading.scope = 'row'; heading.textContent = metric.label;
      if (metric.note) {
        const note = document.createElement('small'); note.textContent = metric.note; heading.appendChild(note);
      }
      row.appendChild(heading);
      const values = records.map(item => item[metric.key]);
      const labels = ComparisonValues.highlights(values, metric.direction);
      values.forEach((value, index) => {
        const td = document.createElement('td');
        td.textContent = ComparisonValues.format(value, metric.format);
        if (labels[index]) {
          td.className = 'best-value';
          const badge = document.createElement('span');
          badge.className = 'compare-badge'; badge.textContent = labels[index]; td.appendChild(badge);
        }
        row.appendChild(td);
      });
      table.tBodies[0].appendChild(row);
    }
  }
  function updateChoices() {
    choices.querySelectorAll('input').forEach(input => {
      input.checked = selected.includes(Number(input.value));
      input.disabled = selected.length >= maxSelections && !input.checked;
    });
  }
  function renderChoices() {
    choices.replaceChildren();
    for (const item of items) {
      const label = document.createElement('label'); label.className = 'compare-choice';
      const input = document.createElement('input'); input.type = 'checkbox'; input.value = item.id;
      const text = document.createElement('span');
      const name = document.createElement('strong'); name.textContent = item.name; text.appendChild(name);
      if (kind === 'programs') {
        const subtitle = document.createElement('small'); subtitle.textContent = `${item.college} · ${item.credential}`; text.appendChild(subtitle);
      }
      input.addEventListener('change', () => {
        if (input.checked && selected.length < maxSelections) selected.push(item.id);
        else selected = selected.filter(id => id !== item.id);
        updateChoices(); renderTable();
      });
      label.append(input, text); choices.appendChild(label);
    }
  }
  async function load(nextKind) {
    kind = nextKind; selected = []; items = []; metrics = [];
    const version = ++requestNumber;
    if (controller) controller.abort();
    controller = new AbortController();
    renderTable(); choices.replaceChildren(); retry.hidden = true;
    document.getElementById('favorite-list-title').textContent = `Favorite ${kind}`;
    document.getElementById('comparison-title').textContent = kind === 'majors' ? 'Major comparison' : 'Program comparison';
    modes.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.compareKind === kind)));
    if (!nav.dataset.userId) {
      status.textContent = 'Your favorites appear here after you sign in. Visit Favorites to get started.';
      return;
    }
    status.textContent = 'Loading favorites…';
    choices.setAttribute('aria-busy', 'true');
    try {
      const url = new URL(page.dataset.apiUrl, window.location.origin); url.searchParams.set('kind', kind);
      const response = await fetch(url, {credentials:'same-origin', headers:{'X-App-User-ID':nav.dataset.userId}, signal:controller.signal});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Unable to load comparisons.');
      if (version !== requestNumber) return;
      items = result.items; metrics = result.metrics;
      renderChoices();
      status.textContent = items.length < 2
        ? `Save at least two ${kind} to compare. ${kind === 'programs' ? 'Use Favorite program on a program detail page.' : 'Use Favorite on a chat recommendation.'}`
        : 'Select two or three favorites. Uncheck one to choose another.';
    } catch (error) {
      if (version !== requestNumber || error.name === 'AbortError') return;
      status.textContent = error.message; retry.hidden = false;
    } finally {
      if (version === requestNumber) choices.setAttribute('aria-busy', 'false');
    }
  }
  modes.forEach(button => button.addEventListener('click', () => load(button.dataset.compareKind)));
  clear.addEventListener('click', () => {selected = []; updateChoices(); renderTable();});
  retry.addEventListener('click', () => load(kind));
  load('majors');
})();
