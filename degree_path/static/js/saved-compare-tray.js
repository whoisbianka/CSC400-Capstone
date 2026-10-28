/* Keep major and program shortlists separate; the server verifies favorites on arrival. */
(() => {
  const workspace = document.getElementById('saved-workspace');
  const tray = document.getElementById('saved-compare-tray');
  if (!workspace || !tray) return;
  const nav = document.getElementById('account-navigation');
  const owner = nav?.dataset.userId;
  if (!owner) return;
  const byId = id => document.getElementById(id);
  const storageKey = `saved-comparison:${owner}`;
  const catalogs = {majors: new Map(), programs: new Map()};
  const selected = {majors: [], programs: []};
  let kind = workspace.dataset.initialSavedView === 'programs' ? 'programs' : 'majors';
  try {
    const saved = JSON.parse(window.sessionStorage.getItem(storageKey) || '{}');
    for (const type of ['majors', 'programs']) {
      if (Array.isArray(saved[type])) selected[type] = [...new Set(saved[type].filter(id => Number.isSafeInteger(id) && id > 0))].slice(0, 3);
    }
  } catch (_) { /* Comparison still works when browser storage is unavailable. */ }
  function node(tag, className, text) {
    const el = document.createElement(tag);
    el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  }
  function remember() {
    try { window.sessionStorage.setItem(storageKey, JSON.stringify(selected)); } catch (_) {}
  }
  function render() {
    const ids = selected[kind];
    const noun = kind === 'majors' ? 'majors' : 'programs';
    byId('saved-tray-title').textContent = ids.length ? `${ids.length} of 3 ${noun} selected` : 'Your comparison starts here';
    byId('saved-tray-hint').textContent = ids.length === 1 ? `Add one more ${kind === 'majors' ? 'major' : 'program'} to compare.`
      : ids.length === 3 ? 'Remove an option to choose another.' : `Select two or three ${noun} to see them side by side.`;
    const chips = byId('saved-tray-items');
    chips.replaceChildren();
    for (const id of ids) {
      const title = catalogs[kind].get(id)?.label || `${kind === 'majors' ? 'Major' : 'Program'} ${id}`;
      const chip = node('span', 'saved-compare-chip');
      chip.append(node('span', '', title));
      const remove = node('button', 'saved-chip-remove', '×');
      remove.type = 'button';
      remove.setAttribute('aria-label', `Remove ${title} from comparison`);
      remove.addEventListener('click', () => removeItem(kind, id));
      chip.append(remove); chips.append(chip);
    }
    byId('saved-tray-clear').disabled = ids.length === 0;
    const action = byId('saved-tray-compare');
    action.disabled = ids.length < 2;
    action.textContent = ids.length >= 2 ? `Compare ${ids.length} ${noun} →` : 'Compare';
    const destination = new URL(workspace.dataset.compareUrl, window.location.origin);
    destination.searchParams.set('view', 'favorites');
    destination.searchParams.set('kind', kind);
    if (ids.length) destination.searchParams.set('ids', ids.join(','));
    if (ids.length >= 2) destination.hash = 'compare-table-container';
    byId('saved-compare-header').href = destination.toString();
    byId('saved-compare-header').textContent = ids.length ? `Compare · ${ids.length}` : 'Compare';
    byId('saved-compare-guidance').textContent = ids.length === 3 ? '3 selected · Remove one to choose another' : `Select up to 3 ${noun} to compare`;
    workspace.querySelectorAll('[data-library-compare]').forEach(button => {
      const type = button.dataset.compareKind;
      const active = selected[type].includes(Number(button.dataset.libraryCompare));
      button.setAttribute('aria-pressed', String(active));
      button.textContent = active ? '✓ Added to compare' : '+ Add to compare';
      button.disabled = !active && selected[type].length === 3;
      button.closest('article').dataset.selected = String(active);
    });
  }
  function removeItem(type, id) {
    selected[type] = selected[type].filter(value => value !== id);
    remember(); render();
  }
  window.SavedCompare = {
    button(type, item) {
      const button = node('button', 'saved-add-compare', '+ Add to compare');
      button.type = 'button';
      button.dataset.libraryCompare = String(item.id);
      button.dataset.compareKind = type;
      button.setAttribute('aria-label', `Compare ${item.label}`);
      button.addEventListener('click', () => {
        if (selected[type].includes(item.id)) removeItem(type, item.id);
        else if (selected[type].length < 3) {
          selected[type].push(item.id); remember(); render();
        }
      });
      return button;
    },
    sync(type, items) {
      catalogs[type] = new Map(items.map(item => [item.id, item]));
      selected[type] = selected[type].filter(id => catalogs[type].has(id));
      remember(); render();
    },
    setKind(type) { kind = type === 'programs' ? 'programs' : 'majors'; render(); },
    remove: removeItem,
  };
  byId('saved-tray-clear').addEventListener('click', () => { selected[kind] = []; remember(); render(); });
  byId('saved-tray-compare').addEventListener('click', () => {
    if (selected[kind].length < 2) return;
    const url = new URL(workspace.dataset.compareUrl, window.location.origin);
    url.searchParams.set('view', 'favorites');
    url.searchParams.set('kind', kind);
    url.searchParams.set('ids', selected[kind].join(','));
    url.hash = 'compare-table-container';
    window.location.assign(url.toString());
  });
  render();
})();
