# Python demo backend

This experimental branch connects the existing website to a Python backend using the same 15 fictional programs. No PostgreSQL database, credentials, packages, or AI service are required. Your teammate can continue developing PostgreSQL independently.

## Run locally

Requires Python 3.10 or newer. From the repository folder:

```sh
python3 backend/server.py
```

Open http://127.0.0.1:8000 in your browser. Stop with Ctrl+C. If that port is busy, run `python3 backend/server.py --port 8001` and open http://127.0.0.1:8001.

The chat footer should say **Python backend**. Ask a question or complete **Find my major**. Both send searches to Python. Explore also loads the program catalog from Python. Program matching remains deterministic keyword/filter matching, not an AI assessment.

Opening the files directly or using static hosting (including GitHub Pages) retains browser-based demo matching. Static hosting cannot run the Python backend. The footer says **Browser search** in that mode. Once Python mode is enabled, failed searches show an error and preserve input so you can retry; they never silently fall back to browser matching.

## Try these searches

- Which colleges offer computer science? → 3 programs.
- Show nursing programs in Connecticut → 1 program.
- Show online business programs under $20,000 → 1 program.
- Show computer science programs in Texas → no matches.
- Show all programs → 15 programs.

For the questionnaire, try “coding”, “programming”, “technology”, “software”, and “computer science”. The matches should include the three computer science programs. Edit an answer and finish again to recalculate.

## API and files

- `GET /api/health` reports the Python engine and demo status.
- `GET /api/programs` returns `{ "programs": [...], "demo": true }`.
- `POST /api/search` accepts JSON such as `{ "question": "computer science" }` and returns `rows`, `terms`, `filters`, `message`, `demo`, and `engine`.
- `backend/search.py` loads fixtures and implements matching.
- `backend/server.py` serves the API and public website files on localhost.
- `assets/js/program-api.js` connects the interface to the API.
- `assets/js/backend-config.js` defaults to static mode; the Python server serves this script with Python mode enabled.

The single fixture remains `assets/data/demo-programs.js`. Its array is now formatted as JSON-compatible data (double-quoted strings, no trailing commas). Python parses only the data after `window.demoPrograms = ` using `json.loads`; it does not execute JavaScript. Restart the Python server after editing fixtures.

Search supports subjects, named colleges, states, Public/Private, Online/Campus/Hybrid, and tuition limits. Results sort by matched topic count, then tuition. Natural-language negation and conversational follow-ups remain unsupported. Questionnaire answers are joined into one query; this is a demo, not a learned recommendation system. Answers remain in browser session storage and are sent to the local backend for matching when you finish. The server does not persist them or log request bodies.

## Test

```sh
python3 -m unittest discover -s tests -v
node --test tests/test_program_api.cjs
node --check assets/js/chat-interface.js
node --check assets/js/program-api.js
```

The Python tests cover documented searches, tuition boundaries, missing tuition, campus/state matching, API validation, and public-file restrictions. JavaScript tests cover static fallback, Python request/response handling, and API failure behavior. Node is optional and used only for these checks.

## Future PostgreSQL integration

Replace fixture loading/search with database queries after agreeing on your teammate's schema. Keep the frontend API response structure stable. This branch creates no database tables or migrations. The standard-library server is a local development demo; production hosting, database access, authentication, and deployment configuration are separate future work.

This branch starts from committed `landingpage` revision `969040d`. Uncommitted sign-in/interface edits in the original checkout were intentionally preserved there and are not included in this experiment.
