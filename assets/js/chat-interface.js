(() => {
  'use strict';
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-message');
  const send = document.getElementById('send-message');
  const messages = document.getElementById('messages');
  const feedback = document.getElementById('chat-feedback');
  const update = () => { send.disabled = !input.value.trim(); };
  input.addEventListener('input', update);
  document.querySelectorAll('[data-prompt]').forEach(button => {
    button.addEventListener('click', () => {
      input.value = button.dataset.prompt;
      update();
      input.focus();
    });
  });
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      if (input.value.trim()) form.requestSubmit();
    }
  });
  form.addEventListener('submit', event => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    const message = document.createElement('article');
    message.className = 'message user';
    const author = document.createElement('p');
    author.className = 'message-author';
    author.textContent = 'You · Local preview';
    const content = document.createElement('p');
    content.textContent = text;
    message.append(author, content);
    messages.append(message);
    input.value = '';
    update();
    feedback.textContent = 'Message added to this preview only. The chatbot is not connected, so no response is available yet.';
    messages.scrollTop = messages.scrollHeight;
    input.focus();
  });
})();
