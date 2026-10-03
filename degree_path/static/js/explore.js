const programTable = document.getElementById('program-table');
if (programTable) {
  const headers = [...programTable.querySelectorAll('.table-sort')];
  const body = programTable.tBodies[0];
  const status = document.getElementById('program-sort-status');
  const pageStatus = status.textContent.split('. ')[0];
  const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' });
  headers.forEach(button => {
    button.addEventListener('click', () => {
      const column = Number(button.dataset.column);
      const descending = button.closest('th').getAttribute('aria-sort') === 'ascending';
      const rows = [...body.rows].filter(row => row.cells.length === headers.length);
      rows.sort((a, b) => collator.compare(a.cells[column].textContent.trim(), b.cells[column].textContent.trim()) * (descending ? -1 : 1));
      rows.forEach(row => body.appendChild(row));
      headers.forEach(header => {
        header.closest('th').setAttribute('aria-sort', header === button ? (descending ? 'descending' : 'ascending') : 'none');
        header.querySelector('span').textContent = header === button ? (descending ? '↓' : '↑') : '↕';
      });
      status.textContent = `${pageStatus}. This page sorted by ${button.childNodes[0].textContent.trim()}, ${descending ? 'descending' : 'ascending'}.`;
    });
  });
}
