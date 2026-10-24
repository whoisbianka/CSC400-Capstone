// Program favorites live alongside the saved-major library on one page.
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
  function node(tag, className, text) {
    const element = document.createElement(tag);
    element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }
  function render(favorites, requestVersion) {
    count.textContent = `${favorites.length} saved`;
    status.textContent = favorites.length ? '' : 'No favorite programs yet. Use a heart button in Explore to save one.';
    for (const program of favorites) {
      const card = node('article', 'saved-program-card');
      const title = node('h4', '', program.major);
      const college = node('p', 'saved-card-college', program.college);
      college.append(node('span', 'saved-card-location', [program.city, program.state].filter(Boolean).join(', ')));
      const degree = node('p', 'saved-card-degree', program.credential || 'Degree not reported');
      const controls = node('div', 'saved-card-controls');
      const details = node('a', '', 'View program ↗');
      details.href = `/programs/${Number(program.program_id)}`;
      details.target = '_blank';
      details.rel = 'noopener noreferrer';
      const remove = node('button', 'secondary-button', '♥ Remove favorite');
      remove.type = 'button';
      remove.setAttribute('aria-label', `Remove ${program.major} at ${program.college} from favorites`);
      remove.addEventListener('click', async () => {
        remove.disabled = true;
        try {
          await api.setProgramFavorite(Number(program.program_id), false);
          if (requestVersion !== version) return;
          card.remove();
          count.textContent = `${cards.children.length} saved`;
          status.textContent = cards.children.length ? 'Program removed from favorites.' : 'No favorite programs yet. Use a heart button in Explore to save one.';
        } catch (error) {
          if (requestVersion === version) { status.textContent = error.message; remove.disabled = false; }
        }
      });
      controls.append(details, remove);
      card.append(title, college, degree, controls);
      cards.append(card);
    }
  }
  async function load() {
    const requestVersion = ++version;
    cards.replaceChildren();
    count.textContent = '';
    retry.hidden = true;
    cards.setAttribute('aria-busy', 'true');
    status.textContent = 'Loading saved programs…';
    try {
      const result = await api.loadProgramFavorites();
      if (requestVersion === version) render(result.favorites, requestVersion);
    } catch (error) {
      if (requestVersion === version) { status.textContent = error.message; retry.hidden = false; }
    } finally {
      if (requestVersion === version) cards.setAttribute('aria-busy', 'false');
    }
  }
  function select(view) {
    const programs = view === 'programs';
    panel.hidden = !programs;
    majors.hidden = programs;
    tabs.forEach(tab => tab.setAttribute('aria-pressed', String(tab.dataset.savedView === view)));
    if (programs) void load(); else version++;
  }
  tabs.forEach(tab => tab.addEventListener('click', () => select(tab.dataset.savedView)));
  retry.addEventListener('click', load);
  select(workspace.dataset.initialSavedView === 'programs' ? 'programs' : 'majors');
})();
