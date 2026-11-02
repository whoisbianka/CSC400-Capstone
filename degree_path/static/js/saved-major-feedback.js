// Shared, server-confirmed feedback for saved majors and favorited college programs.
(() => {
  const toast = document.createElement('section');
  toast.className = 'major-save-toast';
  toast.setAttribute('aria-label', 'Save notification');
  toast.hidden = true;
  const icon = document.createElement('span');
  icon.className = 'major-save-toast-check';
  icon.textContent = '✓';
  icon.setAttribute('aria-hidden', 'true');
  const content = document.createElement('div');
  content.className = 'major-save-toast-content';
  const message = document.createElement('div');
  message.setAttribute('role', 'status');
  message.setAttribute('aria-live', 'polite');
  message.setAttribute('aria-atomic', 'true');
  const title = document.createElement('p');
  title.className = 'major-save-toast-title';
  const detail = document.createElement('p');
  detail.className = 'major-save-toast-detail';
  message.append(title, detail);
  const actions = document.createElement('div');
  actions.className = 'major-save-toast-actions';
  const view = document.createElement('a');
  view.href = '/saved-majors';
  view.textContent = 'View saved majors →';
  const undo = document.createElement('button');
  undo.type = 'button';
  undo.textContent = 'Undo';
  const error = document.createElement('p');
  error.className = 'major-save-toast-error';
  error.setAttribute('role', 'alert');
  actions.append(view, undo);
  content.append(message, actions, error);
  const dismiss = document.createElement('button');
  dismiss.type = 'button';
  dismiss.className = 'major-save-toast-dismiss';
  dismiss.textContent = '×';
  dismiss.setAttribute('aria-label', 'Dismiss save notification');
  toast.append(icon, content, dismiss);
  document.body.append(toast);
  let origin;
  let revision = 0;
  let action;
  let name;
  let collection;
  function restoreFocus() {
    if (toast.contains(document.activeElement) && origin?.isConnected) origin.focus();
  }
  function measureToast() {
    document.documentElement?.style.setProperty('--a11y-toast-height', toast.hidden ? '0px' : `${Math.ceil(toast.getBoundingClientRect().height)}px`);
  }
  function hide() { restoreFocus(); toast.hidden = true; measureToast(); }
  dismiss.addEventListener('click', hide);
  if ('ResizeObserver' in window) new ResizeObserver(measureToast).observe(toast);
  undo.addEventListener('click', async () => {
    if (!action || undo.disabled) return;
    const current = revision;
    const undoAction = action;
    const itemName = name;
    const currentCollection = collection;
    undo.disabled = true;
    error.textContent = '';
    try {
      await undoAction();
      // An older request must not replace feedback for a more recent save.
      if (current !== revision) return;
      title.textContent = 'Save undone';
      detail.textContent = `${itemName} was removed from your ${currentCollection}.`;
      if (document.activeElement === undo) dismiss.focus();
      undo.hidden = true;
      action = null;
    } catch (problem) {
      if (current === revision) error.textContent = problem.message || 'Could not undo. Please try again.';
    } finally {
      if (current === revision) { undo.disabled = false; }
    }
  });
  window.MajorSaveFeedback = {
    show({ majorName, programName, onUndo, button }) {
      const isProgram = Boolean(programName);
      origin = button;
      revision++;
      name = programName || majorName;
      collection = isProgram ? 'favorited programs' : 'saved majors';
      action = onUndo;
      title.textContent = isProgram ? 'Program saved' : 'Major saved';
      detail.textContent = `${name} was added to your ${collection}.`;
      view.href = isProgram ? '/saved-majors?view=programs' : '/saved-majors';
      view.textContent = isProgram ? 'View saved programs →' : 'View saved majors →';
      error.textContent = '';
      undo.hidden = !onUndo;
      undo.disabled = false;
      toast.hidden = false;
      toast.classList.remove('major-save-toast-enter');
      void toast.offsetWidth;
      toast.classList.add('major-save-toast-enter');
      const symbol = isProgram ? '♥' : '★';
      if (button?.isConnected && button.textContent.startsWith(symbol)) {
        const text = button.textContent;
        const star = document.createElement('span');
        star.className = 'major-save-star-pop';
        star.textContent = symbol;
        star.setAttribute('aria-hidden', 'true');
        button.replaceChildren(star, document.createTextNode(text.slice(1)));
      }
      measureToast();
    },
  };
})();
