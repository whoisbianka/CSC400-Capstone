(async () => {
  const button = document.getElementById('program-favorite');
  const status = document.getElementById('program-favorite-status');
  const retry = document.getElementById('program-favorite-retry');
  const api = await window.chatApiReady;
  const id = Number(button.dataset.programId);
  let favorite = false;
  function render() {
    button.textContent = favorite ? 'Remove favorite program' : 'Favorite program';
    button.setAttribute('aria-pressed', String(favorite));
  }
  async function load() {
    retry.hidden = true; button.disabled = true;
    try {
      const result = await api.loadProgramFavorite(id);
      favorite = result.favorite; render(); button.disabled = false; status.textContent = '';
    } catch (error) { status.textContent = error.message; retry.hidden = false; }
  }
  button.addEventListener('click', async () => {
    button.disabled = true;
    try {
      const result = await api.setProgramFavorite(id, !favorite);
      favorite = result.favorite; render();
      status.textContent = favorite ? 'Saved. You can now select this program on Compare.' : 'Favorite removed.';
    } catch (error) { status.textContent = error.message; }
    finally { button.disabled = false; }
  });
  retry.addEventListener('click', load);
  await load();
})();
