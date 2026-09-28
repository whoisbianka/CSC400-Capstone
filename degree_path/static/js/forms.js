// Optional keyboard convenience. All forms and results also work without JavaScript.
document.querySelectorAll('[data-enter-submit]').forEach(input => {
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      input.form.requestSubmit();
    }
  });
});
