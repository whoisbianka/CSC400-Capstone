const degreeForm = document.getElementById('degree-filter-form');
if (degreeForm) {
  const choices = [...degreeForm.querySelectorAll('.degree-choice')];
  degreeForm.addEventListener('change', () => {
    if (!degreeForm.reportValidity()) return;
    document.getElementById('degree-values').value = choices.filter(input => input.checked).map(input => input.value).join(',');
    degreeForm.requestSubmit();
  });
}
