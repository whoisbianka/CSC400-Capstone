/* Integration boundary: pass normalized API records to programCatalog.setPrograms.
   No API credentials or database access belong in this browser module. */
(() => {
  let programs = [];
  let demo = true;
  function setPrograms(records, options = {}) {
    if (!Array.isArray(records)) throw new TypeError('Program records must be an array');
    programs = records.filter(p => p && typeof p.college === 'string' && p.college.trim() && typeof p.major === 'string' && p.major.trim()).map(p => ({
      ...p, college:p.college.trim(), major:p.major.trim(),
      state: typeof p.state === 'string' ? p.state : '', stateCode: typeof p.stateCode === 'string' ? p.stateCode : '',
      type: typeof p.type === 'string' ? p.type : '', format: typeof p.format === 'string' ? p.format : '',
      tuition: typeof p.tuition === 'number' && Number.isFinite(p.tuition) && p.tuition >= 0 ? p.tuition : null,
      keywords:Array.isArray(p.keywords) ? p.keywords.filter(k => typeof k === 'string') : [],
      careers:Array.isArray(p.careers) ? p.careers.filter(k => typeof k === 'string') : []
    }));
    demo = options.demo !== false;
    window.dispatchEvent(new Event('program-catalog-updated'));
  }
  function suggestions() {
    const majors = [...new Set(programs.map(p => p.major))];
    const prompts = majors.slice(0,3).map(major => `Which colleges offer ${major}?`);
    const online = programs.find(p => p.format.toLowerCase() === 'online');
    if (online) prompts.push(`Show online ${online.major} programs`);
    else if (programs.find(p => p.state)) prompts.push(`Show programs in ${programs.find(p => p.state).state}`);
    else if (majors[3]) prompts.push(`Which colleges offer ${majors[3]}?`);
    return [...new Set(prompts)];
  }
  window.programCatalog = {setPrograms, suggestions, getPrograms: () => programs, isDemo: () => demo};
  setPrograms(window.demoPrograms || [], {demo:true});
})();
