// Enhance the two homepage cards without changing navigation.
const section = document.querySelector('.path-section');
const cards = [...document.querySelectorAll('.path-section .feature-card')];
const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
const clamp = value => Math.max(0, Math.min(1, value));
let anchors = [];
let frame = 0;
let measureNextFrame = true;

function renderCards() {
  frame = 0;
  if (measureNextFrame) {
    section.classList.remove('scroll-motion');
    anchors = cards.map(card => card.getBoundingClientRect().top + window.scrollY);
    if (!motionPreference.matches) section.classList.add('scroll-motion');
    measureNextFrame = false;
  }
  if (motionPreference.matches) return;
  const height = window.innerHeight;
  const pageTravel = Math.max(0, document.documentElement.scrollHeight - height);
  cards.forEach((card, index) => {
    const start = height * .95 - (window.innerWidth > 640 ? index * 32 : 0);
    const finish = Math.min(start - 1, Math.max(height * .25, anchors[index] - pageTravel));
    const progress = clamp((start - (anchors[index] - window.scrollY)) / (start - finish));
    card.style.setProperty('--reveal-shift', `${32 * (1 - progress) ** 2}px`);
  });
}
function scheduleCards() {
  if (!frame) frame = window.requestAnimationFrame(renderCards);
}
window.addEventListener('scroll', scheduleCards, { passive: true });
function remeasureCards() {
  measureNextFrame = true;
  scheduleCards();
}
window.addEventListener('resize', remeasureCards);
window.addEventListener('pageshow', remeasureCards);
window.addEventListener('load', remeasureCards);
motionPreference.addEventListener('change', remeasureCards);
cards.forEach(card => {
  card.addEventListener('pointermove', event => {
    if (motionPreference.matches || event.pointerType !== 'mouse') return;
    const bounds = card.getBoundingClientRect();
    card.style.setProperty('--mx', `${(event.clientX - bounds.left) / bounds.width * 100}%`);
    card.style.setProperty('--my', `${(event.clientY - bounds.top) / bounds.height * 100}%`);
  });
  card.addEventListener('pointerleave', () => {
    card.style.removeProperty('--mx');
    card.style.removeProperty('--my');
  });
});
if (section) scheduleCards();
