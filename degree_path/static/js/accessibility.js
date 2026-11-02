// Keep keyboard targets clear of the sticky header and persistent save feedback.
(() => {
  const header = document.querySelector('.site-navigation');
  const root = document.documentElement;
  function measureHeader() {
    root.style.setProperty('--a11y-header-height', `${Math.ceil(header?.getBoundingClientRect().height || 0)}px`);
  }
  measureHeader();
  if (header && 'ResizeObserver' in window) new ResizeObserver(measureHeader).observe(header);
  addEventListener('resize', measureHeader, {passive: true});
  document.addEventListener('click', event => {
    const link = event.target.closest('.skip-link, .home-skip-link');
    if (!link) return;
    const main = document.getElementById('main-content');
    if (!main) return;
    event.preventDefault();
    main.focus({preventScroll: true});
    main.scrollIntoView({block: 'start', behavior: 'instant'});
  });
  document.addEventListener('focusin', event => {
    const target = event.target;
    if (!(target instanceof HTMLElement) || target.matches('main') || target.closest('dialog, .site-navigation, .skip-link, .home-skip-link')) return;
    requestAnimationFrame(() => {
      if (document.activeElement !== target) return;
      const bounds = target.getBoundingClientRect();
      const top = header?.getBoundingClientRect().bottom || 0;
      const toast = document.querySelector('.major-save-toast:not([hidden])');
      const toastBounds = toast?.getBoundingClientRect();
      const behindToast = toastBounds && !toast.contains(target) && bounds.bottom > toastBounds.top && bounds.top < toastBounds.bottom && bounds.right > toastBounds.left && bounds.left < toastBounds.right;
      if (bounds.top < top + 8 || bounds.bottom > innerHeight - 8 || behindToast) {
        target.scrollIntoView({block: 'center', inline: 'nearest', behavior: 'instant'});
      }
    });
  });
})();
