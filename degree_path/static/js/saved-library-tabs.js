/* Switch Saved views independently of requests for majors or programs. */
(() => {
  const workspace = document.getElementById('saved-workspace');
  if (!workspace) return;
  const tabs = [...workspace.querySelectorAll('[data-saved-view]')];
  const byId = id => document.getElementById(id);
  function select(view) {
    if (!tabs.some(tab => tab.dataset.savedView === view)) view = 'majors';
    workspace.dataset.activeSavedView = view;
    for (const kind of ['majors', 'programs', 'filters']) {
      const panel = byId(`saved-${kind}-panel`); if (panel) panel.hidden = kind !== view;
    }
    tabs.forEach(tab => tab.setAttribute('aria-pressed', String(tab.dataset.savedView === view)));
    for (const id of ['saved-majors-list', 'saved-compare-header', 'saved-compare-guidance', 'saved-compare-tray']) {
      const el = byId(id); if (el) el.hidden = view === 'filters';
    }
    if (view === 'filters') window.SavedFilters?.render(); else window.SavedCompare?.setKind(view);
    workspace.dispatchEvent(new CustomEvent('saved-view-change', {detail: {view}}));
    const url = new URL(window.location.href); url.searchParams.set('view', view);
    window.history.replaceState(null, '', url.toString());
  }
  tabs.forEach(tab => tab.addEventListener('click', () => select(tab.dataset.savedView)));
  window.addEventListener('popstate', () => select(new URL(window.location.href).searchParams.get('view') || 'majors'));
  select(workspace.dataset.initialSavedView);
})();
