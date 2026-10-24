/* Saved majors use general field-of-study cards, matching Explore majors. */
(() => {
  const container = document.getElementById('saved-major-cards');
  if (!container) return;
  const byId = id => document.getElementById(id);
  const money = value => Number.isFinite(value) ? new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', maximumFractionDigits: 0,
  }).format(value) : 'Not reported';
  function node(tag, className, text) {
    const element = document.createElement(tag);
    element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }
  function card(major) {
    const article = node('article', 'major-catalog-card');
    const body = node('div', 'major-catalog-body');
    const heading = node('div', 'major-catalog-heading');
    const remove = node('button', 'save-major-button', '★ Saved');
    remove.type = 'button';
    remove.dataset.saveMajor = String(major.cipcode);
    remove.dataset.majorName = major.major;
    remove.setAttribute('aria-pressed', 'true');
    remove.setAttribute('aria-label', `Remove ${major.major} from saved majors`);
    heading.append(node('h3', '', major.major), remove);
    const description = major.description || '';
    const excerpt = description.length > 220 ? description.slice(0, 217).trimEnd() + '…' : description;
    body.append(node('p', 'major-catalog-label', 'Field of study'), heading,
      node('p', 'major-description', excerpt || 'A description for this major is not available yet.'),
      node('p', 'major-catalog-count', `${major.program_count} ${major.program_count === 1 ? 'program' : 'programs'} at ${major.school_count} ${major.school_count === 1 ? 'college' : 'colleges'}`));
    const about = node('details', 'major-about');
    about.append(node('summary', '', 'About this major'));
    if (description.length > 220) about.append(node('p', 'major-description', description));
    if (major.description_source) about.append(node('p', 'small-note', `Source: ${major.description_source}`));
    about.append(node('p', 'small-note', `Median of reported program earnings: ${money(major.earnings)}. This summarizes program-level four-year earnings medians and is not graduate-weighted.`));
    body.append(about);
    const footer = node('footer', 'major-catalog-footer');
    const link = node('a', '', 'Find colleges for this major →');
    link.href = `/explore?view=programs&cipcode=${Number(major.cipcode)}`;
    footer.append(link);
    article.append(body, footer);
    return article;
  }
  window.SavedMajors = {
    async refresh(request, favorites) {
      const data = favorites.length ? await request('/api/saved-majors/summary') : {majors: []};
      container.replaceChildren(...data.majors.map(card));
      byId('saved-library').hidden = data.majors.length === 0;
      byId('saved-empty').hidden = data.majors.length !== 0;
      byId('saved-major-count').textContent = `${data.majors.length} saved`;
    },
  };
})();
