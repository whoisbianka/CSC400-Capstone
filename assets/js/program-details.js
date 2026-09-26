(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const text = (value, fallback = 'Not available in the current dataset.') => typeof value === 'string' && value.trim() ? value : fallback;
  function list(id, values) {
    const entries = Array.isArray(values) ? values.filter(v => typeof v === 'string' && v.trim()) : [];
    (entries.length ? entries : ['Not available in the current dataset.']).forEach(value => {
      const li = document.createElement('li'); li.textContent = value; $(id).append(li);
    });
  }
  function library() {
    const query = $('program-search').value.trim().toLowerCase();
    const records = window.programCatalog.getPrograms().filter(p => [p.major,p.college,p.state].join(' ').toLowerCase().includes(query));
    $('library-count').textContent = `${records.length} programs` + (window.programCatalog.isDemo() ? ' · Fictional demo data' : '');
    $('library-results').replaceChildren();
    records.forEach(program => {
      const link = document.createElement('a'); link.className = 'library-card';
      link.href = '#' + encodeURIComponent(JSON.stringify({program, demo:window.programCatalog.isDemo()}));
      const title = document.createElement('h2'); title.textContent = program.major;
      const college = document.createElement('p'); college.textContent = program.college;
      const meta = document.createElement('p'); meta.textContent = [program.state,program.format].filter(Boolean).join(' · ');
      link.append(title,college,meta); $('library-results').append(link);
    });
    if (!records.length) { const empty = document.createElement('p'); empty.textContent = 'No matching programs. Try another major or college.'; $('library-results').append(empty); }
  }
  function render() {
    $('program-content').hidden = true;
    $('program-library').hidden = !!location.hash;
    $('all-programs').hidden = !location.hash;
    ['program-facts','program-keywords','program-careers','program-courses'].forEach(id => $(id).replaceChildren());
    if (!location.hash) {
      document.title = 'Major Details | Degree Path Explorer';
      $('program-title').textContent = 'Explore major details';
      $('college-name').textContent = 'Browse available programs and open a major to learn more.';
      $('record-label').textContent = 'Your workspace'; library(); return;
    }
    try {
    const record = JSON.parse(decodeURIComponent(location.hash.slice(1)));
    const p = record.program;
    if (!p || typeof p.major !== 'string' || typeof p.college !== 'string') throw Error('Invalid record');
    document.title = `${p.major} at ${p.college} | Degree Path Explorer`;
    $('program-title').textContent = p.major;
    $('college-name').textContent = p.college;
    $('record-label').textContent = record.demo ? 'Fictional demo program' : 'Program details';
    $('record-notice').textContent = record.demo ? 'Demo data only: this college, program, and tuition are fictional test fixtures.' : 'Snapshot of the program record selected in chat. Confirm current requirements and costs with the college.';
    const tuition = typeof p.tuition === 'number' && Number.isFinite(p.tuition) && p.tuition >= 0 ? '$' + p.tuition.toLocaleString('en-US') : 'Not available';
    [['College',p.college],['Location',p.state],['College type',p.type],['Study format',p.format],['Annual tuition (USD)',tuition],['Degree',p.degree],['Duration',p.duration]].forEach(([label,value]) => {
      const group = document.createElement('div'), dt = document.createElement('dt'), dd = document.createElement('dd');
      dt.textContent = label; dd.textContent = text(value); group.append(dt,dd); $('program-facts').append(group);
    });
    $('program-overview').textContent = text(p.overview, 'A detailed major description will appear here when it is included in the program dataset.');
    list('program-keywords',p.keywords); list('program-careers',p.careers); list('program-courses',p.courses);
    $('program-admissions').textContent = text(p.admissions);
    $('program-outlook').textContent = text(p.outlook);
    $('program-website').textContent = 'No program website provided.';
    if (typeof p.url === 'string') {
      try {
        const url = new URL(p.url);
        if (['https:','http:'].includes(url.protocol)) {
          const link = document.createElement('a'); link.href = url.href; link.textContent = 'Visit program website';
          $('program-website').replaceChildren(link);
        }
      } catch { /* Missing or unsafe URLs remain unavailable. */ }
    }
    $('program-content').hidden = false;
  } catch {
    $('program-title').textContent = 'Program unavailable';
    $('college-name').textContent = 'This link is incomplete or invalid. Return to chat and open a matching program.';
  }
  }
  $('program-search').addEventListener('input', library);
  window.addEventListener('hashchange', () => { render(); document.querySelector('.program-workspace').scrollTop = 0; $('program-title').setAttribute('tabindex','-1'); $('program-title').focus(); });
  window.addEventListener('program-catalog-updated', library);
  render();
})();
