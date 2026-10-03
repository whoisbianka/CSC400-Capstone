// Track the pointer within each card. CSS uses these percentages to position its glow.
// Links remain normal links, so navigation also works without JavaScript.
document.querySelectorAll('.feature-card').forEach((card) => {
  card.addEventListener('pointermove', (event) => {
    const bounds = card.getBoundingClientRect();
    card.style.setProperty('--mx', `${(event.clientX - bounds.left) / bounds.width * 100}%`);
    card.style.setProperty('--my', `${(event.clientY - bounds.top) / bounds.height * 100}%`);
  });
  // Return the glow to its resting position when the pointer leaves.
  card.addEventListener('pointerleave', () => {
    card.style.removeProperty('--mx');
    card.style.removeProperty('--my');
  });
});
