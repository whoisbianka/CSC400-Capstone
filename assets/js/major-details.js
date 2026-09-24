(() => {
  'use strict';
  const areaKey = new URLSearchParams(window.location.search).get('area');
  const areas = window.majorAreas;
  const area = areas && Object.prototype.hasOwnProperty.call(areas, areaKey) ? areas[areaKey] : null;
  if (!area) {
    document.getElementById('area-title').textContent = 'Choose a major category';
    document.getElementById('area-overview').textContent = 'Return to Explore Majors and select a category to see its page.';
    document.querySelector('.preview-label').hidden = true;
    document.querySelector('.detail-nav').hidden = true;
    document.getElementById('colleges').hidden = true;
    document.getElementById('insights').hidden = true;
    return;
  }
  document.title = `${area.title} | Degree Path Explorer`;
  document.getElementById('area-title').textContent = area.title;
  document.getElementById('area-overview').textContent = area.overview;
  const element = (tag, text) => {
    const node = document.createElement(tag);
    node.textContent = text;
    return node;
  };
  const addLink = (card, url, label) => {
    try {
      const parsed = new URL(url);
      if (!['https:', 'http:'].includes(parsed.protocol)) return;
      const link = element('a', label);
      link.href = parsed.href;
      card.append(link);
    } catch { /* Incomplete dataset links are omitted. */ }
  };
  const render = (id, items, populate) => {
    if (!Array.isArray(items) || !items.length) return;
    const container = document.getElementById(id);
    container.replaceChildren();
    items.forEach(item => {
      const card = document.createElement('article');
      card.className = 'detail-card';
      populate(card, item);
      container.append(card);
    });
  };
  render('college-list', area.colleges, (card, college) => {
    card.append(element('h3', college.name), element('p', college.program), element('p', college.location));
    addLink(card, college.url, 'View program →');
  });
  render('insight-list', area.insights, (card, insight) => {
    card.append(element('h3', insight.title), element('p', insight.description));
    addLink(card, insight.sourceUrl, insight.sourceLabel || 'View source →');
  });
  if (area.colleges.length && area.insights.length) document.querySelector('.preview-label').hidden = true;
})();
