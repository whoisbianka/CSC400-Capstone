(() => {
  const start = () => {
    if (document.querySelector('.material-preview-tools')) return;
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    let paused = false;
    try { paused = sessionStorage.getItem('pathfinder-material-motion') === 'off'; } catch {}
    const running = new Set();
    const entranceSelector = '.feature-card, .program-card, .major-catalog-card, .saved-option-card, .details-panel, .profile-account, #guided-chat .chat-container, .compare-sidebar, .compare-results';
    const enabled = () => !paused && !reduced.matches;
    function animate(element, frames, options) {
      if (!enabled() || !element.animate) return;
      const animation = element.animate(frames, options);
      running.add(animation);
      animation.finished.catch(() => {}).finally(() => running.delete(animation));
      return animation;
    }
    // Damped-spring samples for spatial movement. Opacity uses a non-overshooting curve.
    function springFrames(distance = 22) {
      const stiffness = 380, dampingRatio = .72, w = Math.sqrt(stiffness);
      const wd = w * Math.sqrt(1 - dampingRatio ** 2);
      return Array.from({length: 45}, (_, index) => {
        const fraction = index / 44, time = fraction * .65;
        const progress = index === 44 ? 1 : 1 - Math.exp(-dampingRatio * w * time) *
          (Math.cos(wd * time) + dampingRatio / Math.sqrt(1 - dampingRatio ** 2) * Math.sin(wd * time));
        return {translate: `0 ${distance * (1 - progress)}px`, offset: fraction};
      });
    }
    function enter(element, index = 0) {
      if (!enabled()) return;
      const delay = Math.min(index * 55, 165);
      animate(element, springFrames(), {duration: 650, delay, easing: 'linear'});
      animate(element, [{opacity: .2}, {opacity: 1}], {duration: 250, delay, easing: 'cubic-bezier(.2,0,0,1)'});
    }
    const toolbar = document.createElement('aside');
    toolbar.className = 'material-preview-tools';
    toolbar.setAttribute('aria-label', 'Material preview controls');
    toolbar.innerHTML = '<strong>Material expressive preview</strong><button type="button" data-motion-toggle aria-pressed="true">Motion on</button><button type="button" data-replay>Replay</button><button type="button" data-preview-help>Colors & details</button><a data-preview-exit>Current UI</a>';
    const exit = new URL(location.href);
    exit.searchParams.set('material', 'off');
    toolbar.querySelector('[data-preview-exit]').href = exit;
    const header = document.querySelector('.site-navigation');
    if (header) header.after(toolbar); else document.body.prepend(toolbar);
    const motionButton = toolbar.querySelector('[data-motion-toggle]');
    const replayButton = toolbar.querySelector('[data-replay]');
    function syncMotion() {
      document.documentElement.dataset.materialMotion = enabled() ? 'on' : 'off';
      motionButton.textContent = 'Motion';
      motionButton.title = reduced.matches ? 'Disabled by your reduced motion setting' : 'Enable or disable interaction motion';
      motionButton.disabled = reduced.matches;
      motionButton.setAttribute('aria-pressed', String(enabled()));
      replayButton.disabled = !enabled();
      if (!enabled()) running.forEach(animation => animation.cancel());
    }
    motionButton.addEventListener('click', () => {
      paused = !paused;
      try { sessionStorage.setItem('pathfinder-material-motion', paused ? 'off' : 'on'); } catch {}
      syncMotion();
    });
    reduced.addEventListener('change', syncMotion);
    syncMotion();
    function replay() {
      running.forEach(animation => animation.cancel());
      let index = 0;
      document.querySelectorAll(entranceSelector).forEach(element => {
        const bounds = element.getBoundingClientRect();
        if (bounds.top < innerHeight && bounds.bottom > 0) enter(element, index++);
      });
      const heading = document.querySelector('.path-heading h1, .explore-intro h1, #page-title');
      if (heading) enter(heading);
    }
    replayButton.addEventListener('click', replay);
    const help = document.createElement('dialog');
    help.className = 'material-preview-help';
    help.setAttribute('aria-labelledby', 'material-preview-title');
    help.setAttribute('aria-describedby', 'material-preview-intro');
    help.innerHTML = `<div class="material-dialog-header"><h2 id="material-preview-title" tabindex="-1" autofocus>Color & motion preview</h2><button type="button" data-preview-close aria-label="Close preview settings">×</button></div>
<p id="material-preview-intro">Explore Material color roles on your existing Pathfinder pages.</p>
<fieldset class="material-color-controls"><legend>Color appearance</legend><div class="material-color-fields">
<label for="material-theme">Theme<select id="material-theme"><option value="dark">Dark</option><option value="light">Light</option><option value="system">Use device setting</option></select></label>
<label for="material-contrast">Contrast<select id="material-contrast"><option value="standard">Standard</option><option value="medium">Medium</option><option value="high">High</option></select></label></div></fieldset>
<p class="material-color-note" id="material-color-note">Settings apply only to this preview and follow navigation in this tab.</p>
<div class="material-color-roles" aria-label="Live color role examples"><div class="material-role-primary">Primary<small>Key actions</small></div><div class="material-role-secondary">Secondary container<small>Selection & quieter controls</small></div><div class="material-role-tertiary">Tertiary container<small>Small supporting accents</small></div><div class="material-role-surface">Surface container<small>Content & hierarchy</small></div></div>
<p>Each fill is paired with its matching foreground. Neutral surfaces carry the layout; lavender periwinkle emphasizes actions, blue-gray marks selection, and warm tan adds small accents. Save notifications use inverse surface colors. Error colors are reserved for errors.</p>
<ul><li><strong>Motion:</strong> hover and press feedback, expanding content, and save confirmations. Page navigation is immediate.</li><li><strong>Shape:</strong> rounded cards, pill controls, and shaped illustration containers.</li><li><strong>Accessibility:</strong> visible focus, existing labels, adjustable contrast, and reduced-motion support.</li></ul>
<p><a href="https://m3.material.io/styles/color/the-color-system" target="_blank" rel="noopener noreferrer">Material color roles ↗</a> · <a href="https://m3.material.io/styles/motion" target="_blank" rel="noopener noreferrer">Motion guidance ↗</a></p><button type="button" data-preview-back>Back to preview</button>`;
    document.body.append(help);
    toolbar.querySelector('[data-preview-help]').addEventListener('click', () => {
      help.showModal(); enter(help);
    });
    help.querySelectorAll('[data-preview-close], [data-preview-back]').forEach(button => button.addEventListener('click', () => help.close()));
    const themeSelect = help.querySelector('#material-theme');
    const contrastSelect = help.querySelector('#material-contrast');
    const lightPreference = matchMedia('(prefers-color-scheme: light)');
    const highContrastPreference = matchMedia('(prefers-contrast: more)');
    let themeChoice = 'dark', contrastChoice = 'standard';
    try {
      themeChoice = sessionStorage.getItem('pathfinder-material-theme') || themeChoice;
      contrastChoice = sessionStorage.getItem('pathfinder-material-contrast') || contrastChoice;
    } catch {}
    if (!['dark', 'light', 'system'].includes(themeChoice)) themeChoice = 'dark';
    if (!['standard', 'medium', 'high'].includes(contrastChoice)) contrastChoice = 'standard';
    function applyColorSettings() {
      const root = document.documentElement;
      root.dataset.materialTheme = themeChoice === 'system' ? (lightPreference.matches ? 'light' : 'dark') : themeChoice;
      root.dataset.materialContrast = highContrastPreference.matches ? 'high' : contrastChoice;
      themeSelect.value = themeChoice;
      contrastSelect.value = root.dataset.materialContrast;
      contrastSelect.disabled = highContrastPreference.matches;
      help.querySelector('#material-color-note').textContent = highContrastPreference.matches
        ? 'High contrast follows your device setting. Theme choices apply only to this preview.'
        : 'Settings apply only to this preview and follow navigation in this tab.';
    }
    themeSelect.addEventListener('change', () => {
      themeChoice = themeSelect.value;
      try { sessionStorage.setItem('pathfinder-material-theme', themeChoice); } catch {}
      applyColorSettings();
    });
    contrastSelect.addEventListener('change', () => {
      contrastChoice = contrastSelect.value;
      try { sessionStorage.setItem('pathfinder-material-contrast', contrastChoice); } catch {}
      applyColorSettings();
    });
    lightPreference.addEventListener('change', applyColorSettings);
    highContrastPreference.addEventListener('change', applyColorSettings);
    applyColorSettings();

    // Page content appears immediately; motion is reserved for direct interactions.
    const nav = document.querySelector('.site-navigation');
    let scrollFrame;
    const updateScroll = () => {
      if (scrollFrame) return;
      scrollFrame = requestAnimationFrame(() => {
        nav?.classList.toggle('material-scrolled', scrollY > 20);
        scrollFrame = null;
      });
    };
    addEventListener('scroll', updateScroll, {passive: true});
    updateScroll();
    const rippleSelector = 'button, .primary-link, .secondary-button, .feature-card, .explore-tabs a, .site-navigation nav a';
    function ripple(event) {
      if (!enabled()) return;
      const host = event.target.closest(rippleSelector);
      if (!host || host.disabled || host.closest('.material-preview-tools')) return;
      host.classList.add('material-ripple-host');
      const box = host.getBoundingClientRect();
      const diameter = Math.hypot(box.width, box.height) * 2;
      const dot = document.createElement('span');
      dot.className = 'material-ripple'; dot.setAttribute('aria-hidden', 'true');
      const x = event.type === 'click' ? box.width / 2 : event.clientX - box.left;
      const y = event.type === 'click' ? box.height / 2 : event.clientY - box.top;
      Object.assign(dot.style, {width: `${diameter}px`, height: `${diameter}px`, left: `${x - diameter/2}px`, top: `${y - diameter/2}px`});
      host.append(dot);
      const animation = animate(dot, [{scale: 0, opacity: .14}, {scale: 1, opacity: 0}], {duration: 450, easing: 'cubic-bezier(.2,0,0,1)'});
      if (animation) animation.finished.catch(() => {}).finally(() => dot.remove());
      else dot.remove();
    }
    document.addEventListener('pointerdown', ripple);
    document.addEventListener('click', event => { if (event.detail === 0) ripple(event); });
    document.addEventListener('toggle', event => {
      const details = event.target;
      if (!details.matches?.('details[open]') || !enabled()) return;
      [...details.children].filter(child => child.tagName !== 'SUMMARY').forEach((child, index) => enter(child, index));
    }, true);
    // Animate confirmations only after the actual app has updated its state.
    new MutationObserver(records => {
      for (const record of records) {
        const target = record.target;
        if (record.type === 'attributes') {
          if (record.attributeName === 'aria-pressed' && target.getAttribute('aria-pressed') === 'true' && target.matches('[data-save-major], [data-program-favorite], .saved-add-compare')) {
            animate(target, [{scale: 1}, {scale: 1.12, offset: .45}, {scale: 1}], {duration: 340, easing: 'cubic-bezier(.2,0,0,1)'});
          }
          if (record.attributeName === 'hidden' && !target.hidden && target.matches('.major-save-toast, .saved-compare-tray')) enter(target);
          continue;
        }
        for (const node of record.addedNodes) {
          if (node.nodeType !== 1) continue;
          if (node.matches('.bot-message, .user-message')) enter(node);
        }
      }
    }).observe(document.body, {subtree: true, childList: true, attributes: true, attributeFilter: ['aria-pressed', 'hidden']});
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});
  else start();
})();
