// Opt-in study; the regular application remains unchanged unless enabled.
(() => {
  const query = new URL(location.href).searchParams.get('material');
  let enabled = query === 'on';
  let theme = 'dark', contrast = 'standard';
  try {
    if (query === 'off') sessionStorage.removeItem('pathfinder-material-preview');
    else if (query === 'on') sessionStorage.setItem('pathfinder-material-preview', 'on');
    if (query !== 'off') enabled ||= sessionStorage.getItem('pathfinder-material-preview') === 'on';
    theme = sessionStorage.getItem('pathfinder-material-theme') || theme;
    contrast = sessionStorage.getItem('pathfinder-material-contrast') || contrast;
  } catch {}
  if (!enabled) return;
  if (!['dark', 'light', 'system'].includes(theme)) theme = 'dark';
  if (!['standard', 'medium', 'high'].includes(contrast)) contrast = 'standard';
  const root = document.documentElement;
  root.dataset.materialPreview = 'on';
  root.dataset.materialTheme = theme === 'system' ? (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark') : theme;
  root.dataset.materialContrast = matchMedia('(prefers-contrast: more)').matches ? 'high' : contrast;
  // The parser has loaded the color tokens; let them own theme colors from here.
  root.style.removeProperty('color-scheme');
  root.style.removeProperty('background-color');
  const assetRoot = new URL('../', document.currentScript.src);
  const style = document.createElement('link');
  style.rel = 'stylesheet';
  style.href = new URL('css/material-preview.css', assetRoot);
  document.head.append(style);
  const script = document.createElement('script');
  script.src = new URL('js/material-preview.js', assetRoot);
  script.defer = true;
  document.head.append(script);
})();
