// Saved program cards share the library's comparison tray without changing favorites.
(async () => {
  const workspace = document.getElementById('saved-workspace');
  const panel = document.getElementById('saved-programs-panel');
  if (!workspace || !panel) return;
  const majors = document.getElementById('saved-majors-panel');
  const cards = document.getElementById('favorited-program-cards');
  const status = document.getElementById('saved-programs-status');
  const count = document.getElementById('saved-program-count');
  const retry = document.getElementById('saved-programs-retry');
  const tabs = document.querySelectorAll('[data-saved-view]');
  const api = await window.chatApiReady;
  let version = 0;
  let favorites = [];
  const money = value => Number.isFinite(value) ? new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', maximumFractionDigits: 0,
  }).format(value) : 'Not reported';
  function node(tag, className, text) {
    const element = document.createElement(tag);
    element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }
  function syncSelection() {
    window.SavedCompare.sync('programs', favorites.map(program => ({id: program.id, label: `${program.name} · ${program.college} · ${program.credential}`})));
    count.textContent = `${favorites.length} saved`;
    document.getElementById('saved-programs-tab-count').textContent = String(favorites.length);
  }
  function render(requestVersion) {
    cards.replaceChildren();
    status.textContent = favorites.length ? '' : 'No favorite programs yet. Use a heart button in Explore to save one.';
    for (const program of favorites) {
      const card = node('article', 'saved-program-card saved-option-card');
      const body = node('div', 'saved-option-body');
      const top = node('div', 'saved-option-top');
      const degree = node('p', 'saved-card-degree', program.credential || 'Degree not reported');
      const remove = node('button', 'saved-remove-favorite', '♥');
      remove.type = 'button';
      remove.setAttribute('aria-label', `Remove ${program.name} at ${program.college} from favorites`);
      remove.addEventListener('click', async () => {
        remove.disabled = true;
        try {
          await api.setProgramFavorite(program.id, false);
          if (requestVersion !== version) return;
          favorites = favorites.filter(item => item.id !== program.id);
          window.SavedCompare.remove('programs', program.id);
          render(requestVersion);
          status.textContent = favorites.length ? 'Program removed from favorites.' : 'No favorite programs yet. Use a heart button in Explore to save one.';
        } catch (error) {
          if (requestVersion === version) { status.textContent = error.message; remove.disabled = false; }
        }
      });
      top.append(degree, remove);
      const college = node('p', 'saved-card-college', program.college);
      const location = node('p', 'saved-card-location', [program.city, program.state].filter(Boolean).join(', '));
      const facts = node('dl', 'saved-option-facts');
      for (const [label, value] of [['Annual net price', program.npt4], ['Annual earnings', program.earnings]]) {
        const fact = node('div', '');
        fact.append(node('dt', '', label), node('dd', '', money(value)));
        facts.append(fact);
      }
      body.append(top, node('h3', '', program.name), college, location, facts);
      const controls = node('footer', 'saved-option-footer');
      const details = node('a', '', 'Details ↗');
      details.href = `/programs/${Number(program.id)}`;
      details.target = '_blank'; details.rel = 'noopener noreferrer';
      controls.append(window.SavedCompare.button('programs', {id:program.id, label:`${program.name} at ${program.college}, ${program.credential}`}), details);
      card.append(body, controls); cards.append(card);
    }
    syncSelection();
  }
  async function load() {
    const requestVersion = ++version;
    cards.replaceChildren(); count.textContent = ''; retry.hidden = true;
    cards.setAttribute('aria-busy', 'true'); status.textContent = 'Loading saved programs…';
    try {
      const result = await api.loadComparisonFavorites('programs');
      if (requestVersion !== version) return;
      favorites = result.items;
      render(requestVersion);
    } catch (error) {
      if (requestVersion === version) { status.textContent = error.message; retry.hidden = false; }
    } finally {
      if (requestVersion === version) cards.setAttribute('aria-busy', 'false');
    }
  }
  function select(view) {
    const programs = view === 'programs';
    panel.hidden = !programs; majors.hidden = programs;
    tabs.forEach(tab => tab.setAttribute('aria-pressed', String(tab.dataset.savedView === view)));
    window.SavedCompare.setKind(programs ? 'programs' : 'majors');
    if (programs) void load(); else version++;
  }
  tabs.forEach(tab => tab.addEventListener('click', () => select(tab.dataset.savedView)));
  retry.addEventListener('click', load);
  select(workspace.dataset.initialSavedView === 'programs' ? 'programs' : 'majors');
  if (workspace.dataset.initialSavedView !== 'programs') void load();
})();
