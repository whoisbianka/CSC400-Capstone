(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const columns = [['college', 'College'], ['state', 'Location'], ['major', 'Major'], ['type', 'College type'], ['format', 'Study format'], ['tuition', 'Annual tuition']];
  let sortKey = 'college', direction = 1, format = '';
  const node = (tag, text) => { const element = document.createElement(tag); element.textContent = text; return element; };
  function render() {
    const term = $('tbl-search').value.trim().toLowerCase();
    const rows = window.programCatalog.getPrograms().filter(p => (!format || p.format === format) && columns.some(([key]) => String(p[key] ?? '').toLowerCase().includes(term)));
    rows.sort((a, b) => {
      if (a[sortKey] == null) return b[sortKey] == null ? 0 : 1;
      if (b[sortKey] == null) return -1;
      return direction * (sortKey === 'tuition' ? a[sortKey] - b[sortKey] : String(a[sortKey]).localeCompare(String(b[sortKey])));
    });
    $('tbl-head').replaceChildren();
    columns.forEach(([key, label]) => {
      const th = node('th', ''); th.scope = 'col';
      th.setAttribute('aria-sort', key === sortKey ? (direction === 1 ? 'ascending' : 'descending') : 'none');
      const button = node('button', label + ' ');
      button.type = 'button';
      const arrow = node('span', key === sortKey ? (direction === 1 ? '▲' : '▼') : '↕');
      arrow.className = 'tbl-arrow'; arrow.setAttribute('aria-hidden', 'true'); button.append(arrow);
      button.addEventListener('click', () => {
        direction = sortKey === key ? -direction : 1; sortKey = key; render();
        $('tbl-head').children[columns.findIndex(([column]) => column === key)].querySelector('button').focus();
      });
      th.append(button); $('tbl-head').append(th);
    });
    $('tbl-body').replaceChildren();
    rows.forEach(program => {
      const tr = node('tr', '');
      columns.forEach(([key]) => {
        const td = node('td', key === 'tuition' ? (program[key] === null ? 'Not available' : '$' + program[key].toLocaleString('en-US')) : program[key] || 'Not available');
        if (key === 'major') {
          const link = node('a', program.major);
          link.href = 'program-details.html#' + encodeURIComponent(JSON.stringify({program, demo: window.programCatalog.isDemo()}));
          td.replaceChildren(link);
        }
        tr.append(td);
      });
      $('tbl-body').append(tr);
    });
    if (!rows.length) {
      const tr = node('tr', ''), td = node('td', 'No results match your search or filters.');
      tr.className = 'tbl-empty'; td.colSpan = columns.length; tr.append(td); $('tbl-body').append(tr);
    }
    $('tbl-count').textContent = `${rows.length} program${rows.length === 1 ? '' : 's'}`;
    $('catalog-note').textContent = window.programCatalog.isDemo() ? 'Demo data only · All colleges, programs, and tuition figures are fictional test fixtures.' : 'Program catalog · Confirm requirements and costs with the college.';
    $('tbl-filters').querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.format === format)));
  }
  function refresh() {
    const formats = [...new Set(window.programCatalog.getPrograms().map(p => p.format).filter(Boolean))].sort();
    if (!formats.includes(format)) format = '';
    $('tbl-filters').replaceChildren();
    ['', ...formats].forEach(value => {
      const button = node('button', value || 'All formats'); button.type = 'button'; button.className = 'tbl-chip'; button.dataset.format = value;
      button.addEventListener('click', () => { format = value; render(); }); $('tbl-filters').append(button);
    });
    render();
  }
  $('tbl-search').addEventListener('input', render);
  window.addEventListener('program-catalog-updated', refresh);
  refresh();
})();
