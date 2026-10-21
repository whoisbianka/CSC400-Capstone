(function (root) {
  const numeric = value => typeof value === "number" && Number.isFinite(value);
  function highlights(values, direction) {
    const labels = values.map(() => '');
    const reported = values.filter(numeric);
    if (!['higher', 'lower'].includes(direction) || reported.length < 2) return labels;
    const best = direction === 'higher' ? Math.max(...reported) : Math.min(...reported);
    const tied = reported.filter(value => value === best).length > 1;
    const label = tied ? 'Tie for best' : direction === 'higher' ? 'Highest earnings' : 'Lowest cost';
    return values.map(value => numeric(value) && value === best ? label : '');
  }
  function format(value, type) {
    if (value === null || value === undefined || value === '') return 'Not reported';
    if (type === 'range') return Array.isArray(value) && value.length === 2 && value.every(numeric)
      ? `${value[0]}–${value[1]}` : 'Not reported';
    if (type === 'text') return String(value);
    if (!numeric(value)) return 'Not reported';
    if (type === 'money') return new Intl.NumberFormat('en-US', {style:'currency', currency:'USD', maximumFractionDigits:0}).format(value);
    if (type === 'percent') return new Intl.NumberFormat('en-US', {style:'percent', maximumFractionDigits:2}).format(value);
    return new Intl.NumberFormat('en-US').format(value);
  }
  const api = {highlights, format};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ComparisonValues = api;
})(globalThis);
