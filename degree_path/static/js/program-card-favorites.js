(async () => {
  const buttons = [...document.querySelectorAll('[data-program-favorite]')];
  if (!buttons.length) return;
  const status = document.getElementById('program-favorites-status');
  const retry = document.getElementById('program-favorites-retry');
  const api = await window.chatApiReady;
  const saved = new Set();
  function label(button) {
    const favorite = saved.has(Number(button.dataset.programFavorite));
    button.textContent = favorite ? 'Remove favorite' : 'Favorite program';
    button.setAttribute('aria-pressed', String(favorite));
  }
  async function load() {
    retry.hidden = true;
    buttons.forEach(button => {button.disabled = true;});
    try {
      // One request for the whole results page, not one per card.
      const result = await api.loadProgramFavorites();
      saved.clear();
      result.favorites.forEach(item => saved.add(Number(item.program_id)));
      buttons.forEach(button => {label(button); button.disabled = false;});
      status.textContent = '';
    } catch (error) {
      status.textContent = error.message;
      buttons.forEach(button => {button.textContent = 'Favorites unavailable';});
      retry.hidden = false;
    }
  }
  buttons.forEach(button => button.addEventListener('click', async () => {
    const id = Number(button.dataset.programFavorite);
    button.disabled = true;
    try {
      const result = await api.setProgramFavorite(id, !saved.has(id));
      if (result.favorite) saved.add(id); else saved.delete(id);
      label(button);
      status.textContent = result.favorite ? 'Program added to favorites.' : 'Program removed from favorites.';
    } catch (error) {status.textContent = error.message;}
    finally {button.disabled = false;}
  }));
  retry.addEventListener('click', load);
  await load();
})();
