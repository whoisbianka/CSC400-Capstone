const degreeForm = document.getElementById('degree-filter-form');
if (degreeForm) {
  const name = document.getElementById('major-name');
  const options = document.getElementById('major-name-options');
  const searchStatus = document.getElementById('major-search-status');
  let timer;
  let searchVersion = 0;
  name.addEventListener('input', () => {
    document.getElementById('legacy-cipcode')?.remove();
    clearTimeout(timer);
    const version = ++searchVersion;
    options.replaceChildren();
    searchStatus.textContent = '';
    const query = name.value.trim();
    if (query.length < 2) return;
    timer = setTimeout(async () => {
      try {
        const url = new URL(name.dataset.suggestionsUrl, window.location.origin);
        url.searchParams.set('q', query);
        const response = await fetch(url);
        const result = await response.json();
        if (version !== searchVersion) return;
        if (!response.ok) throw new Error(result.error || 'Unable to load suggestions.');
        for (const major of result.majors) {
          const option = document.createElement('option');
          option.value = major.name;
          options.appendChild(option);
        }
        searchStatus.textContent = result.majors.length ? '' : 'No matching major names. Try another search.';
      } catch (error) {
        if (version === searchVersion) searchStatus.textContent = error.message;
      }
    }, 250);
  });
  degreeForm.addEventListener('submit', () => {
    document.getElementById('degree-values').value = [...degreeForm.querySelectorAll('.degree-choice:checked')].map(input => input.value).join(',');
  });
}

// Keep normal navigation while giving immediate feedback during server queries.
const exploreLoading = document.getElementById('explore-loading');
const exploreResults = document.querySelector('.explore-results');
function showExploreLoading() {
  if (exploreLoading) exploreLoading.hidden = false;
  if (exploreResults) exploreResults.setAttribute('aria-busy', 'true');
}
if (degreeForm) degreeForm.addEventListener('submit', showExploreLoading);
document.querySelectorAll('.explore-pagination a, .explore-sidebar .sidebar-heading a, .explore-empty a').forEach(link => {
  link.addEventListener('click', event => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    showExploreLoading();
  });
});
// Browser Back can restore this document with its previous loading state.
window.addEventListener('pageshow', () => {
  if (exploreLoading) exploreLoading.hidden = true;
  if (exploreResults) exploreResults.removeAttribute('aria-busy');
});
