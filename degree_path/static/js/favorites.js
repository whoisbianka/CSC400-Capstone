(async function () {
  'use strict';
  const page = document.getElementById('favorites-page');
  const cards = document.getElementById('favoriteCards');
  const status = document.getElementById('favoritesStatus');
  const retry = document.getElementById('retryFavorites');
  const tabs = document.querySelectorAll('[data-favorite-kind]');
  const api = await window.chatApiReady;
  let kind = page.dataset.initialKind === 'programs' ? 'programs' : 'majors';
  let version = 0;
  function emptyMessage() {
    return kind === 'majors'
      ? 'No favorite majors yet. Save one from your chat recommendations.'
      : 'No favorite programs yet. Use Favorite program on an Explore card.';
  }
  function render(favorites, requestVersion) {
    cards.replaceChildren();
    if (!favorites.length) {status.textContent = emptyMessage(); return;}
    status.textContent = '';
    const programs = kind === 'programs';
    for (const favorite of favorites) {
      const card = document.createElement('article'); card.className = 'favorite-card';
      const title = document.createElement('h3'); title.textContent = favorite.major;
      card.appendChild(title);
      if (programs) {
        const details = document.createElement('p');
        details.textContent = `${favorite.college} · ${favorite.credential}`;
        const location = document.createElement('p');
        location.textContent = [favorite.city, favorite.state].filter(Boolean).join(', ');
        card.append(details, location);
      }
      const link = document.createElement('a');
      if (programs) {
        link.href = favorite.url;
        link.textContent = 'View program →';
      } else {
        const destination = new URL(page.dataset.exploreUrl, window.location.origin);
        destination.searchParams.set('cipcode', favorite.cipcode);
        link.href = destination.href;
        link.textContent = 'Explore programs in this major →';
      }
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'secondary-button';
      button.textContent = 'Remove favorite'; button.setAttribute('aria-pressed', 'true');
      button.addEventListener('click', async () => {
        button.disabled = true;
        try {
          if (programs) await api.setProgramFavorite(Number(favorite.program_id), false);
          else await api.setFavorite(Number(favorite.cipcode), false);
          // A response from the previous tab must not change the current tab.
          if (requestVersion !== version) return;
          card.remove();
          status.textContent = cards.children.length ? 'Favorite removed.' : emptyMessage();
        } catch (error) {
          if (requestVersion !== version) return;
          status.textContent = error.message; button.disabled = false;
        }
      });
      card.append(link, button); cards.appendChild(card);
    }
  }
  async function load(nextKind = kind) {
    kind = nextKind;
    const requestVersion = ++version;
    cards.replaceChildren(); cards.setAttribute('aria-busy', 'true');
    retry.hidden = true; status.textContent = 'Loading favorites…';
    document.getElementById('favorites-heading').textContent = `Favorite ${kind}`;
    tabs.forEach(tab => tab.setAttribute('aria-pressed', String(tab.dataset.favoriteKind === kind)));
    try {
      const result = kind === 'programs' ? await api.loadProgramFavorites() : await api.loadFavorites();
      if (requestVersion !== version) return;
      render(result.favorites, requestVersion);
    } catch (error) {
      if (requestVersion !== version) return;
      status.textContent = error.message; retry.hidden = false;
    } finally {
      if (requestVersion === version) cards.setAttribute('aria-busy', 'false');
    }
  }
  tabs.forEach(tab => tab.addEventListener('click', () => load(tab.dataset.favoriteKind)));
  retry.addEventListener('click', () => load());
  await load();
})();
