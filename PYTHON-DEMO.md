# Python-first Flask application

This branch uses Python, Flask, and WTForms for page routing, search, questionnaire steps and validation, results, catalog filtering/sorting, and program lookup. Jinja templates render HTML with the existing warm theme. Small JavaScript files support the mobile menu, Enter-to-submit, and the existing optional Clerk profile UI. Core searches, forms, filters, and result pages work without JavaScript.

## Run locally

Requires Python 3.10 or newer. From this branch's repository folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

On Windows, activate with `.venv\Scripts\activate` instead. Open http://127.0.0.1:8000. Stop with Ctrl+C. For another port, use `python app.py --port 8001`.

The previous `python backend/server.py` command remains a compatibility entry point. You can also use `python -m flask --app degree_path run --port 8000`.

This is now a server-rendered application. Opening HTML files directly, `python -m http.server`, and GitHub Pages cannot run it. Use the Flask command above.

## Architecture

```text
app.py                         Local launcher
requirements.txt               Flask and WTForms dependencies
 degree_path/
   __init__.py                 Application factory, form protection, errors
   forms.py                    WTForms input validation
   routes.py                   Page routes and compatible JSON API
   services/
     search.py                 Keyword/filter matching
     questionnaire.py          Questions, validation, matching
     catalog.py                Filtering and sorting
   repositories/programs.py    Demo data access
   repositories/postgres.py    PostgreSQL catalog mapping
   database.py                 Lazy direct/Cloud SQL connections
   data/demo_programs.json      The same 15 fictional programs
   templates/                  Shared layout and server-rendered pages
   static/css/                 Existing theme plus form layout
   static/js/                  Menu, keyboard convenience, optional Clerk UI
 tests/test_backend.py          Search and Flask integration tests
```

## Try it

- Ask “Which colleges offer computer science?”: 3 matches.
- Ask “Show online business programs under $20,000”: 1 match.
- Ask “Show computer science programs in Texas”: no matches.
- Complete Find my major, review/edit answers, then view results.
- Use Explore to filter by text and study format, and sort by tuition.
- Open a program: the URL uses its ID, for example `/programs/demo-1`.

The examples above describe automated test fixtures. Normal app launches use the Cloud SQL catalog. Matching is deterministic, not AI or an assessment of admission chances. Unsupported cases include negation and conversational follow-ups. Chat displays the last ten successful searches, but each search is independent. Results sort by matched topics and tuition; the catalog table has its own user-selected sort.

## Data and sessions

No database setup or migrations are run. A read-only `PostgresProgramRepository` now implements `all()` and `get(program_id)` against `database-branch`. Cloud SQL is the default; direct PostgreSQL is also supported. Demo fixtures are restricted to automated tests. See [database connection setup](DATABASE-CONNECTION.md). Database credentials belong on the server.

Questionnaire answers and recent searches are held in server memory, scoped to an opaque browser session ID. Tabs in the same browser share a session. They expire after two hours of inactivity, server restart, or eviction when more than 256 demo sessions exist. They are not saved to a Clerk account or PostgreSQL. Cookies contain only a session identifier and form-protection token, not answers. Form POSTs use CSRF tokens, and templates escape user input.

This is a local, single-process demo. Production deployment needs a shared durable session store, server-side account verification where required, HTTPS cookie configuration, and a production WSGI server. An optional `SECRET_KEY` environment variable controls Flask signing; otherwise a random key is generated on startup. Do not commit secrets.

The existing Clerk profile UI is retained and still requires JavaScript and a working Clerk configuration. It does not authenticate Flask routes. Demo routes remain public. Live Clerk sign-in was not exercised during this migration.

## API

- `GET /api/health`: `status`, `engine`, `framework`, `demo`.
- `GET /api/programs`: `{ "programs": [...], "demo": true }`.
- `POST /api/search`: JSON `{ "question": "computer science" }`; returns `rows`, `terms`, `filters`, `message`, `demo`, `engine`.

The JSON API remains compatible with the earlier demo. Current HTML pages submit directly to Flask. Old page URLs redirect to their Flask equivalents; old program-detail snapshot links go to Explore because URL fragments never reach the server.

## Verification

```sh
python -m unittest discover -s tests -v
```

Tests cover demo searches, tuition boundaries, missing costs, routes, templates, static-file restrictions, form validation/escaping, CSRF, session isolation, large answers, questionnaire editing/reset, catalog filtering/sorting, old URL redirects, and API compatibility/errors. Optional JavaScript syntax checks:

```sh
node --check degree_path/static/js/forms.js
node --check degree_path/static/js/chat-shell.js
node --check degree_path/static/js/profile-auth.js
```

This branch derives from committed `landingpage` revision `969040d` and preserves the later Python demo branch commits. Local uncommitted interface/sign-in edits from the original checkout were not included in this migration.
