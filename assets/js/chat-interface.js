(() => {
  'use strict';
  // Our questions will replace these sample questions.
  const questions = [
    { id: 'interests', text: 'What subjects or activities do you enjoy most?' },
    { id: 'strengths', text: 'What do you feel you are good at? Think about skills or strengths you enjoy using.' },
    { id: 'work_style', text: 'What kind of work interests you: working with people, technology, ideas, or hands-on projects?' },
    { id: 'goals', text: 'What matters most to you in a future career?' },
    { id: 'curiosity', text: 'Are there any majors or careers you would like to explore? It is okay to be unsure.' }
  ];
  const $ = id => document.getElementById(id);
  const key = 'degree-path-questionnaire-v1';
  let answers = {};
  let storageAvailable = true;
  try {
    const saved = JSON.parse(sessionStorage.getItem(key) || '{}');
    questions.forEach(q => {
      if (saved && typeof saved[q.id] === 'string' && saved[q.id].trim()) answers[q.id] = saved[q.id].slice(0, 2000);
    });
  } catch { storageAvailable = false; }
  let mode = 'ask';
  let queryDraft = '';
  let guidedDraft = null;
  const queryMessages = [];
  let current = null;
  let editing = false;
  const count = () => Object.keys(answers).length;
  const node = (tag, text) => { const n = document.createElement(tag); n.textContent = text; return n; };
  function save() {
    try { sessionStorage.setItem(key, JSON.stringify(answers)); }
    catch { storageAvailable = false; }
    if (!storageAvailable) $('connection-note').textContent = 'Sample questionnaire. Browser storage is unavailable: answers remain only on this page until it is refreshed. Nothing is sent to a database.';
  }
  function progress() {
    $('answer-progress').max = questions.length;
    $('answer-progress').value = count();
    $('review-answers').hidden = !count();
  }
  function bubble(text, user = false) {
    const item = node('article', ''); item.className = 'message ' + (user ? 'user' : 'assistant');
    const author = node('p', user ? 'You' : 'Degree Path Assistant'); author.className = 'message-author';
    item.append(author, node('p', text)); $('messages').append(item);
  }
  function renderResults(result, target = $('messages')) {
    const item = node('article', ''); item.className = 'message assistant result-message';
    const author = node('p', result.demo ? 'Degree Path Assistant · Demo results' : 'Degree Path Assistant · Program results'); author.className = 'message-author';
    item.append(author, node('p', result.message));
    const disclaimer = node('p', result.demo ? 'Fictional test data — not real colleges, rankings, costs, or recommendations.' : 'Results from the connected program catalog. Check program requirements and costs with the college.');
    disclaimer.className = 'demo-disclaimer'; item.append(disclaimer);
    if (result.filters.length) item.append(node('p', 'Filters: ' + result.filters.join(' · ')));
    if (result.terms.length) item.append(node('p', 'Matched topics: ' + result.terms.join(', ')));
    if (result.rows.length) {
      const colleges = new Map();
      result.rows.forEach(program => {
        const key = program.college + '|' + program.state;
        if (!colleges.has(key)) colleges.set(key, []);
        colleges.get(key).push(program);
      });
      const count = node('p', `${colleges.size} colleges · ${result.rows.length} related programs`); count.className = 'result-count'; item.append(count);
      colleges.forEach(programs => {
        const first = programs[0];
        const card = node('article', ''); card.className = 'college-result-card';
        const header = node('div',''); header.className = 'college-card-header';
        const emblem = node('span', first.college.split(' ').map(w => w[0]).slice(0,2).join('')); emblem.className = 'college-emblem'; emblem.setAttribute('aria-hidden','true');
        const title = node('div',''); title.append(node('h3',first.college),node('p',[first.state,first.type].filter(Boolean).join(' · ') || 'Location and college type not provided'));
        header.append(emblem,title); card.append(header);
        const tagList = node('div',''); tagList.className = 'major-tags';
        [...new Set(programs.map(p => p.major))].forEach(major => tagList.append(node('span',major))); card.append(tagList);
        const stats = node('dl',''); stats.className = 'college-stats';
        const costs = programs.map(p => p.tuition).filter(p => p !== null);
        const tuition = costs.length ? (Math.min(...costs) === Math.max(...costs) ? '$' + Math.min(...costs).toLocaleString('en-US') : '$' + Math.min(...costs).toLocaleString('en-US') + '–$' + Math.max(...costs).toLocaleString('en-US')) : 'Not available';
        [['Annual tuition' + (result.demo ? ' · demo' : ''),tuition],['Study format',[...new Set(programs.map(p => p.format).filter(Boolean))].join(' / ') || 'Not available']].forEach(([label,value]) => { const group = node('div',''); group.append(node('dt',label),node('dd',value)); stats.append(group); });
        card.append(stats);
        const matches = [...new Set(programs.flatMap(p => p.matched))];
        const why = node('p',matches.length ? 'Related to: ' + matches.join(', ') : 'Matches the filters in your question.'); why.className = 'match-reason'; card.append(why);
        const details = node('details',''); details.className = 'program-details'; details.append(node('summary','View matching program details'));
        programs.forEach(program => {
          const section = node('div',''); section.className = 'program-detail';
          section.append(node('h4',program.major),node('p','Format: ' + (program.format || 'Not available')),node('p','Annual tuition: ' + (program.tuition === null ? 'Not available' : '$' + program.tuition.toLocaleString('en-US'))),node('p','Career examples: ' + (program.careers.join(', ') || 'Not available')));
          details.append(section);
        });
        card.append(details); item.append(card);
      });
    }
    target.append(item);
  }
  function transcript() {
    $('messages').replaceChildren();
    questions.forEach(q => { if (answers[q.id]) { bubble(q.text); bubble(answers[q.id], true); } });
  }
  function activate(nextMode) {
    mode = nextMode;
    $('ask-mode').setAttribute('aria-pressed', String(mode === 'ask'));
    $('guided-mode').setAttribute('aria-pressed', String(mode === 'guided'));
    $('guided-progress').hidden = mode !== 'guided';
    $('query-starters').hidden = mode !== 'ask';
    $('major-results').hidden = true;
    $('chat-feedback').textContent = '';
    $('connection-note').textContent = mode === 'ask'
      ? (window.programCatalog.isDemo() ? 'Demo data only · Colleges, programs, and tuition figures are fictional. Matching uses keywords and filters, not a live chatbot.' : 'Program catalog loaded · Keyword and filter search preview.')
      : storageAvailable ? 'Optional sample questions · Answers saved in this browser tab for this session, not to your account.' : 'Optional sample questions · Answers stay on this page only; browser storage is unavailable.';
    $('restart-answers').textContent = mode === 'ask' ? 'Clear conversation' : 'Restart questionnaire';
  }
  function showAsk(focus = false) {
    if (mode === 'guided' && current !== null && !$('chat-form').hidden) guidedDraft = {index:current, editing, text:$('chat-message').value};
    activate('ask'); current = null;
    $('answer-review').hidden = true; $('chat-form').hidden = false;
    $('messages').replaceChildren();
    queryMessages.forEach(message => message.result ? renderResults(message.result) : bubble(message.text, message.user));
    $('answer-label').textContent = 'Ask about majors, colleges, or careers';
    $('chat-message').placeholder = 'What would you like to know?';
    $('chat-message').value = queryDraft;
    $('send-message').textContent = 'Send';
    $('send-message').disabled = !queryDraft.trim();
    if (focus) $('chat-message').focus();
  }
  function startGuided() {
    if (mode === 'ask') queryDraft = $('chat-message').value;
    if (guidedDraft) {
      const draft = guidedDraft; showQuestion(draft.index, draft.editing, true);
      $('chat-message').value = draft.text; $('send-message').disabled = !draft.text.trim();
    } else {
      const next = questions.findIndex(q => !answers[q.id]);
      if (next === -1) review(); else showQuestion(next, false, true);
    }
  }
  function showQuestion(index, isEdit = false, focus = false) {
    activate('guided');
    $('chat-message').placeholder = 'Type your answer here…';
    current = index; editing = isEdit;
    $('answer-review').hidden = true; $('chat-form').hidden = false;
    transcript(); bubble(`${isEdit ? 'Edit answer' : 'Question'} ${index + 1} of ${questions.length}: ${questions[index].text}`);
    $('answer-label').textContent = questions[index].text;
    $('chat-message').value = answers[questions[index].id] || '';
    $('send-message').textContent = isEdit ? 'Save changes' : 'Save & continue';
    $('send-message').disabled = !$('chat-message').value.trim();
    progress();
    const scrollArea = $('conversation-body') || $('messages');
    scrollArea.scrollTop = scrollArea.scrollHeight;
    if (focus) $('chat-message').focus();
  }
  function review(focus = true) {
    if (mode === 'ask') queryDraft = $('chat-message').value;
    activate('guided');
    current = null; $('chat-form').hidden = true; $('answer-review').hidden = false;
    transcript(); $('review-list').replaceChildren();
    questions.forEach((q, index) => {
      if (!answers[q.id]) return;
      const item = node('article', ''); item.className = 'review-item';
      const edit = node('button', 'Edit answer'); edit.type = 'button';
      edit.setAttribute('aria-label', `Edit answer ${index + 1}: ${q.text}`);
      edit.addEventListener('click', () => showQuestion(index, true, true));
      item.append(node('h4', q.text), node('p', answers[q.id]), edit); $('review-list').append(item);
    });
    $('finish-answers').textContent = count() === questions.length ? 'Find my major' : 'Continue questions';
    progress(); if (focus) $('review-title').focus();
  }
  $('chat-message').addEventListener('input', () => { $('send-message').disabled = !$('chat-message').value.trim(); });
  $('chat-message').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); if ($('chat-message').value.trim()) $('chat-form').requestSubmit(); }
  });
  $('chat-form').addEventListener('submit', e => {
    e.preventDefault(); const value = $('chat-message').value.trim();
    if (!value) return;
    if (mode === 'ask') {
      queryMessages.push({text:value, user:true}); bubble(value, true);
      const result = window.demoSearch(value, window.programCatalog.getPrograms());
      result.demo = window.programCatalog.isDemo();
      if (!result.demo) result.message = result.rows.length ? `${result.rows.length} matching programs found.` : 'No matching programs found. Try another major or broaden your filters.';
      queryMessages.push({result}); renderResults(result);
      queryDraft = ''; $('chat-message').value = ''; $('send-message').disabled = true;
      $('conversation-body').scrollTop = $('conversation-body').scrollHeight;
      $('chat-message').focus(); return;
    }
    if (current === null) return;
    guidedDraft = null;
    answers[questions[current].id] = value; save();
    $('chat-feedback').textContent = storageAvailable ? 'Answer saved in this browser tab.' : 'Answer kept on this page only.';
    const next = questions.findIndex(q => !answers[q.id]);
    if (editing || next === -1) review(); else showQuestion(next, false, true);
  });
  $('review-answers').addEventListener('click', () => review());
  $('finish-answers').addEventListener('click', () => {
    const next = questions.findIndex(q => !answers[q.id]);
    if (next !== -1) return showQuestion(next, false, true);
    $('major-results').hidden = false; $('results-title').focus();
  });
  $('restart-answers').addEventListener('click', () => {
    if (mode === 'ask') {
      if (queryMessages.length && !window.confirm('Clear this conversation?')) return;
      queryMessages.length = 0; queryDraft = ''; showAsk(true); return;
    }
    if (count() && !window.confirm('Clear your saved answers and start again?')) return;
    answers = {}; guidedDraft = null; save(); $('chat-feedback').textContent = 'Previous answers cleared.'; showQuestion(0, false, true);
  });
  save();
  $('ask-mode').addEventListener('click', () => { if (mode !== 'ask') showAsk(true); });
  $('guided-mode').addEventListener('click', () => { if (mode !== 'guided') startGuided(); });
  function refreshSuggestions() {
    if (mode === 'ask') $('connection-note').textContent = window.programCatalog.isDemo() ? 'Demo data only · Colleges, programs, and tuition figures are fictional.' : 'Program catalog loaded · Keyword and filter search preview.';
    const container = $('query-starters'); container.replaceChildren();
    const suggestions = window.programCatalog.suggestions();
    suggestions.forEach(prompt => {
      const button = node('button', prompt); button.type = 'button';
      button.addEventListener('click', () => { $('chat-message').value = prompt; $('send-message').disabled = false; $('chat-message').focus(); });
      container.append(button);
    });
    if (!suggestions.length) container.append(node('p', 'Suggested questions will appear when program data is available.'));
  }
  window.addEventListener('program-catalog-updated', refreshSuggestions);
  refreshSuggestions();
  progress(); showAsk();
})();
