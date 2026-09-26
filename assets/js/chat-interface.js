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
    const author = node('p', 'Degree Path Assistant · Demo results'); author.className = 'message-author';
    item.append(author, node('p', result.message));
    const disclaimer = node('p', 'Fictional test data — not real colleges, rankings, costs, or recommendations. Career examples may require additional credentials.');
    disclaimer.className = 'demo-disclaimer'; item.append(disclaimer);
    if (result.filters.length) item.append(node('p', 'Filters: ' + result.filters.join(' · ')));
    if (result.terms.length) item.append(node('p', 'Matched topics: ' + result.terms.join(', ')));
    if (result.rows.length) {
      const wrap = node('div', ''); wrap.className = 'results-scroll'; wrap.tabIndex = 0;
      wrap.setAttribute('role', 'region'); wrap.setAttribute('aria-label', 'Program comparison table; scroll horizontally for more columns');
      const table = node('table', ''); table.className = 'results-table';
      table.append(node('caption', 'Matching majors and colleges · Demo dataset'));
      const head = node('thead', ''); const headers = node('tr', '');
      ['Major', 'College', 'Location', 'Format', 'Annual tuition (demo)', 'Career examples', 'Why shown'].forEach(label => { const th = node('th',label); th.scope = 'col'; headers.append(th); });
      head.append(headers); table.append(head); const body = node('tbody','');
      result.rows.forEach(program => {
        const row = node('tr','');
        const major = node('th', program.major); major.scope = 'row'; row.append(major);
        [program.college + ' · ' + program.type, program.state, program.format, '$' + program.tuition.toLocaleString('en-US'), program.careers.join(', '), program.matched.length ? program.matched.join(', ') : 'Matches your filters'].forEach(value => row.append(node('td',value)));
        body.append(row);
      });
      table.append(body); wrap.append(table); item.append(wrap);
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
      ? 'Demo data only · Colleges, programs, and tuition figures are fictional. Matching uses keywords and filters, not a live chatbot.'
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
      const result = window.demoSearch(value, window.demoPrograms);
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
  document.querySelectorAll('[data-query]').forEach(button => button.addEventListener('click', () => {
    $('chat-message').value = button.dataset.query; $('send-message').disabled = false; $('chat-message').focus();
  }));
  progress(); showAsk();
})();
