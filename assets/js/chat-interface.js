(() => {
  'use strict';
  // Replace these sample questions with the chatbot's questions during integration.
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
    $('progress-label').textContent = `${count()} of ${questions.length} answers saved${storageAvailable ? ' in this tab' : ' on this page'}`;
    $('review-answers').hidden = !count();
  }
  function bubble(text, user = false) {
    const item = node('article', ''); item.className = 'message ' + (user ? 'user' : 'assistant');
    const author = node('p', user ? 'Your answer' : 'Degree Path Assistant'); author.className = 'message-author';
    item.append(author, node('p', text)); $('messages').append(item);
  }
  function transcript() {
    $('messages').replaceChildren();
    questions.forEach(q => { if (answers[q.id]) { bubble(q.text); bubble(answers[q.id], true); } });
  }
  function showQuestion(index, isEdit = false, focus = false) {
    current = index; editing = isEdit;
    $('answer-review').hidden = true; $('chat-form').hidden = false;
    transcript(); bubble(`${isEdit ? 'Edit answer' : 'Question'} ${index + 1} of ${questions.length}: ${questions[index].text}`);
    $('answer-label').textContent = questions[index].text;
    $('chat-message').value = answers[questions[index].id] || '';
    $('send-message').textContent = isEdit ? 'Save changes' : 'Save & continue';
    $('send-message').disabled = !$('chat-message').value.trim();
    progress(); $('messages').scrollTop = $('messages').scrollHeight;
    if (focus) $('chat-message').focus();
  }
  function review(focus = true) {
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
    $('finish-answers').textContent = count() === questions.length ? 'Finish review' : 'Continue questions';
    progress(); if (focus) $('review-title').focus();
  }
  $('chat-message').addEventListener('input', () => { $('send-message').disabled = !$('chat-message').value.trim(); });
  $('chat-message').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); if ($('chat-message').value.trim()) $('chat-form').requestSubmit(); }
  });
  $('chat-form').addEventListener('submit', e => {
    e.preventDefault(); const value = $('chat-message').value.trim();
    if (!value || current === null) return;
    answers[questions[current].id] = value; save();
    $('chat-feedback').textContent = storageAvailable ? 'Answer saved in this browser tab.' : 'Answer kept on this page only.';
    const next = questions.findIndex(q => !answers[q.id]);
    if (editing || next === -1) review(); else showQuestion(next, false, true);
  });
  $('review-answers').addEventListener('click', () => review());
  $('finish-answers').addEventListener('click', () => {
    const next = questions.findIndex(q => !answers[q.id]);
    if (next !== -1) return showQuestion(next, false, true);
    $('chat-feedback').textContent = 'Review complete. Your answers are ready for this preview. Database submission and chatbot recommendations will be connected later.';
  });
  $('restart-answers').addEventListener('click', () => {
    if (count() && !window.confirm('Clear your saved answers and start again?')) return;
    answers = {}; save(); $('chat-feedback').textContent = 'Previous answers cleared.'; showQuestion(0, false, true);
  });
  save();
  const next = questions.findIndex(q => !answers[q.id]);
  if (next === -1) review(false); else showQuestion(next);
})();
