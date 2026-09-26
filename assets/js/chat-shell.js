(() => {
  const toggle = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('app-sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  const mobile = window.matchMedia('(max-width: 760px)');
  function setOpen(open, restoreFocus = false) {
    document.body.classList.toggle('nav-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    backdrop.hidden = !open;
    sidebar.inert = mobile.matches && !open;
    if (open) sidebar.querySelector('a').focus();
    else if (restoreFocus) toggle.focus();
  }
  toggle.addEventListener('click', () => setOpen(toggle.getAttribute('aria-expanded') !== 'true'));
  backdrop.addEventListener('click', () => setOpen(false, true));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') setOpen(false, true);
    if (event.key === 'Tab' && mobile.matches && document.body.classList.contains('nav-open')) {
      const items = [...sidebar.querySelectorAll('a,button')].filter(el => !el.hidden);
      const first = items[0], last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  sidebar.querySelectorAll('a,button').forEach(el => el.addEventListener('click', () => { if (mobile.matches) setOpen(false); }));
  mobile.addEventListener('change', () => setOpen(false));
  setOpen(false);
})();
