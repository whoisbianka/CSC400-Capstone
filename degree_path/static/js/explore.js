const degreeForm = document.getElementById('degree-filter-form');
if (degreeForm) {
  degreeForm.addEventListener('submit', () => {
    const choices = [...degreeForm.querySelectorAll('.degree-choice')];
    document.getElementById('degree-values').value = choices.filter(input => input.checked).map(input => input.value).join(',');
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
document.querySelectorAll('.explore-pagination a, .explore-sidebar .sidebar-heading a, .explore-empty a, .active-filters a').forEach(link => {
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

// Each search keeps its own form and server-side query parameters.
(() => {
  for (const [sortId, formId] of [['program-sort', 'degree-filter-form'], ['major-sort', 'major-filter-form']]) {
    const sort = document.getElementById(sortId);
    const form = document.getElementById(formId);
    if (sort && form) sort.addEventListener('change', () => form.requestSubmit());
  }
  const majorForm = document.getElementById('major-filter-form');
  if (majorForm) {
    majorForm.addEventListener('submit', showExploreLoading);
    majorForm.querySelector('[name="favorites_only"]')?.addEventListener('change', () => majorForm.requestSubmit());
  }
  const mode = document.getElementById('major-filter');
  if (!mode) return;
  const nameFields = document.querySelector('[data-major-name-fields]');
  const favoriteFields = document.querySelector('[data-major-favorite-fields]');
  const name = document.getElementById('major-name');
  function updateMajorFields() {
    for (const [container, active] of [[nameFields, mode.value === 'name'], [favoriteFields, mode.value === 'favorites']]) {
      if (!container) continue;
      container.hidden = !active;
      container.querySelectorAll('input').forEach(input => { input.disabled = !active; });
    }
    name.required = mode.value === 'name' && !nameFields.querySelector('[name="cipcode"]');
  }
  mode.addEventListener('change', updateMajorFields);
  updateMajorFields();
  const options = document.getElementById('major-name-options');
  const status = document.getElementById('major-search-status');
  let timer;
  let controller;
  name.addEventListener('input', () => {
    clearTimeout(timer);
    controller?.abort();
    options.replaceChildren();
    status.textContent = '';
    const query = name.value.trim();
    if (query.length < 2) return;
    timer = setTimeout(async () => {
      controller = new AbortController();
      try {
        const url = new URL(name.dataset.suggestionsUrl, window.location.origin);
        url.searchParams.set('q', query);
        const response = await fetch(url, { signal: controller.signal });
        if (!response.ok) throw new Error('Major suggestions unavailable');
        const data = await response.json();
        if (name.value.trim() !== query) return;
        options.replaceChildren(...data.majors.map(major => {
          const option = document.createElement('option');
          option.value = major.name;
          return option;
        }));
      } catch (error) {
        if (error.name !== 'AbortError') status.textContent = 'Suggestions are unavailable. Enter an exact major name or browse Explore majors.';
      }
    }, 250);
  });
})();
