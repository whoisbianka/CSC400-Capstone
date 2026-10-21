(async () => {
  const api = await window.chatApiReady;
  const status = document.getElementById('major-favorites-status');
  document.querySelectorAll('[data-major-favorite]').forEach(button => {
    button.addEventListener('click', async () => {
      const desired = button.getAttribute('aria-pressed') !== 'true';
      button.disabled = true;
      try {
        const result = await api.setFavorite(Number(button.dataset.majorFavorite), desired);
        button.setAttribute('aria-pressed', String(result.favorite));
        button.textContent = result.favorite ? 'Remove favorite' : 'Favorite major';
        status.textContent = result.favorite ? 'Major added to favorites.' : 'Major removed from favorites.';
      } catch (error) { status.textContent = error.message; }
      finally { button.disabled = false; }
    });
  });
})();
