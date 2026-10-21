const degreeForm = document.getElementById('degree-filter-form');
if (degreeForm) {
  const choices = [...degreeForm.querySelectorAll('.degree-choice')];
  degreeForm.addEventListener('change', () => {
    if (!degreeForm.reportValidity()) return;
    document.getElementById('degree-values').value = choices.filter(input => input.checked).map(input => input.value).join(',');
    degreeForm.requestSubmit();
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
