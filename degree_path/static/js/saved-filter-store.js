/* Database-backed saved searches. The server owns authentication and major resolution. */
(() => {
  const account = document.getElementById('account-navigation');
  const owner = account?.dataset.userId || '';
  const numericFields = ['net_price_max','tuition_in_max','tuition_out_max','acceptance_min','acceptance_max','satmt','satvr','satwr','actmt','acten','actwr'];
  async function request(path, method = 'GET', body) {
    if (!owner) throw new Error('Sign in to save and restore searches.');
    const response = await fetch(path, {
      method, credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':account.dataset.csrf,'X-App-User-ID':owner},
      ...(body === undefined ? {} : {body:JSON.stringify(body)}),
    });
    let result;
    try { result = await response.json(); } catch { throw new Error('Saved searches are unavailable. Please reload and retry.'); }
    if (!response.ok) throw new Error(result.error || 'Unable to access saved searches. Please retry.');
    return result;
  }
  function bodyFor(value) {
    const params = new URLSearchParams(value);
    const list = key => [...new Set(params.getAll(key).map(v=>v.trim()).filter(Boolean))].sort();
    const kind = params.get('view') === 'majors' ? 'majors' : 'programs';
    const body = {search_text:params.get('q') || '', sort_order:params.get('sort') || (kind === 'majors' ? 'name_asc' : 'school_asc')};
    if (kind === 'majors') {
      body.majors = list('majors'); body.saved = params.get('saved') === '1'; body.recs = params.get('recs') === '1';
      if (params.get('earnings_min')?.trim()) body.earnings_min = Number(params.get('earnings_min'));
    } else {
      const mode = params.get('major_filter') || 'all';
      body.majors = mode === 'favorites' ? list('favorite_major') : mode === 'selected' ? list('majors') : mode === 'name' ? [params.get('major_name')?.trim() || params.get('cipcode') || ''].filter(Boolean) : [];
      if (mode !== 'all' && !body.majors.length) throw new Error('Select at least one major, or choose All majors before saving.');
      body.colleges = list('school_name'); body.states = list('state').map(v=>v.toUpperCase());
      body.degrees = [...new Set((params.has('degree_form') ? params.getAll('degree') : (params.get('degrees') || '').split(',')).filter(Boolean))].sort().join(',');
      for (const key of numericFields) if (params.get(key)?.trim()) body[key] = Number(params.get(key));
    }
    return {kind,body};
  }
  window.SavedFilterStore = {
    async read() {
      const rows = await Promise.all(['programs','majors'].map(async kind => {
        const result = await request('/api/saved-searches/' + kind);
        return result.searches.map(item=>({...item,kind}));
      }));
      return rows.flat();
    },
    async save(value) { const {kind,body} = bodyFor(value); const result = await request('/api/saved-searches/' + kind,'POST',body); return {...result,duplicate:!result.created}; },
    async remove(item) { return request('/api/saved-searches/' + item.kind + '/' + item.id,'DELETE'); },
    url(item) { return '/saved-searches/' + item.kind + '/' + item.id + '/apply'; },
    bodyFor,
  };
})();
