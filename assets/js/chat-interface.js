(() => {
  'use strict';

  // =========================================================
  // QUESTIONNAIRE DATA
  // =========================================================

  // Questions shown to users in Guided mode.
  // Each `id` is used to save and retrieve the answer.
  const questions = [
    { id: 'interests', text: 'What subjects or activities do you enjoy most?' },
    {
      id: 'strengths',
      text: 'What do you feel you are good at? Think about skills or strengths you enjoy using.'
    },
    {
      id: 'work_style',
      text: 'What kind of work interests you: working with people, technology, ideas, or hands-on projects?'
    },
    { id: 'goals', text: 'What matters most to you in a future career?' },
    {
      id: 'curiosity',
      text: 'Are there any majors or careers you would like to explore? It is okay to be unsure.'
    }
  ];

  // =========================================================
  // VARIABLES AND STARTING STATE
  // =========================================================

  // Shortcut for finding HTML elements by their id.
  const $ = id => document.getElementById(id);

  // The key used to save answers in this browser tab's sessionStorage.
  const key = 'degree-path-questionnaire-v1';

  // Object that holds the user's questionnaire answers.
  let answers = {};

  // Tracks whether browser storage is available.
  let storageAvailable = true;

  // Load any answers saved earlier in this browser tab.
  try {
    const saved = JSON.parse(sessionStorage.getItem(key) || '{}');

    questions.forEach(q => {
      // Only restore valid, non-empty saved answers.
      if (saved && typeof saved[q.id] === 'string' && saved[q.id].trim()) {
        answers[q.id] = saved[q.id].slice(0, 2000);
      }
    });
  } catch {
    // Storage may be blocked, unavailable, or contain invalid data.
    storageAvailable = false;
  }

  // Tracks whether the user is searching ("ask") or answering questions ("guided").
  let mode = 'ask';

  // Stores unfinished Ask mode text when the user changes modes.
  let queryDraft = '';

  // Stores an unfinished Guided mode answer when the user changes modes.
  let guidedDraft = null;

  // Stores Ask mode user messages and their matching search results.
  const queryMessages = [];

  // Stores the index of the question currently being answered.
  let current = null;

  // True when the user is editing an existing answer.
  let editing = false;

  // Holds the final program-table component after it is created.
  let quizTable = null;

  // Counts how many questionnaire answers currently exist.
  const count = () => Object.keys(answers).length;

  // Creates an HTML element, sets its text, and returns it.
  const node = (tag, text) => {
    const n = document.createElement(tag);
    n.textContent = text;
    return n;
  };

  // =========================================================
  // STORAGE AND PROGRESS FUNCTIONS
  // =========================================================

  // Saves questionnaire answers into this browser tab's sessionStorage.
  function save() {
    try {
      sessionStorage.setItem(key, JSON.stringify(answers));
    } catch {
      storageAvailable = false;
    }

    // Tell the user if answers cannot be saved after a page refresh.
    if (!storageAvailable) {
      $('connection-note').textContent =
        'Sample questionnaire. Browser storage is unavailable: answers remain only on this page until it is refreshed. Nothing is sent to a database.';
    }
  }

  // Updates the Guided mode progress bar and answer count label.
  function progress() {
    $('answer-progress').max = questions.length;
    $('answer-progress').value = count();
    $('progress-label').textContent =
      `${count()} of ${questions.length} questions answered`;
  }

  // =========================================================
  // CHAT DISPLAY FUNCTIONS
  // =========================================================

  // Adds one message bubble to the chat area.
  // When `user` is true, the bubble is shown as a message from the user.
  function bubble(text, user = false) {
    const item = node('article', '');
    item.className = 'message ' + (user ? 'user' : 'assistant');

    const author = node('p', user ? 'You' : 'Degree Path Assistant');
    author.className = 'message-author';

    item.append(author, node('p', text));
    $('messages').append(item);
  }

  // Rebuilds the chat transcript using the questions and saved answers.
  function transcript() {
    $('messages').replaceChildren();

    questions.forEach(q => {
      if (answers[q.id]) {
        bubble(q.text);
        bubble(answers[q.id], true);
      }
    });
  }

  // =========================================================
  // SEARCH RESULT FUNCTIONS
  // =========================================================

  // Displays matching colleges and programs inside the chat area.
  // `result` comes from demoSearch(), and `target` is where results are added.
  function renderResults(result, target = $('messages')) {
    const item = node('article', '');
    item.className = 'message assistant result-message';

    // Show filters selected by the search, if any.
    if (result.filters.length) {
      item.append(node('p', 'Filters: ' + result.filters.join(' · ')));
    }


    // Only create college cards if matching programs exist.
    if (result.rows.length) {
      // Group matching programs by college and state.
      const colleges = new Map();

      result.rows.forEach(program => {
        const key = program.college + '|' + program.state;

        if (!colleges.has(key)) {
          colleges.set(key, []);
        }

        colleges.get(key).push(program);
      });


      // Create one result card for each college.
      colleges.forEach(programs => {
        const first = programs[0];

        const card = node('article', '');
        card.className = 'college-result-card';

        // Build the card header with initials, college name, and location.
        const header = node('div', '');
        header.className = 'college-card-header';

        const emblem = node(
          'span',
          first.college
            .split(' ')
            .map(w => w[0])
            .slice(0, 2)
            .join('')
        );
        emblem.className = 'college-emblem';
        emblem.setAttribute('aria-hidden', 'true');

        const title = node('div', '');
        title.append(
          node('h3', first.college),
          node(
            'p',
            [first.state, first.type].filter(Boolean).join(' · ') ||
              'Location and college type not provided'
          )
        );

        header.append(emblem, title);
        card.append(header);

        // Display each unique major offered by this college in the results.
        const tagList = node('div', '');
        tagList.className = 'major-tags';

        [...new Set(programs.map(p => p.major))].forEach(major => {
          tagList.append(node('span', major));
        });

        card.append(tagList);

        // Build the tuition and study-format information.
        const stats = node('dl', '');
        stats.className = 'college-stats';

        const costs = programs
          .map(p => p.tuition)
          .filter(p => p !== null);

        // Show a single tuition value or a tuition range.
        const tuition = costs.length
          ? Math.min(...costs) === Math.max(...costs)
            ? '$' + Math.min(...costs).toLocaleString('en-US')
            : '$' +
              Math.min(...costs).toLocaleString('en-US') +
              '–$' +
              Math.max(...costs).toLocaleString('en-US')
          : 'Not available';

        [
          ['Annual tuition', tuition],
          [
            'Study format',
            [...new Set(programs.map(p => p.format).filter(Boolean))].join(' / ') ||
              'Not available'
          ]
        ].forEach(([label, value]) => {
          const group = node('div', '');
          group.append(node('dt', label), node('dd', value));
          stats.append(group);
        });

        card.append(stats);

        // Explain why the program matched the user search.
        const matches = [...new Set(programs.flatMap(p => p.matched))];

        const why = node(
          'p',
          matches.length
            ? 'Related to: ' + matches.join(', ')
            : 'Matches the filters in your question.'
        );
        why.className = 'match-reason';

        card.append(why);

        // Create detail-page links for each matching program.
        const details = node('div', '');
        details.className = 'program-details';

        programs.forEach(program => {
          const link = node('a', `View ${program.major} details ↗`);
          link.className = 'program-detail-link';

          // Pass the selected program data to program-details.html.
          link.href =
            'program-details.html#' +
            encodeURIComponent(JSON.stringify({ program, demo: result.demo }));

          link.target = '_blank';
          link.rel = 'noopener noreferrer';

          link.setAttribute(
            'aria-label',
            `View ${program.major} at ${program.college} (opens in a new tab)`
          );

          details.append(link);
        });

        card.append(details);
        item.append(card);
      });
    }

    target.append(item);
  }

  // =========================================================
  // MODE SWITCHING FUNCTIONS
  // =========================================================

  // Updates shared interface elements when changing between Ask and Guided modes.
  function activate(nextMode) {
    mode = nextMode;

    $('query-starters').hidden = mode !== 'ask' || queryMessages.length > 0;
    $('ask-mode').setAttribute('aria-pressed', String(mode === 'ask'));
    $('guided-progress').hidden = mode !== 'guided';
    $('major-results').hidden = true;
    $('messages').hidden = false;
    $('chat-feedback').textContent = '';

    // Show a message that fits the active mode and data source.
    $('connection-note').textContent =
      mode === 'ask'
        ? window.programCatalog.isDemo()
          ? 'Demo data only · Colleges, programs, and tuition figures are fictional. Matching uses keywords and filters, not a live chatbot.'
          : 'Program catalog loaded · Keyword and filter search preview.'
        : storageAvailable
          ? 'Optional sample questions · Answers saved in this browser tab for this session, not to your account.'
          : 'Optional sample questions · Answers stay on this page only; browser storage is unavailable.';
  }

  // Switches to Ask mode and restores saved Ask mode messages.
  function showAsk(focus = false) {
    // Save unfinished Guided mode text before changing modes.
    if (mode === 'guided' && current !== null && !$('chat-form').hidden) {
      guidedDraft = {
        index: current,
        editing,
        text: $('chat-message').value
      };
    }

    activate('ask');

    current = null;
    $('answer-review').hidden = true;
    $('chat-form').hidden = false;
    $('messages').replaceChildren();

    // Restore previous Ask mode messages and search results.
    queryMessages.forEach(message => {
      if (message.result) {
        renderResults(message.result);
      } else {
        bubble(message.text, message.user);
      }
    });

    $('chat-message').placeholder = 'What would you like to know?';
    $('chat-message').value = queryDraft;

    if (focus) {
      $('chat-message').focus();
    }
  }

  // Starts Guided mode with an unfinished answer or the next unanswered question.
  function startGuided() {
    // Save unfinished Ask mode text before changing modes.
    if (mode === 'ask') {
      queryDraft = $('chat-message').value;
    }

    // Restore unfinished Guided mode work if it exists.
    if (guidedDraft) {
      const draft = guidedDraft;

      showQuestion(draft.index, draft.editing, true);
      $('chat-message').value = draft.text;
    } else {
      // Find the first question that has not been answered.
      const next = questions.findIndex(q => !answers[q.id]);

      if (next === -1) {
        review();
      } else {
        showQuestion(next, false, true);
      }
    }
  }

  // =========================================================
  // GUIDED QUESTIONNAIRE FUNCTIONS
  // =========================================================

  // Shows one questionnaire question in Guided mode.
  // `isEdit` decides whether the user is editing an existing answer.
  function showQuestion(index, isEdit = false, focus = false) {
    activate('guided');

    $('chat-message').placeholder = 'Type your answer here…';

    current = index;
    editing = isEdit;

    $('answer-review').hidden = true;
    $('chat-form').hidden = false;

    // Show earlier questions and answers before showing the current prompt.
    transcript();

    bubble(
      `${isEdit ? 'Edit answer' : 'Question'} ${index + 1} of ${questions.length}: ${
        questions[index].text
      }`
    );

    // Label the input area with the current question.
    $('answer-label').textContent = questions[index].text;

    // Fill the input with the old answer if the user is editing.
    $('chat-message').value = answers[questions[index].id] || '';

    progress();

    // Scroll the chat workspace down to the newest question.
    const scrollArea = document.querySelector('.chat-workspace');
    scrollArea.scrollTop = scrollArea.scrollHeight;

    if (focus) {
      $('chat-message').focus();
    }
  }

  // Displays submitted answers and lets the user choose one to edit.
  function review(focus = true) {
    // Save unfinished Ask mode text before changing to the review screen.
    if (mode === 'ask') {
      queryDraft = $('chat-message').value;
    }

    activate('guided');

    current = null;
    $('chat-form').hidden = true;
    $('answer-review').hidden = false;

    transcript();

    // Clear old review content before rebuilding the list.
    $('review-list').replaceChildren();

    questions.forEach((q, index) => {
      // Skip unanswered questions.
      if (!answers[q.id]) {
        return;
      }

      const item = node('article', '');
      item.className = 'review-item';

      const edit = node('button', 'Edit answer');
      edit.type = 'button';

      edit.setAttribute(
        'aria-label',
        `Edit answer ${index + 1}: ${q.text}`
      );

      // Return to the selected question when the edit button is clicked.
      edit.addEventListener('click', () => {
        showQuestion(index, true, true);
      });

      item.append(node('h4', q.text), node('p', answers[q.id]), edit);

      $('review-list').append(item);
    });

    // Change the button label based on questionnaire completion.
    $('finish-answers').textContent =
      count() === questions.length ? 'Finish review' : 'Continue questions';

    progress();

    if (focus) {
      $('review-title').focus();
    }
  }

  // =========================================================
  // EVENT LISTENERS
  // =========================================================

  // Submit the chat form when Enter is pressed.
  // Shift + Enter still allows the user to create a new line.
  $('chat-message').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
      e.preventDefault();

      if ($('chat-message').value.trim()) {
        $('chat-form').requestSubmit();
      }
    }
  });

  // Handles submitted text in both Ask mode and Guided mode.
  $('chat-form').addEventListener('submit', e => {
    e.preventDefault();

    const value = $('chat-message').value.trim();

    if (!value) {
      return;
    }

    // Ask mode: search the program catalog using the user's message.
    if (mode === 'ask') {
      queryMessages.push({ text: value, user: true });

      $('query-starters').hidden = true;
      bubble(value, true);

      const result = window.demoSearch(
        value,
        window.programCatalog.getPrograms()
      );

      result.demo = window.programCatalog.isDemo();

      // Use a different result message if a real catalog is connected.
      if (!result.demo) {
        result.message = result.rows.length
          ? `${result.rows.length} matching programs found.`
          : 'No matching programs found. Try another major or broaden your filters.';
      }

      queryMessages.push({ result });

      renderResults(result);

      queryDraft = '';
      $('chat-message').value = '';

      const scrollArea = document.querySelector('.chat-workspace');
      scrollArea.scrollTop = scrollArea.scrollHeight;

      $('chat-message').focus();

      return;
    }

    // Guided mode: stop if no current question is selected.
    if (current === null) {
      return;
    }

    // Save the submitted answer to the correct question id.
    guidedDraft = null;
    answers[questions[current].id] = value;

    save();

    $('chat-feedback').textContent = storageAvailable
      ? 'Answer saved in this browser tab.'
      : 'Answer kept on this page only.';

    // Find the next question that still needs an answer.
    const next = questions.findIndex(q => !answers[q.id]);

    // Return to review after editing or after the final question.
    if (editing || next === -1) {
      review();
    } else {
      showQuestion(next, false, true);
    }
  });

  // Continues the questionnaire or creates final major/program results.
  $('finish-answers').addEventListener('click', () => {
    const next = questions.findIndex(q => !answers[q.id]);

    // Continue if any questions still need answers.
    if (next !== -1) {
      return showQuestion(next, false, true);
    }

    // Hide the questionnaire interface and show final results.
    $('answer-review').hidden = true;
    $('guided-progress').hidden = true;
    $('messages').hidden = true;
    $('chat-form').hidden = true;
    $('query-starters').hidden = true;
    $('chat-feedback').textContent = '';
    $('major-results').hidden = false;

    // Reset the table if it already exists.
    if (quizTable) {
      quizTable.reset();
    } else {
      // Create the final major/program table the first time it is needed.
      quizTable = window.createProgramTable($('major-results'), {
        showMatches: true,

        // Combines every answer into one search query for the program catalog.
        getPrograms() {
          const query = questions
            .map(question => answers[question.id])
            .join(' ');

          const result = window.demoSearch(
            query,
            window.programCatalog.getPrograms()
          );

          const details = [...result.terms, ...result.filters];

          // Tell the user how many matching programs were found.
          $('quiz-match-summary').textContent = result.rows.length
            ? `${result.rows.length} ${
                result.rows.length === 1
                  ? 'program matches'
                  : 'programs match'
              } ${
                details.length
                  ? details.join(', ')
                  : 'the preferences in your answers'
              }.`
            : 'No programs match your answers in the current catalog. Edit your answers to add a subject or broaden your preferences.';

          return result.rows;
        }
      });
    }

    $('results-title').focus();
    $('major-results').scrollIntoView({ block: 'start' });
  });

  // Returns the user to the review page from final results.
  $('edit-quiz-answers').addEventListener('click', () => review());

  // Switches from Guided mode back to Ask mode.
  $('ask-mode').addEventListener('click', () => {
    if (mode !== 'ask') {
      showAsk(true);
    }
  });

  // =========================================================
  // STARTER SUGGESTIONS
  // =========================================================

  // Rebuilds the buttons below the chat input with suggested searches.
  function refreshSuggestions() {
    // Update the catalog status message while in Ask mode.
    if (mode === 'ask') {
      $('connection-note').textContent = window.programCatalog.isDemo()
        ? 'Demo data only · Colleges, programs, and tuition figures are fictional.'
        : 'Program catalog loaded · Keyword and filter search preview.';
    }

    const container = $('query-starters');

    // Remove old suggestion buttons before adding new ones.
    container.replaceChildren();

    const suggestions = [
      'Not sure where to start',
      'I like building things',
      ...window.programCatalog.suggestions().slice(0, 2)
    ];

    suggestions.forEach(prompt => {
      const button = node('button', prompt);
      button.type = 'button';

      // Put the selected prompt into the chat input.
      button.addEventListener('click', () => {
        $('chat-message').value = prompt;
        $('chat-message').focus();
      });

      container.append(button);
    });

    // Fallback message if suggestions cannot be loaded.
    if (!suggestions.length) {
      container.append(
        node(
          'p',
          'Suggested questions will appear when program data is available.'
        )
      );
    }
  }

  // Refresh suggestion buttons after the program catalog is updated.
  window.addEventListener('program-catalog-updated', refreshSuggestions);

  // =========================================================
  // INITIAL PAGE SETUP
  // =========================================================

  // Save answers once on startup and update the starter UI.
  save();
  refreshSuggestions();
  progress();

  // Start in Guided mode only when the URL includes ?mode=guided.
  if (new URLSearchParams(location.search).get('mode') === 'guided') {
    startGuided();
  } else {
    showAsk();
  }
})();