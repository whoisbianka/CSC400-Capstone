/* Browser-local filter sets, separated by account and shared between Explore and Saved. */
(() => {
  const owner = document.getElementById('account-navigation')?.dataset.userId || 'guest';
  const key = `pathfinder:saved-filters:${owner}`;
  const fields = ['q', 'major_filter', 'major_name', 'cipcode', 'favorite_major', 'degrees', 'school_name', 'state', 'city', 'net_price_max', 'tuition_in_max', 'tuition_out_max', 'acceptance_min', 'acceptance_max', 'sort'];
  function normalize(value) {
    const source = new URLSearchParams(value);
    const params = new URLSearchParams({view: 'programs', degree_form: '1'});
    for (const field of fields) {
      const values = [...new Set(source.getAll(field).map(value => value.trim()).filter(Boolean))].sort();
      for (const value of values) params.append(field, value);
    }
    return params.toString();
  }
  function read() {
    const raw = JSON.parse(window.localStorage.getItem(key) || '[]');
    if (!Array.isArray(raw)) throw new Error('Invalid saved filters.');
    return raw.filter(item => item && typeof item.params === 'string' && typeof item.savedAt === 'string')
      .map(item => ({params: normalize(item.params), savedAt: item.savedAt}));
  }
  window.SavedFilterStore = {
    read,
    save(params) {
      const normalized = normalize(params);
      const items = read();
      const existing = items.find(item => item.params === normalized);
      if (existing) return {item: existing, duplicate: true};
      if (items.length >= 50) throw new Error('You have 50 saved filter sets. Remove one in Saved filters before saving another.');
      const item = {params: normalized, savedAt: new Date().toISOString()};
      window.localStorage.setItem(key, JSON.stringify([item, ...items]));
      return {item, duplicate: false};
    },
    remove(params) { window.localStorage.setItem(key, JSON.stringify(read().filter(item => item.params !== params))); },
    url(params, base = '/explore') {
      const url = new URL(base, window.location.origin);
      url.search = normalize(params); url.hash = ''; return url.toString();
    },
    key,
  };
})();
