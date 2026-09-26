/* Local deterministic demo matching; replace with backend search during integration. */
(function (root) {
  'use strict';
  const normalize = text =>
    String(text)
      .toLowerCase()
      .replace(/[^a-z0-9 ]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  const contains = (text, phrase) => (' ' + text + ' ').includes(' ' + normalize(phrase) + ' ');
  function search(question, programs) {
    const text = normalize(question);
    const terms = [
      ...new Set(programs.flatMap(p => [p.major, ...p.keywords, ...p.careers]).map(normalize))
    ]
      .filter(term => contains(text, term))
      .filter(
        (term, _, all) => !all.some(other => other !== term && contains(normalize(other), term))
      );
    const namedColleges = [...new Set(programs.map(p => p.college))].filter(name =>
      contains(text, name)
    );
    const states =
      'Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming'.split(
        '|'
      );
    const locations = states.filter(state => contains(text, state));
    // Avoid matching Virginia inside West Virginia.
    const locationsExact = locations.filter(
      state => !locations.some(other => other !== state && other.includes(state))
    );
    programs.forEach(p => {
      if (
        p.stateCode &&
        new RegExp('\\b' + p.stateCode + '\\b').test(question) &&
        !locationsExact.includes(p.state)
      )
        locationsExact.push(p.state);
    });
    const cost = question.match(
      /(?:under|below|less than|up to|at most)\s*\$?([0-9][0-9,]*(?:\.[0-9]+)?)\s*(k|thousand)?/i
    );
    const budget = cost ? Number(cost[1].replace(/,/g, '')) * (cost[2] ? 1000 : 1) : null;
    const inclusive = cost && /up to|at most/i.test(cost[0]);
    const formats = ['Online', 'Campus', 'Hybrid'].filter(f => contains(text, f));
    const types = ['Public', 'Private'].filter(t => contains(text, t));
    const filters = [...locationsExact, ...formats, ...types];
    if (budget !== null)
      filters.push(
        `${inclusive ? 'At most' : 'Under'} $${budget.toLocaleString('en-US')} annual demo tuition`
      );
    const browse =
      /\b(all|any|show|list|browse)\b/.test(text) &&
      /\b(programs|majors|colleges|options)\b/.test(text);
    if (!terms.length && !namedColleges.length && !filters.length && !browse)
      return {
        rows: [],
        filters,
        terms,
        message:
          'I could not match that question to the demo dataset. Try a subject such as computer science, nursing, business, or psychology.'
      };
    const matches = programs
      .map(p => ({
        ...p,
        matched: terms.filter(t =>
          [p.major, ...p.keywords, ...p.careers].some(value => normalize(value) === t)
        )
      }))
      .filter(
        p =>
          (!terms.length || p.matched.length) &&
          (!namedColleges.length || namedColleges.includes(p.college)) &&
          (!locationsExact.length || locationsExact.includes(p.state)) &&
          (!formats.length || formats.includes(p.format)) &&
          (!types.length || types.includes(p.type)) &&
          (budget === null ||
            (p.tuition !== null && (inclusive ? p.tuition <= budget : p.tuition < budget)))
      )
      .sort(
        (a, b) =>
          b.matched.length - a.matched.length || (a.tuition ?? Infinity) - (b.tuition ?? Infinity)
      );
    return {
      rows: matches,
      filters,
      terms,
      message: matches.length
        ? `${matches.length} demo program${matches.length === 1 ? '' : 's'} matched.`
        : 'No demo programs match these subjects and filters. Try removing a location, format, or tuition limit.'
    };
  }
  root.demoSearch = search;
})(typeof window !== 'undefined' ? window : globalThis);
