const majorSearch = document.getElementById('major-search');
if (majorSearch) {
  document.getElementById('major-search-controls').hidden = false;
  const options = [...document.querySelectorAll('[data-major]')];
  const empty = document.getElementById('major-search-empty');
  majorSearch.addEventListener('input', () => {
    const query = majorSearch.value.trim().toLocaleLowerCase();
    let matches = 0;
    options.forEach(option => {
      option.hidden = !option.dataset.major.toLocaleLowerCase().includes(query);
      if (!option.hidden) matches += 1;
    });
    empty.hidden = matches > 0;
  });
}

const degreeForm = document.getElementById('degree-filter-form');
if (degreeForm) {
  const choices = [...degreeForm.querySelectorAll('.degree-choice')];
  choices.forEach(choice => choice.addEventListener('change', () => {
    document.getElementById('degree-values').value = choices.filter(input => input.checked).map(input => input.value).join(',');
    degreeForm.requestSubmit();
  }));
}
