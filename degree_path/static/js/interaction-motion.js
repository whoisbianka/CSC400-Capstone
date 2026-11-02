// Shared interaction motion. Content and navigation appear immediately.
(() => {
  const start = () => {
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const running = new Set();
    const enabled = () => !reduced.matches;
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
      animate(element, springFrames(8), {duration: 280, delay, easing: 'linear'});
      animate(element, [{opacity: .2}, {opacity: 1}], {duration: 180, delay, easing: 'cubic-bezier(.2,0,0,1)'});
    }
    reduced.addEventListener('change', () => { if (reduced.matches) running.forEach(animation => animation.cancel()); });
    const rippleSelector = 'button, .primary-link, .secondary-button, .feature-card';
    function ripple(event) {
      if (!enabled()) return;
      const host = event.target.closest(rippleSelector);
      if (!host || host.disabled) return;
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
