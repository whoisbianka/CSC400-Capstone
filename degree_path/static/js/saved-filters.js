(() => {
  const panel = document.getElementById('saved-filters-panel');
  if (!panel) return;
  const list = document.getElementById('saved-filter-cards');
  const status = document.getElementById('saved-filters-status');
  const count = document.getElementById('saved-filters-tab-count');
  const labels = {search_text:'Search',majors:'Majors',colleges:'Colleges',states:'States',degrees:'Degrees',saved:'My saved majors',recs:'My recommended majors',earnings_min:'Minimum earnings',net_price_max:'Maximum yearly cost after aid',tuition_in_max:'Maximum in-state tuition',tuition_out_max:'Maximum out-of-state tuition',acceptance_min:'Minimum acceptance rate',acceptance_max:'Maximum acceptance rate',satmt:'SAT Math',satvr:'SAT Reading',satwr:'SAT Writing',actmt:'ACT Math',acten:'ACT English',actwr:'ACT Writing',sort_order:'Sort by'};
  const sorts = {name_asc:'Major name A–Z',name_desc:'Major name Z–A',school_asc:'School name A–Z',school_desc:'School name Z–A',earnings_desc:'Highest reported earnings',earnings_asc:'Lowest reported earnings',programs_desc:'Most programs',net_price_asc:'Lowest cost after aid',tuition_in_asc:'Lowest in-state tuition',tuition_out_asc:'Lowest out-of-state tuition'};
  let version = 0;
  function node(tag, className, text) { const el = document.createElement(tag); el.className = className; if (text !== undefined) el.textContent = text; return el; }
  async function render() {
    const current = ++version;
    status.textContent = 'Loading saved searches…';
    try {
      const items = await window.SavedFilterStore.read();
      if (current !== version) return;
      count.textContent = String(items.length); list.replaceChildren();
      status.textContent = items.length ? '' : 'No saved searches yet. Choose filters in Explore, then press Save search.';
      for (const item of items) {
        const card = node('article','saved-filter-card');
        const title = (item.kind === 'majors' ? 'Major search' : 'Program search') + (item.search_text ? ': ' + item.search_text : '');
        card.append(node('h3','',title));
        const facts = node('dl','saved-filter-facts');
        for (const [key,label] of Object.entries(labels)) {
          const value = item[key];
          if (value == null || value === '' || value === false || (Array.isArray(value) && !value.length)) continue;
          let display = Array.isArray(value) ? value.join(', ') : value === true ? 'Yes' : String(value);
          if (key === 'majors') display = item.major_names?.join(', ') || `${value.length} selected majors`;
          if (key === 'sort_order') display = sorts[value] || value;
          if (key === 'degrees') display = value.split(',').map(v=>v === '2' ? 'Associate degree' : v === '3' ? 'Bachelor’s degree' : v).join(', ');
          if (key.startsWith('acceptance')) display += '%';
          if (['earnings_min','net_price_max','tuition_in_max','tuition_out_max'].includes(key)) display = new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(Number(value));
          const fact=node('div',''); fact.append(node('dt','',label),node('dd','',display)); facts.append(fact);
        }
        const actions=node('div','saved-filter-actions');
        const apply=node('a','primary-link','Apply filters →'); apply.href=window.SavedFilterStore.url(item);
        const remove=node('button','secondary-button','Remove'); remove.type='button'; remove.setAttribute('aria-label','Remove '+title);
        remove.addEventListener('click',async()=>{
          remove.disabled=true;
          try {
            await window.SavedFilterStore.remove(item);
            if (current !== version) return;
            await render();
            (list.querySelector('button') || document.getElementById('saved-filters-tab'))?.focus();
          } catch(error) { if(current === version) { status.textContent=error.message; remove.disabled=false; } }
        });
        actions.append(apply,remove);card.append(facts,actions);list.append(card);
      }
    } catch(error) {
      if(current !== version) return;
      list.replaceChildren();status.textContent=error.message || 'Unable to load saved searches.';count.textContent='—';
    }
  }
  window.SavedFilters={render};
  window.addEventListener('pageshow',event=>{if(event.persisted) render();});
  render();
})();
