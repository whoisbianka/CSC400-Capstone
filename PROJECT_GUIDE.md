# Degree Path Explorer — a guide to the current project

**Update:** Explore now supports saved/resettable preferences and chat has a separate reset action. See [current preferences and reset behavior](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/PREFERENCES_SETUP.md). The walkthrough below describes the earlier snapshot; its comments about preferences/reset and definition line numbers may be outdated.

This guide describes the files present on October 21, 2026. It explains the implementation, rather than the older plans in the conversation or README. It does not certify that the deployed database or external services are configured correctly. No application code was changed to prepare it, and no cloud requests or database rebuilds were run.

The project is in `CSC400-Capstone-newtestbranch`. There is no separate `database` directory in the current parent directory. Database code, website code, and data preparation files now live together here.

Read sections 1–4 first, then follow a feature through section 6 and its database functions in section 7. The later sections explain every template, browser script, stylesheet, data file, and test file. Installed library internals and generated files are explained as categories; they are not code your team wrote.

## Contents

- [1. What the application actually does](#1-what-the-application-actually-does)
- [2. How the files work together](#2-how-the-files-work-together)
- [3. Startup, configuration, and connections](#3-startup-configuration-and-connections)
- [4. Sign-in and guest state](#4-sign-in-and-guest-state)
- [5. Gemini interpretation](#5-gemini-interpretation)
- [6. Every route and helper in `degree_path/routes.py`](#6-every-route-and-helper-in-degreepathroutespy)
- [7. Every function in `db_functions.py`](#7-every-function-in-dbfunctionspy)
- [8. Schema files and database relationships](#8-schema-files-and-database-relationships)
- [9. Data preparation and every data file](#9-data-preparation-and-every-data-file)
- [10. Every HTML template](#10-every-html-template)
- [11. Every browser JavaScript file and its functions](#11-every-browser-javascript-file-and-its-functions)
- [12. Comparison rules in `degree_path/comparison.py`](#12-comparison-rules-in-degreepathcomparisonpy)
- [13. Remaining Python helper: `degree_path/forms.py`](#13-remaining-python-helper-degreepathformspy)
- [14. Every stylesheet and image](#14-every-stylesheet-and-image)
- [15. Tests: what each file and helper checks](#15-tests-what-each-file-and-helper-checks)
- [16. Repository, editor, documentation, and generated files](#16-repository-editor-documentation-and-generated-files)
- [17. Three complete examples to connect the pieces](#17-three-complete-examples-to-connect-the-pieces)
- [18. What is implemented, what is older, and where to work next](#18-what-is-implemented-what-is-older-and-where-to-work-next)

## 1. What the application actually does

There are five main user activities:

1. **Chat:** Gemini asks questions and identifies interests from a controlled keyword list. Python validates the answer. SQL finds up to six majors that match the most saved interests.
2. **Explore:** browse either individual programs or the major catalog. Search, filters, sorting, and pagination run through Flask and SQL.
3. **Favorites:** signed-in users can save majors and particular programs separately.
4. **Compare:** signed-in users select two or three favorites and compare their database statistics.
5. **Accounts:** Clerk verifies a sign-in. Flask then remembers the verified application user in a signed session cookie for a fixed 24-hour login period.

A **major** is a field of study, such as Biology. A **program** is a particular school's offering of a major at a credential level. Biology at College A and Biology at College B are different programs. An associate and bachelor's offering can also be different programs at the same school.

The AI does not directly query PostgreSQL, assign database IDs, or compute the final ranking. It translates conversational interests into approved keyword names. Python translates those names to IDs; SQL counts the matching keyword IDs for each major. This separation lets the AI understand language while keeping the recommendation evidence and ranking inspectable.

School preferences are only partly represented in the code. There is a `user_info` table and a guest `preferences` object, but the current chat flow does not save a completed school-preference model or automatically generate personalized program recommendations from it. Profile and Settings are placeholders.

## 2. How the files work together

```text
Browser
  HTML: structure and initial database results
  CSS: appearance
  JavaScript: clicks, API requests, chat, favorites, comparisons
        |
        | HTTP requests
        v
app.py -> degree_path.create_app()
        -> degree_path/routes.py
             | auth.py: verified identity from the session
             | chat_service.py: Gemini interpretation and validation
             | comparison.py: comparison display rules
             | guest_state.py: temporary guest identity
             v
        db_functions.py: SQL queries and transactions
             v
        cloud_sql_connection.py: connection pool and database password
             v
        Cloud SQL PostgreSQL

Separate administrative workflow:
db_setup.py -> cloud_admin_connection.py
            -> data files + schemas/all_schema.sql -> populated PostgreSQL
```

The browser cannot import your Python functions. It sends a request to a route. The route calls the Python function, then returns HTML or JSON.

An example: clicking a favorite button runs JavaScript, which sends `POST /api/favorites` with a major code. Flask reads the user's ID from its session, calls `add_major_fav`, and returns JSON. JavaScript changes the button only after the server confirms success.

### Terms you will see throughout the project

- **Route:** a URL plus an HTTP method connected to a Python function.
- **GET:** usually asks for information. Explore filters are GET query parameters, so filtered pages can be bookmarked.
- **POST:** submits a change or message. The application checks a CSRF token for every POST.
- **Template:** an HTML file with Jinja expressions such as `{{ program.major }}`. Flask fills these in before sending HTML.
- **JSON:** a format for sending dictionaries/lists between the browser, Flask, and Gemini.
- **Blueprint:** Flask's way to collect related routes. This project's blueprint is called `web`; `web.explore` means the `explore` endpoint on that blueprint.
- **Session:** the small visitor-specific dictionary Flask stores in a signed browser cookie. Signed means changes can be detected; it does not mean the contents are encrypted.
- **Database transaction:** a group of writes that either all commit or all roll back.
- **Connection pool:** reusable database connections. Returning one to the pool is faster than authenticating and opening a new connection for every request.
- **Primary key:** the identifier for one row. A foreign key points at a related row. A unique constraint prevents duplicate values or pairs.
- **CIP code / `cipcode`:** the major identifier used across the catalog tables. It is different from the internal `majors.id`.
- **`unitid`:** the school identifier. It is different from `schools.id`.
- **`program_id`:** the application's program identifier. The database also has a separate internal `programs.id`.

## 3. Startup, configuration, and connections

### `app.py`

This is the local entry point. There are no named functions in this file.

It loads `.env` from the directory containing `app.py`, sets default certificate bundle environment variables using `certifi`, imports `create_app`, and creates the Flask application. Loading settings before importing the application matters because importing the database module builds the database engine and reads its password secret.

When run directly, the `if __name__ == '__main__'` block parses `--port` and runs Flask on `127.0.0.1`, default port 8000, with debugging disabled. For example, `python app.py --port 8001` uses another local port. Importing `app` creates the application but does not execute that direct-run server block.

### `degree_path/__init__.py`

The special filename makes `degree_path` a Python package. Its main job is the application factory.

**`create_app(test_config=None)`** builds and returns the Flask app. It loads configuration, sets certificate defaults, validates `PRIVATE_IP`, checks that the required session and Clerk settings exist, registers request hooks and routes, and warms five database connections outside testing mode. `test_config` lets tests supply settings without relying on the real environment.

The nested functions are registered with Flask through decorators:

- **`protect_forms()`** runs before requests and checks POST requests. JSON requests must send `X-CSRF-Token`; ordinary form requests must send `csrf_token`. The value must match the token in the session. A mismatch produces HTTP 400. This helps prevent another website from silently submitting actions using a visitor's cookies.
- **`template_helpers()`** creates a random CSRF token if necessary and makes it and the public Clerk key available to templates. It does not send the Clerk secret key to the browser.
- **`money(value)`** is a Jinja filter: `{{ earnings|money }}` formats a number with a dollar sign and commas. `None` displays as `Not available`; zero remains a real dollar value.
- **`http_error(error)`** handles Flask/Werkzeug HTTP errors such as `abort(404)`. `/api/` paths receive JSON with an error message and the appropriate status; ordinary pages receive `error.html`. This is not a universal handler for every unexpected Python exception.
- **`response_headers(response)`** adds `Cache-Control: no-store` to non-static responses and `X-Content-Type-Options: nosniff` to responses. Static CSS/JS can still be cached.
- **`cleanup_guests()`** registers the `flask --app app cleanup-guests` command. It deletes expired guest rows and prints the count. Defining the command does not schedule it to run automatically.

Session settings matter: `HTTPONLY` prevents ordinary browser scripts from reading the cookie; `SAMESITE='Lax'` limits some cross-site cookie sending; `SESSION_COOKIE_SECURE` controls HTTPS-only delivery. `PERMANENT_SESSION_LIFETIME` is 24 hours and `SESSION_REFRESH_EACH_REQUEST=False` avoids refreshing the cookie on every ordinary request. The separate login deadline in `auth.py` enforces the fixed account login period even if other session values change.

`MAX_CONTENT_LENGTH=65536` limits entire request bodies to 64 KiB. Chat also has its own 4,000-character message limit. These are different limits.

The pool is warmed during app creation, before the local server starts serving requests—not on the first click of a visitor. A database authentication failure can therefore prevent startup. Each separate server process has its own pool; five connections are not a single global limit across all deployed workers.

### `cloud_sql_connection.py`

This is the normal website connection module. The database login is the built-in PostgreSQL user from `DB_USER`, authenticated with a password. It is separate from a website visitor's Clerk account.

- **Module-level `_connector`:** creates a Cloud SQL connector with lazy refresh. It provides the connection machinery; SQLAlchemy manages pooling.
- **`get_database_password()`** reads the secret version named by `DB_PASSWORD_SECRET_VERSION` with Google Secret Manager, decodes its payload from bytes to text, and returns the password. The Google identity running Python needs permission to read that secret.
- **`connect_with_connector()`** reads instance, database, username, password, and public/private network settings. It creates and returns the SQLAlchemy engine with a pool size of five, up to two overflow connections, and a 30-second pool checkout timeout.
- **Nested `getconn()`** is the engine's connection factory. When the pool needs a physical connection, it calls the Cloud SQL connector with the `pg8000` driver, username, password, database, and `enable_iam_auth=False`.
- **`close_connector()`** closes the global connector's resources. Merely defining this function does not make it an automatic shutdown hook.

The password is fetched when the engine is constructed, not on every SQL query. Existing engine configuration will not automatically reread a rotated Secret Manager password. The connector still uses Google credentials to access Cloud SQL connection services, while PostgreSQL separately checks the database username/password and its SQL grants.

### `cloud_admin_connection.py`

This is the administrative connection used by the setup script. `connect_with_connector()` reads `DB_IAM` rather than the runtime password user. Its nested `getconn()` uses `enable_iam_auth=True`. The Google identity and database IAM user must correspond to the administrative access being used. `close_connector()` closes its connector.

It has a similar pool configuration. Unlike the runtime certificate defaults, its certificate assignments overwrite those environment variables. Also, its `certifi` import is above its `try` block, so that block would not handle a missing `certifi` package at import time.

This file exists locally but is listed in `.gitignore`. That matters to teammates: the checked-out project may not provide this local file even though `db_setup.py` imports it.

### `.env`

This is local configuration, not application logic. Its values are intentionally not reproduced here.

| Variable present | What it means |
|---|---|
| `INSTANCE_CONNECTION_NAME` | Identifies the Cloud SQL project, region, and instance. |
| `DB_NAME` | PostgreSQL database name within that instance. |
| `DB_IAM` | Database IAM identity used by the administrative connector. |
| `DB_USER` | Built-in database username used by the website. |
| `DB_PASSWORD_SECRET_VERSION` | Full Secret Manager version resource for the website's database password. |
| `GEMINI_MODEL` | Model name passed to the Gemini SDK. |
| `GEMINI_API_KEY` | Server-side credential for Gemini. |
| `CLERK_SECRET_KEY` | Backend Clerk credential used during sign-in verification. |
| `CLERK_PUBLISHABLE_KEY` | Public key allowed in browser configuration. |
| `CLERK_AUTHORIZED_PARTIES` | Comma-separated allowed application origins for token verification. |
| `SECRET_KEY` | Flask cookie-signing secret; changing it invalidates existing signed sessions. |
| `SESSION_COOKIE_SECURE` | Whether cookies are delivered only over HTTPS. |

Code also supports `PRIVATE_IP` with a default of false, even though it was not an assignment in the inspected `.env`. Certificates can be configured through `SSL_CERT_FILE` and `REQUESTS_CA_BUNDLE`. Google Application Default Credentials are usually outside `.env`; absence of a credential assignment in this file does not mean no Google credentials exist.

### `requirements.txt`

This is the installation list. Flask runs the website; WTForms provides form validation; python-dotenv loads environment settings; SQLAlchemy executes SQL and pools connections; pg8000 speaks PostgreSQL; the Cloud SQL connector connects to the managed instance; certifi provides trusted certificate authorities; pandas and NumPy prepare datasets; Secret Manager reads the runtime password; sqlparse splits the schema script; google-genai calls Gemini; Pydantic validates structured data; clerk-backend-api verifies account sign-ins; httpx constructs the request passed to Clerk. Some versions are pinned, some bounded, and some unpinned, so it is not a fully reproducible dependency lockfile.

## 4. Sign-in and guest state

### `degree_path/auth.py`

**`establish_login()`** is called only when establishing the app login. It requires an `Authorization: Bearer ...` header, constructs an `httpx.Request`, and asks Clerk to authenticate it with the configured authorized parties. It rejects unsigned-in results and a missing or malformed `sub` identity. A valid Clerk `sub` is the `clerk_user_id`.

It then calls `create_or_update_user`, obtaining the local database user ID. It stores `user_id`, `clerk_user_id`, and `login_expires_at` in the Flask session, makes the cookie permanent, and generates a fresh CSRF token. It returns the local user dictionary. It does not store the bearer token or a password in the users table.

**`expire_login()`** runs before every request. When the fixed deadline has passed, it removes the three login fields. It does not clear every guest or unrelated session field. A later protected request then treats the visitor as signed out.

**`get_current_user()`** reads the verified session and returns an identity dictionary or `None`. It makes no Clerk or database request. If the page supplies `X-App-User-ID`, it checks that the page's remembered identity still matches the session. This rejects an old tab after an account switch. The header is a consistency check, not permission to impersonate the ID in it.

The identity lifetime is therefore controlled by Flask after login. The app does not recheck Clerk revocation on every request. Signing out clears this browser's Flask session; there is no server-side registry that individually revokes copied signed cookies.

### `degree_path/guest_state.py`

**`get_or_create_guest_session()`** looks for `guest_id` in the Flask cookie, then loads the matching unexpired database row. If none exists, it creates a random opaque ID, inserts initial guest state, saves that ID in the permanent Flask cookie, and returns `(guest_id, guest_record)`.

The cookie holds the ID, not the conversation. The conversation lives temporarily in `guest_sessions.state`, a PostgreSQL JSONB object:

```json
{"messages": [], "keywords": [], "preferences": {}, "recommendations": []}
```

Successful guest messages extend the database row's expiration by 24 hours. Reading the chat does not extend that database deadline. Cookie lifetime and database expiration are separate: a surviving database row cannot be recovered by a browser that has lost its guest ID.

The version number supports optimistic concurrency. If two tabs both read version 4, only the first save can update version 4 to version 5. The other save receives a conflict instead of silently overwriting newer state.

Signing in does not migrate the guest conversation into the account tables. Account and guest histories currently remain separate. Signing out clears the cookie, including its guest ID; it does not immediately delete the former guest row or the permanent account data.

## 5. Gemini interpretation

### `degree_path/chat_schemas.py`

These are Pydantic classes. Think of each class as a precise shape that an incoming object must satisfy.

- **`GeminiKeywordAddition`** contains a keyword name and evidence string. Both must be nonempty strings.
- **`GeminiAdvisorTurn`** contains `reply`, a list of name-based additions, a list of name-based removals, and `major_mentions`.
- **`KeywordAddition`** is the internal equivalent with `keyword_id` instead of a name. IDs must be integers at least 1.
- **`AdvisorTurn`** is the internal validated result with ID-based additions and removals. Its reply is between 1 and 4,000 characters.

All four reject extra fields, use strict types, and strip surrounding whitespace from string fields. The list fields have no defaults, so the model must return them even when empty. These classes do not themselves check that a keyword exists in PostgreSQL; `chat_service.py` checks names against the supplied catalog.

Two representations are intentional. Sending only names to Gemini reduces repeated context such as `keyword_id` and object keys. The server already knows the name-to-ID mapping and can resolve IDs deterministically.

### `degree_path/prompts/advisor.txt`

This is the AI's system instruction text, read by `interpret_message`. It asks the model to act as a major-exploration advisor, ask one clear question at a time, choose exact catalog keyword names based on meaning, quote the latest user message as evidence, and remove interests only when the user indicates a change. It instructs the model not to invent school data or admissions predictions and to treat conversation/context as data rather than overriding instructions.

A prompt influences output; it is not a database constraint or a guarantee. The Python checks remain necessary even with a good prompt. Instructions about discussing preferred majors do not themselves implement preference storage or school matching.

### `degree_path/chat_service.py`

**`InvalidAdvisorResponse`** is a custom exception class. It distinguishes a response that came back but cannot safely be used from an external API/network failure.

**`_keyword_rows(rows, name)`** checks that the input is a list of dictionaries with positive integer IDs and nonempty labels. It rejects duplicate IDs and returns cleaned dictionaries. `name` is used to make error messages identify which input was bad. A leading underscore signals an internal helper, not special Python access control.

**`interpret_message(message, keyword_catalog, saved_keywords, recent_messages, *, client=None, model=None)`** performs one complete AI interpretation without reading or writing the database:

1. Validate and strip the latest message, enforcing 1–4,000 characters.
2. Validate catalog and saved keywords. Build ID-to-name and name-to-ID dictionaries. Reject duplicate keyword names because a name would otherwise map ambiguously to more than one ID.
3. Check that saved IDs and labels match the catalog.
4. Take the last 20 history messages. Validate their `user`/`assistant` roles and string contents. History excludes the new message, which has its own field.
5. Obtain the model from the argument or `GEMINI_MODEL`, and read `advisor.txt`.
6. Build compact JSON containing keyword names, saved names, recent messages, and the latest message. Evidence and numeric IDs are not repeated in the catalog sent to Gemini.
7. Set the system instruction, request JSON output, and supply the JSON schema from `GeminiAdvisorTurn.model_json_schema()`.
8. Log model/counts/context-byte length. This log is context size, not token count or a complete size measurement of system instructions and schema.
9. Use an injected client, or open a client with the environment API key. The owned client's timeout is 90,000 milliseconds and its retry settings allow three attempts for 503/504 with increasing delays and jitter. Total user waiting can exceed a single timeout because of retries.
10. Call `client.models.generate_content`. This is still the Generate Content API, not Interactions.
11. Reject missing text, malformed JSON, or invalid fields.
12. Reject unknown keyword names, repeated changes, a keyword both added and removed, and removals of unsaved interests.
13. Normalize case and whitespace in evidence and the latest message, and require the evidence to appear inside that message. This detects invented quotes, but it is not an independent proof that the AI's interpretation of a quote is correct.
14. Translate the approved names to IDs and return `AdvisorTurn`.

The function's optional injected client makes offline tests possible. Provider exceptions propagate to the route. A valid result is still only a proposal until the route saves it. `major_mentions` is returned but is not used by the current save path to generate school recommendations.

Example: the catalog has `{keyword_id: 7, keyword: 'Biology'}`. Gemini returns an addition with `keyword: 'Biology'` and evidence `I enjoy biology`. The service returns `KeywordAddition(keyword_id=7, evidence='I enjoy biology')`. The database then counts this ID against `major_keywords`.

## 6. Every route and helper in `degree_path/routes.py`

This file is the web coordinator. It reads request inputs, gets identity, calls services and SQL functions, and chooses an HTML or JSON response. It should be read as a set of small request workflows, not as one function that runs top to bottom on each visit.

### Shared helpers

- **`database_errors(function)`** wraps database-related helper calls. Its nested **`wrapped(*args, **kwargs)`** calls the original function, preserves intentional HTTP errors, and converts other exceptions into a generic 503 database-unavailable page. Because it catches all other exceptions, a programming bug can also get that message; the label alone is not proof of a database outage. `wraps` preserves the original function's metadata.
- **`normalize(value)`** lowercases text, replaces non-ASCII-letter/digit runs with spaces, and collapses whitespace. It supports the older major-name search, not Gemini's semantic interpretation.
- **`college_website_url(value)`** converts suitable bare domains to HTTPS URLs and allows only HTTP/HTTPS addresses with a hostname and no embedded username/password. It rejects whitespace and suspicious schemes before the template uses a link.
- **`format_program_cards(data)`** transforms flat query rows into a consistent card dictionary. It puts credential/cost/test/admission fields under `facts`, sanitizes the website URL, and preserves pagination metadata.
- **`catalog_majors()`** scans the majors table, extracts codes/names, sorts by name, and caches the result in Flask `g` for the current request only. This is used by the older search path. It is not an application-wide cache.
- **`program_page(...)`** merges major and degree arguments with other filters, calls `get_page_programs` for 25 results, converts validation failures to 400, then formats cards. Its `shuffle_seed` argument is currently unused. Having a seed in the session does not shuffle the SQL results.
- **`program(program_id)`** rejects invalid IDs, loads one program, returns `None` if absent, and groups cost, SAT, ACT, and description fields for the detail template.
- **`recommendations(terms)`** is the older name-matching workflow. It normalizes supplied major names, scans actual catalog names for whole normalized phrases, orders exact matches first, takes up to six majors, and retrieves three high-earnings programs per major. It does not use Gemini or user keywords. The old helper does not return program IDs, so this function does not invent detail links.
- **`positive_arg(name, default=None, maximum=2147483647)`** reads a URL query argument, returns its default when missing/empty, otherwise requires an integer from 1 to the specified maximum. Invalid input aborts with 400.
- **`text_value(value)`** validates a stripped 1–200-character major-name string for the older search routes.

### HTML page routes

| Method and path | Function | What it does |
|---|---|---|
| GET `/` | `home()` | Renders the home page with direct links to Explore and the Gemini chat. |
| POST `/`; GET/POST `/chat` | `chat()` | Renders the older major-name search. POST validates `question` and calls the older `recommendations()` helper. It is not the Gemini chat. |
| POST `/chat/reset` | `reset_chat()` | Redirects to `/chat` with 303. It does not delete permanent or guest Gemini chat history. |
| GET `/questionnaire` | `questionnaire()` | Renders `guided_chat.html`, the current Gemini chat shell. JavaScript loads its content separately. |
| GET `/explore` | `explore()` | Chooses the programs or majors catalog, validates filters, queries data, and renders the selected view. |
| GET `/programs/<int:program_id>` | `program_details(program_id)` | Calls `program()`, returns 404 if missing, otherwise renders the detail page. |
| GET `/start/<destination>` | `start(destination)` | Compatibility redirect for `explore` or `questionnaire`. The old account-choice screen is gone. Other destinations get 404. |
| GET `/profile` | `profile()` | Renders the placeholder Profile page; it does not load a student profile. |
| GET `/settings` | `settings()` | Renders the placeholder Settings page. |
| GET `/<page>.html` | `legacy_page(page)` | Maps known old HTML URLs to current routes. `index.html?mode=guided` goes to the chat. Unknown names return 404. |
| GET `/favorites` | `favorites()` | Renders a signed-in favorites shell or the sign-in/home gate. Favorites data is loaded by JavaScript only for signed-in visitors. |
| GET `/compare` | `compare()` | Renders a signed-in comparison shell or the same account gate. |

### The `explore()` program workflow, step by step

1. Read `view`, default `programs`; reject unknown values. `majors` delegates to `explore_major_catalog()`.
2. Translate an approved UI sort name such as `earnings_desc` into a database sort key and direction. Browser input never becomes an arbitrary SQL column here.
3. Read page number, optional major code, major name, and major-filter mode.
4. For a signed-in user, fetch their favorite major list for the filter controls.
5. In `all` mode, clear the single-major restriction. In `name` mode, use an exact case-insensitive major name or a supplied CIP code. In `favorites` mode, verify every selected code belongs to this user and use the union of those majors. An empty selected favorites list deliberately yields no results.
6. Parse selected degree levels 2 and 3. An empty degree selection means no degree restriction.
7. Parse school-name substring, state/city, cost ceilings, and acceptance-rate limits. Validate lengths, integer ranges, and minimum/maximum consistency.
8. Create the old shuffle-seed session value if missing; this value currently does not affect sorting.
9. Call `program_page`, which calls SQL once for the joined result rows.
10. Construct a `pagination` dictionary that preserves the active filters in Previous/Next links, and render `explore.html`.

The selected favorite majors are OR choices within one filter (`major A OR major B`); independent restrictions combine with AND (`one of those majors AND NY AND net price <= ceiling`).

**`explore_major_catalog()`** handles the major tab without querying the program page helper. It validates page, partial-name search, sort, favorites-only flag, has-programs flag, and minimum earnings. Favorites-only guests go to the account gate. It passes the session's user ID to `get_major_catalog_page`, preserves filters in pagination, and renders `explore_majors.html`. Name search here is partial; the program tab's specific-major name filter is exact.

### JSON API routes

| Method and path | Function | Inputs and response |
|---|---|---|
| GET `/api/health` | `health()` | Returns static Flask status information. It does not test the database or Gemini. |
| GET `/api/programs` | `programs_api()` | Accepts page and optional CIP code; returns formatted programs and pagination metadata. It does not expose every HTML Explore filter. |
| POST `/api/search` | `search_api()` | Requires JSON `{question: ...}`; uses the old major-name search. |
| POST `/api/recommendations` | `recommendations_api()` | Requires a list of 1–20 major-name strings; also uses the old search, not the saved keyword ranking. |
| GET/POST `/api/chat` | `api_chat()` | Loads or updates the real Gemini chat. Detailed below. |
| GET/POST `/api/favorites` | `favorites_api()` | Signed-in users only. GET lists major favorites; POST requires integer `cipcode` and Boolean `favorite`, then saves/removes that favorite for the session user. |
| POST `/api/auth/session` | `auth_session_api()` | Calls `establish_login()` with the Clerk bearer token; returns the verified local user ID. Logs unexpected login failures and returns 503. |
| POST `/logout` | `logout()` | Calls `session.clear()` and returns `{ok: true}`. The browser separately signs out of Clerk. |
| GET `/api/compare` | `compare_api()` | Requires login and `kind=majors` or `programs`; queries only the user's favorites and returns items plus metric rules. |
| GET/POST `/api/program-favorites/<int:program_id>` | `program_favorite_api(program_id)` | GET returns whether one program is saved. POST requires Boolean `favorite` and saves/removes it. Invalid IDs get 400; saving a nonexistent program gets 404. |
| GET `/api/program-favorites` | `program_favorites_api()` | Returns this user's saved programs with credential labels and detail URLs. |
| GET `/api/major-names` | `major_names_api()` | Accepts `q`; under two characters returns an empty list without a database query. Over 200 characters gets 400. Otherwise returns up to 20 suggestions. |

For favorites endpoints, the trusted user ID comes from the session, not a `user_id` supplied in the JSON or URL. Unexpected database failures are logged and exposed as generic 503 messages. All POST requests also pass the global CSRF check before entering these functions.

### The `api_chat()` workflow

GET identifies an account user or temporary guest, loads messages and keywords, loads recommendations from the corresponding storage, and returns JSON. GET does not call Gemini.

POST first requires a JSON object with a nonempty message of at most 4,000 characters. It loads current history/keywords, loads the keyword catalog, and calls `interpret_message`. A signed-in user goes through `save_chat_turn`, which saves the messages, keyword changes, and refreshed recommendations together. A guest goes through `apply_guest_chat_turn`, ranks the resulting keywords, then saves the JSON state with its expected version.

A guest version conflict or expiration produces 409 and asks the user to reload. An invalid model response produces 502. Other exceptions, including provider outages, produce a logged 503. This is why “Chat is temporarily unavailable” by itself does not tell you which dependency failed: the terminal traceback supplies that detail.

The successful POST response contains `mode`, `reply`, and `recommendations`. The browser knows the message it sent and adds both bubbles only after saving succeeds.

**`apply_guest_chat_turn(state, message, turn, catalog)`** copies the old state rather than mutating it, builds a keyword-ID dictionary, removes requested keywords, inserts or replaces additions with labels/evidence, and appends user/assistant messages. It keeps only the last 100 guest messages. It clears recommendations when interests change; the route immediately recalculates them. It preserves any other state such as the preferences object, but does not populate new preference fields itself.

## 7. Every function in `db_functions.py`

This file is the database access layer. Importing it runs `engine = connect_with_connector()`. Most helpers use raw SQL inside SQLAlchemy `text(...)`; this project is not using ORM model classes to represent all tables.

### How to read the repeated SQLAlchemy patterns

`with engine.connect() as connection` checks out a pooled connection and returns it to the pool when the block ends. `with engine.begin() as connection` additionally commits successful writes or rolls back on an exception.

`text('... WHERE user_id = :user_id')` defines SQL with a placeholder. `execute(query, {'user_id': user_id})` supplies the value separately. The parameter is data, not SQL syntax. Names of tables/columns and `ASC`/`DESC` cannot safely be supplied this same way; the current catalog helpers choose those from approved dictionaries.

`.mappings()` makes row fields accessible by column name. `.all()` fetches a list. `.one()` requires exactly one row; `.one_or_none()` allows zero or one; `.scalar_one()` returns a single cell. `dict(row)` makes a plain Python dictionary that can be sent to templates or JSON.

`bindparam('keyword_ids', expanding=True)` expands a list into individual SQL placeholders for an `IN` condition. For example, `[7, 9]` means “ID is 7 or 9.” It does not insert unescaped user strings into SQL.

`LEFT JOIN` keeps the main record even when optional statistics are missing, filling those fields with SQL NULL/Python None. `JOIN` requires a matching related record. A `WHERE` filter on an optional value can still exclude a NULL row because a missing value does not satisfy a numeric comparison.

### Users, inserts, and simple lookups

- **`create_or_update_user(clerk_user_id)`** inserts a local user if the unique Clerk ID is new. `ON CONFLICT DO NOTHING` avoids duplicate accounts. If the insert returns no row, a lookup returns the existing user. Despite the name, it currently does not update profile fields.
- **`add_major_fav(user_id, cipcode)`** first checks that the major exists. If not, returns false. Otherwise inserts the user/major pair, ignores duplicates, and returns true, including when already saved.
- **`add_program_fav(user_id, program_id)`** does the equivalent for a specific program. The older comment mentioning a school is misleading; this stores a program ID.
- **`add_program_rec(user_id, program_id)`** inserts a program recommendation directly. It does not calculate a recommendation and does not have the duplicate-ignore behavior of favorites. It is not the current Gemini ranking path.
- **`add_to_chat_to_log(user_id, content, sender)`** writes one message. Its spelling is the actual function name. The main account chat uses the larger atomic `save_chat_turn` instead.
- **`add_user_keyword(user_id, keyword_id, evidence)`** inserts a saved interest. On a duplicate pair it does nothing, so it keeps the old evidence. This differs from `save_chat_turn`, which updates evidence on conflict.
- **`get_a_keyword_id_from_keyword(keyword)`** fetches exactly one matching keyword ID. It returns a SQLAlchemy row, not just the integer; missing or multiple matches raise an exception.
- **`get_a_keyword_from_keyword_id(keyword_id)`** performs the reverse lookup and similarly expects exactly one row.
- **`get_user(clerk_user_id)`** returns a user dictionary or None. The normal request-time `get_current_user` does not call this; it uses the session.
- **`get_user_keywords(user_id)`** joins `user_keywords` to `keywords` and returns dictionaries containing `keyword_id`, label, and evidence. These are the saved interest records used by chat.
- **`get_keywords()`** returns the entire catalog as ordered ID/label dictionaries. Those IDs remain on the server when building the compact Gemini context.
- **`get_recent_chatlog(user_id, limit=20)`** selects the latest messages by time and ID descending, then reverses them to conversational order. It loads 20 individual messages by default, not 20 user/assistant pairs. Older messages remain in the database.

### Older school/statistic helpers

These functions are useful to understand your original database interface, but the main Explore/detail/compare pages mostly use joined queries instead of calling one helper for each statistic.

- **`get_school_adm_crit(unitid)`** fetches school admission and test-score fields, packaged as a dictionary keyed by the string form of the school ID.
- **`get_cost_info(unitid)`** fetches the school's cost fields, including net-price income brackets and tuition, in the same school-keyed style.
- **`get_all_npt_info(unitid)`** fetches overall net price and all five income-specific net prices without the unrelated admission fields.
- **`get_tuition_info(unitid)`** fetches in-state and out-of-state tuition/fees.
- **`get_city_state(unitid)`** fetches the school's name, city, state, longitude, and latitude in a school-keyed dictionary.
- **`get_school_url(unitid)`** fetches its website field. As written, its local result variable may be unassigned if no record exists, unlike helpers that return an empty dictionary.
- **`get_sat_crit(unitid)`** fetches math, reading, and writing 25th/75th percentile SAT values.
- **`get_school_act_crit(unitid)`** fetches the corresponding ACT English, math, and writing values.
- **`get_school_list_from_satscores(math_sat_score, reading_sat_score)`** selects schools where supplied scores meet the stored 25th-percentile thresholds and prints/returns results. This is a rough score filter; the printed wording about acceptance is not a guarantee of admission.
- **`get_bracket(income)`** converts an income or bracket choice `a`–`e` into an `npt41`–`npt45` column name. The breakpoints are 30,000; 48,000; 75,000; and 110,000 dollars.
- **`get_npt(unitid, inc_bracket)`** selects the requested net-price column. The column name is interpolated into SQL, so callers must supply a trusted bracket name, such as one produced by `get_bracket`, not arbitrary browser input.
- **`get_programs_from_cipcode(cipcode)`** retrieves program records associated with a major code. It is a focused lookup, not the full filtered/paginated Explore workflow.
- **`get_mdn_earnings(program_id)`** looks up a program's reported median earnings. Its loop-based return variable can be missing if no record is found.
- **`get_program_id_fom_unit_and_cip(unitid, cipcode)`** looks up program IDs by school and major; the misspelling `fom` is part of the actual name. Multiple credential levels can match, and the loop retains the last result rather than selecting a particular credential. A missing match is also not handled cleanly.
- **`get_unit_and_cip_from_program_id(program_id)`** looks up a program's school and major identifiers. It has the same missing-result issue with its loop result.
- **`get_best_progs_from_cip(x, cip, criteria)`** joins program/school/major/ranking data, orders by the chosen ranking field, limits to `x`, and returns dictionaries including school, major, and earnings. The old search calls it with constant earnings criteria. The dynamic criteria and limit must remain trusted inputs. “Best” here means the selected statistic, not individual fit.
- **`get_major_id_from_cipcode(cipcode)`** converts an external major code to the internal table ID.
- **`get_cipcode_from_major_id(major_id)`** reverses that conversion.
- **`get_school_id_from_unitid(unitid)`** converts the external school identifier to the internal ID.
- **`get_unitid_from_school_id(school_id)`** reverses that conversion. All four conversion helpers assume a match and index the first result; they can raise if the identifier is absent.

### Older pagination and scanning helpers

- **`get_a_page(page, page_count, table_name, column_to_sort, order)`** computes an offset and fetches a page from schools, majors, or programs. It restricts table names and normalizes direction, but the column name is still interpolated without the current catalog's allowlist.
- **`paginate(table_name, last_id)`** fetches up to 2,000 rows with internal `id > last_id`, ordered by ID. This is cursor-style pagination rather than page-number offsets. Its table name must be trusted.
- **`scan_entire_table(table_name, batch_size=5000)`** is a generator. It repeatedly reads the next ID-ordered batch and yields rows one at a time until no rows remain. This avoids loading the entire table at once, but holds a connection while the generator is being consumed. `catalog_majors` uses it with the fixed table name `majors`.
- **`get_page_schools(...)`** joins schools, costs, and admissions, applies one dynamic comparison, and pages the results. Inner joins can omit schools lacking related rows.
- **`get_page_majors(...)`** is the older simple major-table pager with one comparison. The current Majors Explore tab uses `get_major_catalog_page`, not this function.
- **`get_page_program_recs(user_id, ...)`** joins stored program recommendations to programs, earnings, schools, costs, and admission fields; restricts by user; applies an optional comparison and page/sort settings.
- **`get_page_program_favs(user_id, ...)`** does the same for program favorites. The current favorites screen uses the lighter `get_program_favorites` instead.
- **`get_page_major_recs(user_id, ...)`** pages stored major recommendations joined to major names. The current chat uses `get_recommendations`, which also supplies evidence.
- **`get_page_major_favs(user_id, ...)`** pages major favorites joined to names. The current favorites/filter UI uses `get_major_favorites` instead.

Those older `get_page_*` helpers accept raw column names, comparison operators, and sort expressions. Parameters protect values such as `threshhold` (the spelling in the functions), but they do not protect the interpolated SQL structure. They are not interchangeable with the newer validated public-facing helpers.

### Current program queries

**`get_a_program(program_id)`** runs the joined query for a single detail page. It selects the major and college names, location, earnings, all cost brackets, score ranges, and the major description/source. It uses the program identifier as a bound parameter and returns a dictionary or None. One joined query avoids a separate network round trip for every fact shown on the detail page.

**`validate_program_filters(filters)`** validates provided school/major strings, lists of positive CIP codes, integer ranges for IDs/costs/admission percentages/SAT/ACT, degree levels 2/3, and consistent acceptance minimum/maximum. It raises ValueError rather than an HTTP response because it is a database-layer helper. Route code turns that into a useful 400. State/city length checks are in the route; this function is not a blanket validation of every possible key.

**`get_page_programs(page=1, page_count=25, sort_option='school_name', sort_order='ASC', filters=None)`** is the main program search:

1. Validate pagination and copy the filters so the caller's dictionary is not modified.
2. Validate recognized filter values.
3. Build a list of SQL conditions and a separate parameters dictionary. No filters produces `WHERE TRUE`.
4. Use an exact CIP or major name, a list of majors, school substring, location, degree list, cost limits, admission range, or score thresholds when supplied. Percent inputs are divided by 100 to match stored decimal rates.
5. Choose `ORDER BY` from a fixed map. Most sorts include `program_id` as a stable tie-breaker and put missing statistics last. The database helper supports more sort keys than the current HTML controls expose.
6. Join the program to school, major, costs, admissions, and earnings. Select only the fields needed for cards.
7. Expand `degrees` and `cipcodes` list parameters when present.
8. Calculate offset `(page-1)*page_count` and fetch `page_count+1` rows. For a 25-card page, the 26th row only answers whether Next should appear; it is not displayed.
9. Measure connection checkout separately from query/fetch time and print both durations.
10. Return `{'rows': [...], 'page': page, 'has_next': ...}`.

Why separate `is not None` from truth checks? A cost ceiling of 0 is a supplied value and must not be ignored. An empty `cipcodes` list is intentional “match no majors,” while no list (`None`) means no list restriction. Empty degrees means no degree restriction in this implementation. Those differences reflect UI decisions, not accidental Python syntax.

This query does not calculate a total number of pages. Deep OFFSET pages can become more expensive than the first page. Warm connections remove repeated setup work but do not make joins, sorting, or cloud round trips free.

### Saving a chat and ranking recommendations

**`save_chat_turn(user_id, user_message, turn)`** uses one `engine.begin()` transaction. It locks the user row, inserts the user message and assistant reply, deletes requested keyword pairs, and upserts additions. An upsert means insert if absent, otherwise update; `EXCLUDED.evidence` is the newly proposed evidence used to replace the old quote. Finally it refreshes recommendations using the same connection and returns them. If any step fails, the whole transaction rolls back.

The row lock serializes account saves. It does not retroactively make two simultaneously generated Gemini responses use the same fresh history; AI interpretation happens before this saving transaction.

**`_rank_majors_from_keywords(connection, saved_keywords)`** is the shared ranking core. It deduplicates saved keywords by ID and immediately returns an empty list if none exist. Its SQL:

1. Filters `major_keywords` to the saved IDs.
2. Groups by major and counts distinct matching keyword IDs.
3. Sorts highest count first, breaks ties by CIP code, and keeps six.
4. Joins those six to major names and their matching keyword labels.

A `WITH ranked_majors AS (...)` clause names the intermediate result so the outer query can fetch evidence-related rows for those ranked majors. Python groups those rows into one recommendation per major and attaches the evidence quote from each saved interest.

Example: a user has Biology, Helping People, and Research. If Major A matches all three and Major B matches two, A ranks first. Repeating the same interest does not multiply its score because the query counts DISTINCT IDs. No weighting or semantic similarity score is added at this SQL stage. More heavily tagged majors can naturally have more opportunities to match.

- **`get_recommendations_for_keywords(saved_keywords)`** opens a connection and calls the shared ranker. Guests use it without needing a permanent users row.
- **`_refresh_user_recommendations(connection, user_id)`** reads saved account keywords, ranks them, deletes the old `major_rec` rows for that user, and inserts the current results. It reuses the caller's transaction.
- **`create_recommendations(user_id)`** is a standalone way to lock the user's row and refresh saved recommendations in a transaction. Normal chat saving already refreshes them, so it does not need a second separate refresh call.
- **`get_recommendations(user_id)`** reads stored recommendation rows, joins the matching saved keywords and labels, and packages counts and evidence for display. It does not ask Gemini for another response. Evidence comes from current `user_keywords`, not a second copied evidence table.

### Guest database functions

- **`create_guest_session(guest_id)`** inserts the initial JSON state with empty messages/keywords/preferences/recommendations. The schema supplies creation and expiration defaults. It returns state and version.
- **`get_guest_session(guest_id)`** loads an unexpired row and returns it, or returns None when absent/expired.
- **`save_guest_session(guest_id, state, expected_version)`** serializes the object to JSON, updates only the unexpired matching version, increments version, and extends expiration by 24 hours. It returns the new version, or None for a conflict/expiration.
- **`delete_expired_guest_sessions()`** deletes expired rows and returns the deleted count. The CLI command calls this; normal expiration checks deny access even before cleanup deletes old rows.

### Current favorites, comparisons, and major catalog

- **`get_major_favorites(user_id)`** joins this user's `major_fav` rows to names and returns an alphabetized code/name list. It serves Favorites, chat favorite-button state, and program Explore's favorites filter.
- **`get_comparison_favorites(user_id, kind)`** selects one of two fixed SQL statements. Major comparisons join description/earnings and count related programs/distinct schools. Program comparisons join school, credential, earnings, optional costs, admissions, and score ranges. Both restrict favorites by user ID. Invalid kinds raise ValueError.
- **`is_program_favorite(user_id, program_id)`** uses `SELECT EXISTS` to return a Boolean for one saved pair.
- **`get_program_favorites(user_id)`** returns a light list with program ID, major, school, credential code, city, and state. It avoids loading every comparison statistic when only a favorites card is needed.
- **`get_major_name_suggestions(query)`** performs a case-insensitive substring search, escapes SQL LIKE wildcard characters `%` and `_` (using `!` as its escape character), orders results, and limits to 20. The route enforces query length.
- **`get_major_catalog_page(...)`** pages majors independently from programs. It validates page/size/search/sort/earnings filter and Boolean flags; supports partial-name matching, minimum reported earnings, favorites-only, and has-programs. It joins major descriptions/earnings and aggregated program/school counts, uses EXISTS for each user's favorite state, and returns 25 rows plus a next-page indicator. Missing counts become zero with COALESCE; missing earnings remain missing. Sorting supports names, earnings, and program counts, with stable CIP tie-breakers.
- **`get_major_info(cipcode)`** returns a description and source dictionary or `{}`. Detail/major catalog queries already include this data through joins; this remains a standalone helper.
- **`warm_database_connections(engine, size=5)`** checks out several connections simultaneously and runs `SELECT 1` on each. `ExitStack` keeps them all open until the loop finishes, then releases them together. Without that stack, immediately returning each connection could keep reusing one connection instead of creating five.

### Delete functions

These use transactions and restrict the delete by the identifiers passed:

- **`remove_user(user_id)`** deletes the user. The schema's ON DELETE CASCADE relationships remove dependent account rows.
- **`remove_from_major_fav(user_id, cipcode)`** removes one major favorite.
- **`remove_major_rec(user_id, cipcode)`** removes one stored major recommendation; a later refresh can recreate it if it still matches.
- **`remove_school_fav(user_id, program_id)`** actually removes a program favorite. The name is older than the current program-based feature.
- **`remove_program_rec(user_id, program_id)`** removes one stored program recommendation.
- **`delete_chatlog(user_id)`** deletes all account messages for that user. It does not automatically delete their keywords or favorites.
- **`remove_user_keyword(user_id, keyword_id)`** removes one saved interest. Calling this helper alone does not refresh recommendations; the main chat transaction coordinates both operations.

A database function accepting a user ID does not independently authenticate that person. The route must pass the verified session ID. This distinction is why server-side identity handling matters even with parameterized SQL.

## 8. Schema files and database relationships

The schema is PostgreSQL SQL. `public` is a schema namespace inside the selected database; `public.majors` means the majors table in that namespace. An unqualified `majors` depends on the connection's search path. Your current setup explicitly writes pandas uploads into `public`.

### What each SQL file does

- **`schemas/all_schema.sql`** is the combined reset/rebuild script that `db_setup.py` actually reads. It drops/recreates the catalog and account/guest tables and grants runtime access. Running it is a destructive rebuild, not a migration preserving existing data.
- **`schemas/data_schema.sql`** is the catalog-table reset/create subset. Its CASCADE drops can affect relationships from user tables too; it is not an isolated harmless catalog read.
- **`schemas/user_schema.sql`** is the account/guest-table reset/create subset. It assumes referenced catalog tables already exist. It deletes existing account-related contents when run.
- **`schemas/app_runtime_perms.sql`** creates `app_runtime` if missing, grants its privileges, and assigns it to `python_connection`. It does not rebuild tables. The same permission block also appears at the end of `all_schema.sql`; editing a standalone subset does not automatically update the combined file.

`app_runtime` is a NOLOGIN role: a reusable bundle of privileges, not a separate password login. It gets schema usage, SELECT on catalog tables, read/write/delete on account and guest tables, and sequence usage for generated account IDs. `GRANT app_runtime TO python_connection` gives those permissions to the runtime database login. It does not revoke other preexisting privileges, such as elevated role memberships. SQL roles are separate from Google IAM roles and Clerk users.

### Catalog tables

| Table | Fields and purpose |
|---|---|
| `schools` | Internal `id`; unique `unitid`; `opeid6`; school name `instnm`; undergraduate enrollment `ug12mn`; `city`, `stabbr`, longitude/latitude; institutional level `iclevel`; website `insturl`. |
| `majors` | Internal `id`, unique `cipcode`, and major name `cipdesc`. This is the major catalog. |
| `major_info` | One row per unique CIP code, with `mdn_earnings`, `major_description`, and `description_source`. |
| `programs` | Internal `id`, unique `program_id`, school `unitid`, major `cipcode`, and credential level `credlev`. Foreign keys connect programs to schools and majors. |
| `adm_crit` | One row per unique school ID, with decimal admission rate and SAT/ACT percentile fields. These statistics belong to the school, not separately to each program. |
| `cost_info` | One row per unique school ID: overall `npt4`, income brackets `npt41`–`npt45`, and in/out-of-state tuition fees. |
| `program_rank_crit` | One row per unique program ID: reported four-year earnings median and earnings cohort count. The count remains stored even though Compare no longer displays it. |
| `keywords` | Keyword ID and text label. IDs are referenced by user interests and major mappings. The schema does not currently make keyword text unique, although `interpret_message` requires unambiguous names. |
| `major_keywords` | Links a CIP code to a keyword ID. This is a many-to-many bridge: one major can have many keywords, and one keyword can describe many majors. The schema does not currently enforce uniqueness of the pair; ranking uses DISTINCT to avoid duplicate counts. |

The unique school/program IDs on optional statistic tables prevent a join from multiplying a program card through multiple matching statistic rows. Uniqueness enforces at most one row, not that every school/program must have a statistic row.

### Account and guest tables

| Table | Fields and purpose |
|---|---|
| `users` | Generated local `id`, unique non-null `clerk_user_id`, and creation timestamp. No email/password/token is stored here. |
| `user_info` | A unique `user_id` plus SAT/ACT fields, maximum cost, city/state, search coordinates, and maximum distance. It provides room for preferences but is not populated by the current chat workflow. |
| `user_keywords` | User ID, keyword ID, and evidence. `UNIQUE(user_id, keyword_id)` prevents one user having duplicate rows for the same interest. |
| `chatlog` | User ID, message content, sender, and timestamp. `CHECK(sender IN ('user','assistant'))` rejects other sender labels. The unquoted SQL `createdAt` identifier is folded by PostgreSQL; keep this in mind if using quoted names later. |
| `major_rec` | User ID, major code, and number of matching keywords, unique per user/major. These are recalculated account recommendations. |
| `program_rec` | User ID and program ID, unique per pair. The schema/helper exist, but the Gemini chat does not currently create a personalized program recommendation pipeline. |
| `major_fav` | User/major pairs, unique per pair. Saving a favorite is separate from being recommended that major. |
| `program_fav` | User/program pairs, unique per pair. Favorites preserve a specific school/major/credential offering. |
| `guest_sessions` | Random text primary key, JSONB state, integer version, creation timestamp, and expiration timestamp. A CHECK requires state to be a JSON object. An expiration index supports cleanup. |

`SERIAL` supplies generated IDs through a sequence, hence the runtime role's sequence grants. `TIMESTAMPTZ` is PostgreSQL's abbreviation for `TIMESTAMP WITH TIME ZONE`, used for time-zone-aware instants. `NOT NULL` means a field cannot be missing. `ON DELETE CASCADE` on the account relationships removes dependent rows when a user is deleted.

A useful relationship sketch:

```text
users.id ------ user_keywords ------ keywords.id
                                      |
                                      | major_keywords
                                      v
users.id ------ major_fav -------- majors.cipcode ------ major_info
users.id ------ major_rec --------       |
                                        | programs.cipcode
                                        v
users.id ------ program_fav ------ programs.program_id ------ program_rank_crit
users.id ------ program_rec ------       |
                                        | programs.unitid
                                        v
                                     schools.unitid ------ cost_info
                                            |------------- adm_crit
users.id ------ chatlog
users.id ------ user_info

guest_sessions is separate; it stores temporary state as JSON.
```

## 9. Data preparation and every data file

### `db_setup.py`

**`main()`** is the only named function. It is an administrative import/reset workflow and is not called by normal page requests.

1. Load settings and create the IAM administrative engine.
2. Read the large field-of-study source file. Keep selected identifiers, names, credentials, and earnings columns. Keep associate and bachelor's rows only.
3. Convert the `PS` suppression marker to missing values, then drop programs missing either the earnings median or earnings cohort count.
4. Read the large institution source. Combine each public/private net-price column pair by taking the public value when available, otherwise the private value.
5. Keep selected institution columns and remove schools with missing undergraduate enrollment. Restrict schools and programs to school IDs present in both filtered datasets.
6. Write the smaller intermediate `FieldOfStudy.csv` and `Institution.csv`, then reread them.
7. Assign `program_id` as dataframe row index plus one. These IDs depend on dataset row order and should not be assumed stable across a differently ordered rebuild.
8. Split the data into normalized school, major, program, cost, admission, and earnings dataframes. Lowercase column names to match SQL names.
9. Compute each major's median across its program-level earnings medians. This is not a weighted median of all graduates. Merge those values into the base description data.
10. Read the prepared keyword list and ID-based major-keyword mappings.
11. Write derived table CSVs.
12. Read `all_schema.sql`, split statements using sqlparse, and execute them inside a transaction.
13. Upload the nine catalog dataframes in dependency order using `to_sql(..., schema='public', if_exists='append', index=False, chunksize=1000, method='multi')`.
14. Dispose the engine and close the admin connector on normal completion.

`if_exists='append'` does not protect existing data from the earlier reset script. The reset has already recreated the tables. The schema step and all subsequent table uploads are not one encompassing transaction; an upload failure can leave a partially loaded database. Cleanup is at the end rather than a `finally` block.

Paths such as `./data/...` are relative to the shell's current directory. Run-location errors can therefore cause “file not found” even if the data exists beside the project. `app.py`'s explicit .env path does not make every path in this separate script absolute.

The commented-out scoring formulas do not run. The live major earnings calculation uses a median, not those experimental scores. Ordinary browsing reads PostgreSQL, not CSVs on each request.

### `data/`

- **`Most-Recent-Cohorts-Field-of-Study.csv`** is the large source dataset for programs, credentials, major codes/names, and program earnings. The setup script selects only some columns and rows.
- **`Most-Recent-Cohorts-Institution.csv`** is the large institution source for school names, location, costs, admissions, and enrollment.
- **`FieldOfStudy.csv`** is the smaller filtered program intermediate produced by setup.
- **`Institution.csv`** is the filtered institution intermediate with combined net-price columns.

The guide follows the loader and file headers; it is not a row-by-row audit of these large datasets. Because setup filters out some missing data and credential levels, the database is not a complete listing of every original source program.

### `tables/`

These files are preparation inputs or exported snapshots, not separate live databases.

| File | Role in the current project |
|---|---|
| `base_major_info.csv` | Setup input: CIP code, description, and description source. |
| `kwd_list.csv` | Setup input: keyword text and explicit keyword ID. This becomes `keywords`. |
| `major_keywords.csv` | Setup input: CIP code and keyword ID pairs. This becomes the recommendation bridge table. |
| `kwd_pairs.csv` | Text-based CIP/keyword pairs. It is not read by the current setup script; it appears to be a preparation artifact for the ID-based mapping. |
| `schools.csv` | Setup output: school identifiers, name, enrollment, location, institution level, and URL. |
| `majors.csv` | Setup output: distinct CIP codes and descriptions/names. |
| `programs.csv` | Setup output: generated program ID, school ID, CIP code, and credential level. |
| `adm_crit.csv` | Setup output: school admission rates and score percentiles. |
| `cost_info.csv` | Setup output: school net prices and tuition. |
| `program_rank_crit.csv` | Setup output: program earnings medians and cohort counts. |
| `major_info.csv` | Setup output: descriptions/source merged with calculated major-level earnings summaries. |
| `majors_excelsheet.xlsx` | Spreadsheet artifact with `Sheet1`; no current application or setup code reads it. Its name suggests a major-authoring worksheet, but the filename alone does not establish how it was created. |
| `majors_with_keywords_and_descriptions_corrected.xlsx` | Another spreadsheet artifact with `Sheet1`; also not read by the current loader. Any manual edits here do not automatically update the CSV inputs or database. |

The `tables` directory mixes inputs and outputs. Editing an output CSV alone will not necessarily affect the next rebuild, because setup regenerates it from its inputs.

## 10. Every HTML template

All templates live in `degree_path/templates/`. `{{ ... }}` inserts a value. `{% if ... %}` chooses content. `{% for ... %}` repeats it. `url_for` builds a URL from a Flask endpoint. Jinja escapes ordinary variable output in HTML; browser-created messages also use textContent instead of interpreting text as HTML.

- **`base.html`** is the shared document shell for most pages. It loads theme/app CSS, the favicon, and the optional form keyboard helper; includes navigation; and defines `extra_head` and `content` blocks. A child template supplies those blocks rather than duplicating the whole document. It includes a skip link for keyboard navigation.
- **`_navigation.html`** is a reusable partial included by all current page shells. It displays Sign in/Sign out based on the session, plus Favorites, Compare, and Settings links. Its `data-user-id`, `data-csrf`, and public Clerk key attributes let account/API scripts read server-rendered state. It also supplies account status/retry elements and loads `account-auth.js`.
- **`_favorites_signin.html`** is the shared guest gate for Favorites and Compare. The caller sets `gate_title`; it displays a sign-in button and Back to home. The sign-in button uses the shared modal handler, not a separate sign-in page.
- **`_explore_tabs.html`** displays Programs and Majors links, marks the active view with `aria-current`, and navigates to a fresh view URL. Switching tabs drops the other view's filter parameters.
- **`home.html`** is a standalone document rather than a child of base. It loads Bootstrap CSS from a CDN plus local theme/home CSS, includes the shared navigation, and has two feature-card links to chat and Explore. `home.js` provides a decorative hover glow. A comment preserves the adapted layout's license attribution.
- **`guided_chat.html`** is the standalone Gemini chat document. It provides empty message/recommendation containers and disabled input controls until initialization succeeds. It includes the shared navigation and loads `chat-api.js` before `guided-chat.js` using deferred scripts. It includes CSRF and Explore URL data attributes, status areas, retry button, and a no-JavaScript message. The inline public Clerk-key assignment is public configuration, not a secret.
- **`chat.html`** extends base for the older major-name search. A normal POST form sends `question` plus a hidden CSRF token. Returned results show matching major names and sample programs. Its link to `/questionnaire` leads to the actual AI chat.
- **`explore.html`** extends base for programs. Its GET form contains school-name search, sort, major mode/name/favorite selections, degree checkboxes, location, cost, and acceptance filters. Hidden fields preserve view/degree compatibility and a CIP code when relevant. It loops over `data.rows` for cards and creates Previous/Next links from `pagination`. Card names, costs, and scores come from server SQL. Signed-in users get favorite buttons/scripts; guests get a link to the sign-in gate. Missing card facts are generally omitted. Although earnings can drive sorting, the current card facts block does not display earnings; details show it.
- **`explore_majors.html`** extends base for the independent major catalog. It has partial-name search, major sorts, minimum earnings, has-programs, and optionally favorites-only controls. Each card shows earnings summary, program/school counts, an expandable description/source, favorite state, and a link to programs restricted to that major. Favorite states are already part of the server query. Its GET form works as ordinary navigation and does not load `explore.js`.
- **`program_details.html`** displays one program's name/school/location, earnings, overall net price, major description, tuition, all income brackets, and SAT/ACT ranges. Missing values have explicit fallbacks. Logged-in users get the single-program favorite controller; guests get the Favorites sign-in link. The school costs are not program-specific tuition estimates.
- **`favorites.html`** chooses the guest gate or signed-in favorites interface. The latter has Majors/Programs buttons, status/retry controls, and an initially empty card container populated by `favorites.js`. The template does not query the database itself.
- **`compare.html`** similarly gates guests. Signed-in content contains type buttons, a sidebar of future choices, selection count, reset/retry controls, and an empty table. It loads formatting logic before the comparison controller. The text explains which statistics have a meaningful higher/lower comparison and that missing data is not zero.
- **`error.html`** shows a generic title, the supplied HTTP error description, and a Return to chat link. That link currently targets the older `/chat` route, not `/questionnaire`.
- **`profile.html`** says profiles and saved preferences are coming soon. It does not contain an editable connected account profile.
- **`settings.html`** says application preferences are coming soon. It has no working settings form or save route.

The leading underscore on partial filenames is a convention, not a special Flask restriction. A template has no database connection simply because it displays a table; the route must pass its data.

## 11. Every browser JavaScript file and its functions

Scripts live in `degree_path/static/js/`. An immediately invoked function such as `(() => { ... })()` runs once when the script loads and keeps local variables out of the global scope. Anonymous event handlers run later on clicks, typing, or other events. `async`/`await` lets a handler wait for network results without freezing browser rendering.

### `chat-api.js`

This publishes `window.chatApiReady`, a promise containing shared API methods. Despite its name, favorites also use it. It captures the user ID rendered in navigation when the page loaded.

**`apiRequest(path, method, body)`** sends a same-origin fetch, the captured `X-App-User-ID`, and JSON/CSRF headers for POST. It JSON-encodes the body, parses the response, throws an error for unsuccessful status codes, and returns successful data. Cookies are sent by the browser; it does not fetch a new Clerk token for each request.

The returned wrapper methods are:

- **`load()`**: GET the chat state.
- **`send(message)`**: POST one chat message.
- **`isSignedIn()`**: whether the page was rendered with a user ID. This is a UI hint; the server remains authoritative if login expires later.
- **`loadProgramFavorites()`**: GET the saved program list.
- **`loadProgramFavorite(id)`**: GET whether one program is saved.
- **`setProgramFavorite(id, favorite)`**: POST the desired saved state for a program.
- **`loadFavorites()`**: GET saved majors.
- **`setFavorite(cipcode, favorite)`**: POST the desired saved state for a major.

### `account-auth.js`

This handles all `[data-auth-action]` buttons, including those in the guest gate. Normal visits do not load Clerk. It uses browser `sessionStorage` for pending login/logout flags, which is different from Flask's signed session cookie.

- **`showStatus(message)`** updates the shared status text and hides it when empty.
- **`loadScript(src, key)`** creates an external script element, optionally attaches the publishable key, and returns a promise. Load succeeds, network failure rejects, and a 20-second timer rejects an excessively slow load.
- **`loadClerk()`** decodes the Clerk domain from the publishable key, validates the domain, loads Clerk UI and Clerk JS when absent, initializes Clerk, and returns it. `clerkPromise` shares one initialization attempt; failure clears the promise for a later retry.
- **`post(path, token)`** sends a CSRF-protected JSON request, optionally with a bearer token. It is used for app login/logout.
- **`completeLogin(clerk)`** avoids duplicate completions, obtains the current Clerk token, posts to `/api/auth/session`, clears the pending flag, closes the modal, and reloads the same page. Reloading is needed so the HTML has the verified session ID and rotated CSRF token.
- **`signIn()`** loads Clerk after an explicit click. If Clerk already has a session, it verifies that session with Flask. Otherwise it subscribes to Clerk state changes and opens the sign-in modal. OAuth may visit an external provider and then returns to the same page.
- **`signOut()`** clears the Flask session first, sets a pending external-logout flag, then attempts Clerk sign-out. It reloads even if Clerk is unavailable, so the app no longer shows authenticated access. A later retry can finish external logout.

The button click handler prevents concurrent clicks, disables the clicked control during work, chooses sign-in/out, displays errors, and restores the control. The retry-logout handler repeats Clerk sign-out and removes the pending flag when successful. The startup pending-login block completes only a previously requested OAuth sign-in; it does not automatically prompt ordinary guests.

### `guided-chat.js`

This is the Gemini chat UI controller, not the AI itself. It waits for the shared API, loads saved chat, optionally loads major favorite IDs, then enables input.

- **`createFavoriteButton(cipcode)`** makes a button for a recommendation. Its nested **`updateLabel()`** chooses guest, saved, unsaved, or unavailable text and `aria-pressed`. Its click handler sends the desired state, updates the local favorite-ID Set only on success, and displays a status message. A guest click currently tells the visitor to use account sign-in; it does not automatically open the modal or navigate to the gate.
- **`setStatus(message)`** updates the chat status line.
- **`setBusy(value)`** tracks an active send, disables input/send, and updates the message area's busy attribute.
- **`showStorageNote(mode)`** shows account or temporary guest storage text. The guest wording refers to the browser's session, but the actual message data is in the temporary database row, not inside the cookie.
- **`addMessage(role, content)`** creates the correct user/assistant bubble and label, inserts text with `textContent`, preserves line breaks, and scrolls to the latest message. It does not execute HTML returned by Gemini.
- **`renderHistory(history)`** clears old bubbles and draws the loaded messages. With no history it displays a local greeting; that greeting is not itself a saved Gemini turn.
- **`renderRecommendations(recommendations)`** clears old cards, hides the panel if empty, and creates each major's title, match count, evidence list, program-exploration link, and favorite button.
- **`sendMessage()`** prevents duplicate submits, validates message length, sets the busy status, calls the API, and appends both messages only after success. It clears the input on success; on failure it keeps the typed text and offers Reload chat. A finally block re-enables controls.

Clicking Send or pressing Enter (without Shift and outside text composition) invokes sending. The reload handler reloads the page. Initialization leaves sending disabled if the saved chat cannot be loaded, so a failed load is not mistaken for an empty conversation. Failure to load favorites can show a warning while chat itself remains usable.

### `explore.js`

This adds convenience to the program filter form; SQL filtering still occurs on the server.

- **`updateMode()`** shows/enables the major-name or favorite-major fields for the chosen mode. Disabled irrelevant inputs are not submitted. A legacy CIP hidden field permits a linked major filter without requiring a typed name.
- The **major-name input handler** removes an old hidden CIP code after the user starts editing, clears suggestions, and debounces lookup by 250 ms. Its asynchronous callback requests `/api/major-names`, creates datalist options, and uses an incrementing search version so a slow old response cannot replace newer suggestions.
- The **form submit handler** records selected degree values in a compatibility hidden field. The route also understands the actual repeated checkbox values.
- **`showExploreLoading()`** reveals the loading indicator and marks results busy while full-page navigation runs.
- Pagination/reset/empty-result links call that helper for ordinary clicks, but do not intercept modified clicks intended for a new tab.
- The **`pageshow` handler** clears a restored loading state when browser Back shows a cached document.

### `favorites.js`

Maintains the selected type (`majors` or `programs`) and a request version counter.

- **`emptyMessage()`** returns the appropriate no-favorites guidance for the current type.
- **`render(favorites, requestVersion)`** creates cards. Program cards show school/credential/location and detail links; major cards link to Explore filtered by CIP. Each remove handler calls the matching API, then removes the card only after success. If the user has switched tabs meanwhile, a version check prevents the old response from altering the current tab.
- **`load(nextKind=kind)`** changes the mode, clears old cards, updates active tab and loading status, and calls the matching list API. It ignores stale responses, renders current data, and offers retry on failure.

Tab handlers call `load` for that type; Retry reloads the current type. Initial loading defaults to majors.

### `major-card-favorites.js`

This script adds click handlers to the server-rendered major catalog buttons. It needs no initial favorites-list fetch because `get_major_catalog_page` already included `is_favorite`. Each handler derives the desired state from `aria-pressed`, disables the button, posts the change, then updates label/state/status on success. Errors preserve the last confirmed state. There are no separately named helper functions.

### `program-card-favorites.js`

This handles all program cards together.

- **`label(button)`** reads a local Set of saved program IDs and sets the label and pressed state.
- **`load()`** makes one favorites-list request for the whole result page, fills the Set, labels/enables all buttons, or marks them unavailable with a retry option. It does not make one status request per card.
- Each **button click handler** posts the opposite saved state, updates the Set only after success, relabels the clicked button, and reports the result. Failed requests retain the confirmed state.
- The **retry handler** calls `load` again. Initialization returns immediately if there are no program buttons.

### `program-favorite.js`

This is the single-program detail-page variant.

- **`render()`** updates its label and pressed state from the local `favorite` Boolean.
- **`load()`** fetches saved state for this program, enables the button on success, or offers Retry.
- The **click handler** posts the opposite state, applies the confirmed result, and gives save/remove feedback. The retry handler reloads state.

### `compare.js`

This controller keeps `kind`, loaded items/metrics, selected IDs, a request number, and an AbortController. The selection limit is three; fewer than two does not show a table.

- **`title(item)`** uses the major name alone for majors or adds school and credential for programs.
- **`renderTable()`** clears the prior table, updates the count and Clear button, and shows a placeholder until two items are selected. It creates one column per selection plus a Statistic column. For each metric, it formats values and asks `ComparisonValues.highlights` for winner labels. The three-item data attribute controls table width in CSS.
- **`updateChoices()`** synchronizes checkbox state and disables unselected choices when three are selected. Selected choices remain enabled so users can uncheck them.
- **`renderChoices()`** builds sidebar labels/checkboxes from the loaded favorites. Each change handler enforces the maximum and redraws choices/table.
- **`load(nextKind)`** resets selections and table, aborts an earlier request, increments request version, updates headings/tabs, and fetches this user's `/api/compare` data. Both the abort and version check protect against late responses. It shows retry or insufficient-favorites guidance as appropriate.

Mode buttons reset and load the selected type; Clear empties selection without another database request; Retry reloads the current type. Once favorites/statistics are loaded, changing selected checkboxes builds the table locally rather than querying SQL per click. There is no saved comparison selection in the database.

### `comparison-values.js`

This is pure formatting/ranking logic, usable in the browser or Node tests.

- **`numeric(value)`** accepts only finite JavaScript numbers. It excludes null, undefined, NaN, and numeric-looking strings.
- **`highlights(values, direction)`** returns one label per value. With `higher` or `lower` and at least two reported numbers, it finds the maximum/minimum and labels winners, including ties. Otherwise it returns empty labels. It does not invent a winner when only one value is reported.
- **`format(value, type)`** formats money, percentages, ordinary numbers, text, or complete two-number ranges. Missing/invalid values show `Not reported`; zero stays valid.

It exports `ComparisonValues` in the browser or `module.exports` in Node. Its ability to handle more than three numbers in tests does not change the UI's three-selection limit.

### `forms.js`

A small keyboard enhancement for elements with `data-enter-submit`: its keydown handler submits the associated normal form on Enter unless Shift is held or text composition is active. This supports the old search textarea. It has no AI or database behavior.

### `home.js`

For each feature card, the pointermove handler calculates the pointer position as percentages of the card's rectangle and sets CSS custom properties `--mx` and `--my`. CSS uses them for a glow. Pointerleave removes them to restore the resting position. Navigation remains a normal link without JavaScript.

### `clerk-config.js`

This is an older browser configuration file assigning a hardcoded public publishable key. Current templates do not load it: they receive the public key from Flask configuration through navigation/template data. It should not be mistaken for the active source of authentication settings. No secret key belongs in browser files.

## 12. Comparison rules in `degree_path/comparison.py`

This small Python file defines the meaning of comparison rows rather than fetching data.

**`MAJOR_METRICS`** describes earnings, program count, school count, description, and source. Each metric has a key, label, display format, and optionally a preferred direction and explanatory note.

**`PROGRAM_METRICS`** starts with school/location/credential/earnings, then loops to add cost rows, admission/enrollment, and SAT/ACT ranges. Earnings use `higher`; costs use `lower`. Counts, admission rates, and scores have no universal best direction. **`CREDENTIALS`** maps numeric codes to readable labels.

**`comparison_payload(kind, rows)`** copies query dictionaries and normalizes program fields: converts credential codes to names, joins city/state, combines each score's 25/75 values into a range, and converts a PostgreSQL Decimal admission rate to float for browser number formatting. It returns `{kind, items, metrics}`. Major items need less transformation. The route validates kind before calling it.

Highlighting occurs in browser `comparison-values.js` using these rules. No total “best school” score is computed.

## 13. Remaining Python helper: `degree_path/forms.py`

**`TextInputForm`** is a WTForms Form subclass with a required `text` textarea field. **`validate_text(value, limit=2000)`** rejects non-string inputs, creates that form, applies a Length validator with the requested limit, and returns None on success or the first validation error on failure.

The current routes perform their own explicit validation (`text_value`, chat validation, and filter parsing); they do not import this helper. It remains a small older validation utility. It does not handle login or sessions.

## 14. Every stylesheet and image

CSS files contain style rules rather than Python routes or database functions. A selector identifies HTML elements; its declarations control layout, color, spacing, and interaction appearance. Media queries change layouts for small screens or reduced-motion preferences. These files do not fetch data or change recommendation rankings.

- **`static/css/theme.css`** defines shared color/background variables, base fonts and links, navigation styling, account-button/status styling, and shared responsive behavior. Other CSS files use variables such as `--panel`, `--accent`, and `--mint`.
- **`static/css/app.css`** provides the shared page shell, panels, typography, form controls, buttons, tables, old chat/search cards, spacing, and mobile adjustments. It styles pages extending `base.html`.
- **`static/css/home.css`** styles the standalone landing page: hero area, feature cards, icons, gradients, pointer-following glow, hover movement, and reduced-motion behavior. Some older selectors coexist with the newer shared navigation.
- **`static/css/guided-chat.css`** styles the standalone Gemini page: centered chat panel, scrolling history, user/assistant bubbles, input controls, status notes, recommendation cards, evidence lists, and mobile spacing.
- **`static/css/explore.css`** styles the two-column filters/results layout, program and major cards, statistic blocks, pagination, loading indicator/spinner, major-filter controls, tabs, and narrower-screen layouts. It is shared by both Explore views.
- **`static/css/favorites.css`** styles the type buttons, responsive card grid, card links, and disabled favorite controls.
- **`static/css/compare.css`** styles type buttons, sidebar choices, the comparison grid, scrollable table, best-value cells, badges, focus states, and mobile stacking. Three selected items increase the table's minimum width so cells remain readable.
- **`static/css/program-details.css`** styles the detailed hero, college monogram, earnings/cost summary, description, tuition panels, income-price table, test-score rows, footer, and responsive columns.
- **`static/css/profile.css`** contains older profile/auth component centering and account-action styles. Current templates do not load this file, so its existence alone does not make those rules active.
- **`static/img/favicon.png`** is the browser-tab icon used by templates linking it. It has no application logic.

Some styles override earlier declarations later in the same file. That is normal CSS cascading: the applicable rule with stronger precedence wins. Changing a class in HTML may require matching CSS and JavaScript selectors to change too.

## 15. Tests: what each file and helper checks

These tests are offline checks. They cannot prove that real Cloud SQL permissions, current Gemini availability, external certificates, or a deployed Clerk application work. This explanation pass inspected the tests; it did not rerun them or call the cloud services.

### `tests/test_chat_service.py`

`ChatServiceTests` uses a mocked Gemini client. **`setUp()`** creates a one-keyword catalog and a sample response. **`call_service(payload, saved=None)`** injects a mock client's response into the real interpreter and retains the mock so tests can inspect the outgoing request.

- **`test_valid_turn_and_request_context`** checks translation from name to ID and the outgoing latest-message/history/system-instruction context.
- **`test_invalid_responses_are_rejected`** checks missing text, invalid JSON, and missing schema fields.
- **`test_unknown_name_and_invented_evidence_are_rejected`** checks unknown keyword names, quotes not in the user's text, and incorrectly typed names.
- **`test_conflicting_changes_are_rejected`** checks that one interest cannot be added and removed together.
- **`test_existing_additions_can_update_evidence`** confirms already-saved interests can appear in additions to refresh their evidence.
- **`test_only_saved_keywords_can_be_removed`** rejects removing an unsaved keyword and converts valid removals to IDs.
- **`test_provider_failure_propagates`** checks that an external failure reaches the caller rather than becoming a fake successful response.
- **`test_import_does_not_load_database_module`** starts a subprocess to confirm importing the interpreter alone does not initialize the database.

The `unittest.main()` block permits running the file directly.

### `tests/test_comparison_data.py`

`ComparisonDataTests.setUp()` creates an in-memory SQLite engine, attaches another in-memory database as `public`, makes small fixture tables, and inserts two users' favorites. It extracts selected real functions from `db_functions.py` using Python AST rather than importing the module and initializing cloud credentials. `addCleanup` disposes the fixture engine. This executes the selected real query code against fixtures, but is not a complete PostgreSQL integration test.

- **`test_only_owned_favorites_and_missing_optional_data`** checks account isolation and preservation of favorites without optional statistics.
- **`test_program_save_is_idempotent_and_removal_is_scoped`** checks saving twice does not duplicate a favorite, invalid programs fail, and removal leaves another user's data intact.
- **`test_program_favorites_list_is_scoped_and_preserves_credential`** checks the lightweight favorites list's identity and degree fields.
- **`test_decimal_rates_and_partial_scores`** checks Decimal conversion, incomplete score ranges, comparison directions, and absence of the cohort-count metric.
- **`test_program_major_filters_exact_name_union_and_empty`** checks exact major names, multiple selected majors, intentional empty selection, combined filters, paging, invalid input, and a SQL-like string treated as data.
- **`test_major_suggestions_match_names_and_escape_wildcards`** checks partial names and literal wildcard handling.
- **`test_major_catalog_filters_sort_pagination_and_user_scope`** checks name/earnings/program/favorite filters, missing values, sort options, pagination, and invalid arguments.
- **`test_program_school_search_and_sort_remain_program_specific`** checks school-name matching and sorting program results by program earnings.

### `tests/test_session_auth.py`

`SessionAuthTests.setUpClass()` installs a fake `db_functions` module and creates Flask with test settings, avoiding Cloud SQL. **`setUp()`** creates a fresh test browser, resets mocks, and initializes CSRF. **`login(signed_in=True)`** supplies a mocked Clerk authentication result and submits the actual login endpoint.

- **`test_verified_login_and_cookie_only_favorites`** checks login stores the local user and later favorites calls do not call Clerk again.
- **`test_login_persists_for_24_hours_without_sliding_expiration`** checks the persistent cookie/deadline and that a normal later request does not move it.
- **`test_navigation_uses_session`** checks Sign in/out labels and absence of the old Profile navigation link.
- **`test_invalid_token_and_untrusted_user_id_cannot_login`** checks a failed Clerk result or a supplied arbitrary local user ID does not establish login.
- **`test_csrf_required_for_login_and_logout`** checks missing CSRF prevents these POST actions.
- **`test_logout_clears_account`** checks all Flask session fields and cookie are cleared, including unrelated guest state.
- **`test_expired_login_and_stale_tab_rejected`** checks expiration and an old tab's identity header.
- **`test_account_switch_rejects_old_tab`** checks a mismatched page identity does not read favorites.
- **`test_chat_and_explore_skip_account_choice`** checks direct navigation, compatibility redirects, and the current chat shell.
- **`test_guest_favorites_has_signin_and_home_without_data_requests`** checks the guest gate does not load protected favorite scripts/data, while signed-in users get type tabs.
- **`test_comparison_requires_login_and_valid_kind`** checks comparison access and kind validation.
- **`test_comparison_reads_only_session_user`** checks a URL-supplied different user ID cannot change query ownership.
- **`test_program_favorite_requires_login_and_csrf`** checks program save/remove identity, CSRF, types, and nonexistent records.
- **`test_program_favorite_list_uses_session_and_returns_links`** checks list ownership, credential labels, and detail URLs.
- **`test_explore_cards_offer_favorites_for_guests_and_users`** checks the right favorite control/script appears in each mode.
- **`test_explore_major_search_and_favorite_selection_persist`** checks selected majors and degree filters survive navigation and unowned selections are rejected.
- **`test_major_name_api_short_query_needs_no_database`** checks short searches return empty and overly long searches fail.
- **`test_explore_tabs_separate_catalogs_and_keep_major_filters`** checks major view does not use program search, filters survive pagination, favorites scope is trusted, and program sorts remain separate.

The `unittest.main()` block enables direct execution.

### JavaScript test infrastructure

The browser-controller tests use Node's `assert`, `fs`, and `vm` to execute scripts against small fake document objects. They are not full browser rendering tests.

Where present, the fake **`Element` constructor** creates simple children/dataset/attributes storage. **`appendChild`**, **`append`**, and **`replaceChildren`** model adding/replacing DOM children. **`remove`** removes a node from its fake parent. **`setAttribute`** records state; in the Explore fixture **`setAttribute`** and **`removeAttribute`** are no-op stubs because their visual result is not under test. **`addEventListener`** records callbacks for the test to invoke. **`querySelectorAll`** finds fake descendants or returns prepared fixture controls. These are test utilities, not production page functions.

**`flush()`** yields through `setImmediate` so promise continuations finish. **`deferred()`** creates a promise whose resolution the test controls, letting it simulate slow responses arriving out of order. Top-level async test functions run the scenarios; their `.catch` handlers log failures and set a nonzero process exit code.

- **`tests/test_account_auth.js`**: **`fixture(...)`** builds fake navigation, Clerk, fetch, location, and sessionStorage; its **`element(...)`** helper builds simple controls. Tests prove normal visits do not initialize Clerk, explicit clicks open the modal, sign-in exchanges a token then reloads, OAuth continuation finishes, Flask logout happens before external logout, and failed external logout can be retried. Mock Clerk callbacks emulate SDK behavior rather than authenticating real tokens.
- **`tests/test_compare_ui.js`**: uses fake Elements, **`flush()`**, and **`reply(index, items)`**, which resolves a queued fake API response. Tests selection minimum/maximum, rejection of a fourth selection, table clearing, tab reset, insufficient favorites, identity headers, and stale-response protection even if abort is ignored.
- **`tests/test_comparison_values.js`**: imports the actual pure formatting functions and directly asserts higher/lower selection, zero handling, missing/NaN exclusion, ties, money, percent, and range formatting. It has no additional named functions. Some arrays have four values to test the generic utility, not the three-item UI limit.
- **`tests/test_explore_filters.js`**: uses a fake Element class and controllable timer/fetch callbacks. Tests mode visibility/disabled fields, multi-selection before Apply, required name search, and older autocomplete responses not overwriting newer ones.
- **`tests/test_favorites_ui.js`**: uses Elements, **`deferred()`**, **`flush()`**, and a local **`request(kind)`** queue helper. Tests switching tabs while requests are in flight, program removal via the right endpoint, one batch favorite-status request for all cards, and keeping confirmed state after a failed save.

From the project directory, the existing Python suite can be run with `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`. JavaScript tests can be run individually with `node tests/test_account_auth.js` and the analogous filenames. These commands are examples, not a claim that they were run during this walkthrough.

## 16. Repository, editor, documentation, and generated files

- **`README.md`** contains basic setup instructions, but some text describes an earlier account-choice and incomplete-integration version. Its reference to `.env.example` does not correspond to a file in the inspected inventory. Use current source behavior when the README conflicts.
- **`CLERK-SETUP.md`** documents an earlier integration, including older startup/config script references. The active login flow is `account-auth.js` → `/api/auth/session` → `auth.py` → signed Flask session.
- **`AGENTS.md`** contains an instruction for coding tools: commit messages must end with ` (codex)`. It has no effect on the running website.
- **`.gitignore`** excludes Python caches/bytecode, `.venv`, `.env`, `instance`, data/table directories, testoutput, and the local admin connector from normal Git tracking. Ignoring a path does not delete it, encrypt it, or untrack a file that was already committed.
- **`.vscode/settings.json`** currently has an empty Python environment-projects list. It is editor configuration, not Flask settings or database credentials.
- **`PROJECT_GUIDE.md`** is this explanation, added for your reference. The app does not import or render it.
- **`.DS_Store`** files are macOS Finder metadata. They do not participate in the app.
- **`.git/`** holds version-control history, index, branches, and repository metadata. It is not a web feature.
- **`.venv/`** holds the installed Python interpreter environment, package code, scripts, and package metadata. Files such as `site-packages/google/genai/models.py` in a traceback are library internals. Usually trace back to the nearest project-owned calling line before editing dependencies.
- **`__pycache__/` and `.pyc` files** are generated Python bytecode caches. They are not the authoritative source; the `.py` files are.

No Dockerfile, Alembic migration directory, or GitHub Actions workflow appeared in the inspected first-party inventory. Their appearance in earlier planning discussions does not mean they are implemented in this checkout.

## 17. Three complete examples to connect the pieces

### Example A: “I enjoy biology” as a guest

1. `/questionnaire` returns `guided_chat.html` and a signed session cookie.
2. `guided-chat.js` calls `chatApiReady.load()` → GET `/api/chat`.
3. `get_current_user()` returns None. `get_or_create_guest_session()` finds/creates the guest JSONB row.
4. The browser displays the saved conversation or local greeting.
5. Send calls `chatApiReady.send(message)` → POST `/api/chat`, with CSRF and cookie.
6. The route loads catalog/guest interests and calls `interpret_message`.
7. Gemini proposes a Biology keyword by name, a quote, and a follow-up question. Python validates and maps the name to its real ID.
8. `apply_guest_chat_turn` updates the copied state. SQL ranks majors using matching keyword IDs and attaches the quote as evidence.
9. `save_guest_session` checks the version and stores the new state/expiration.
10. The route returns the assistant reply and recommendations. JavaScript draws the messages and cards.

A Gemini failure before saving leaves this turn unsaved. A guest conflict also prevents silently replacing a newer conversation. The visible typed text is kept so the visitor can recover.

### Example B: search programs from two favorite majors

1. The signed-in user opens Programs Explore and chooses Selected favorite majors.
2. The page's favorite list came from `get_major_favorites(session['user_id'])`.
3. They select two codes and a net-price ceiling, then Apply.
4. The browser navigates to a GET URL containing repeated `favorite_major` arguments and other filters.
5. `explore()` verifies both codes are actually this user's favorites and builds a list.
6. `get_page_programs` uses `p.cipcode IN :cipcodes` plus the cost condition. The expanded list matches either selected major; the cost condition restricts both.
7. SQL returns joined program rows, including major names. There is no separate full major-catalog scan in this path.
8. Flask renders 25 cards and pagination links preserving the filters.
9. One additional browser API request loads saved program IDs for all the card buttons.

### Example C: compare three saved programs

1. `/compare` renders the shell for a signed-in user.
2. `compare.js` loads major favorites initially; clicking Programs resets selection and fetches `/api/compare?kind=programs`.
3. The route reads the session identity, queries only that user's favorites, and normalizes display fields with `comparison_payload`.
4. JavaScript builds a sidebar. One selection shows guidance; two or three show a table.
5. Changing selections reads already-loaded data. Higher earnings and lower costs receive badges only when at least two values are reported. Missing data is not treated as zero.
6. Changing type or reentering the page resets the temporary selections. The actual favorite records remain saved.

## 18. What is implemented, what is older, and where to work next

The active paths are the Gemini `/api/chat` workflow, verified Flask-session login, temporary guest state, both Explore catalogs, favorites, and comparison. Older name-search routes and generic SQL helpers remain callable, but they are not the same recommendation mechanism.

Keep these distinctions in mind while changing code:

- Chat interpretation belongs in `chat_service.py` and its schemas/prompt; account persistence belongs in `save_chat_turn`; guest changes belong in `apply_guest_chat_turn` and guest persistence.
- A new program filter usually needs controls in `explore.html`, parsing in `explore()`, validation/SQL in `get_page_programs`, and preservation in pagination. A new major filter uses the corresponding major files instead.
- A new displayed comparison statistic needs a query column in `get_comparison_favorites` and a metric in `comparison.py`; general table rendering already loops through metrics.
- A new account preference needs an actual write/read path. Merely adding a column to `user_info` or wording to the prompt will not save it.
- A new keyword needs a unique, consistent label/ID and links to relevant majors. The AI cannot make a catalog keyword recommend a major that has no mapping to it.
- The old shuffle seed is retained but unused. The old `/chat/reset` does not reset Gemini chat. Profile/Settings are placeholders. Guest-to-account migration is not implemented.
- Existing tests cover useful contracts but do not cover every database function, PostgreSQL-specific transaction detail, template rendering in a real browser, or external-service availability.

A practical reading order is `app.py`, `degree_path/__init__.py`, one route in `routes.py`, the database/service functions it calls, its template, and finally its JavaScript. Trace one request all the way through before trying to memorize every helper in the project.

## 19. Clickable source index

These links point to the files and definition lines inspected for this guide. Line numbers can change after later edits.

- `.env`: private configuration; variable names are explained in section 3.
- [.gitignore](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/.gitignore)
- [.vscode/settings.json](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/.vscode/settings.json)
- [AGENTS.md](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/AGENTS.md)
- [CLERK-SETUP.md](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/CLERK-SETUP.md)
- [README.md](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/README.md)
- [app.py](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/app.py)
- [cloud_admin_connection.py](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/cloud_admin_connection.py)

  Definitions: [connect_with_connector](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/cloud_admin_connection.py:21), [getconn](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/cloud_admin_connection.py:45), [close_connector](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/cloud_admin_connection.py:67).

- [cloud_sql_connection.py](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/cloud_sql_connection.py)

  Definitions: [get_database_password](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/cloud_sql_connection.py:10), [connect_with_connector](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/cloud_sql_connection.py:22), [getconn](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/cloud_sql_connection.py:47), [close_connector](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/cloud_sql_connection.py:70).

- [data/FieldOfStudy.csv](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/data/FieldOfStudy.csv)
- [data/Institution.csv](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/data/Institution.csv)
- [data/Most-Recent-Cohorts-Field-of-Study.csv](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/data/Most-Recent-Cohorts-Field-of-Study.csv)
- [data/Most-Recent-Cohorts-Institution.csv](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/data/Most-Recent-Cohorts-Institution.csv)
- [db_functions.py](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py)

  Definitions: [create_or_update_user](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:19), [add_major_fav](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:40), [add_program_fav](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:58), [add_program_rec](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:73), [add_to_chat_to_log](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:82), [add_user_keyword](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:90), [get_a_keyword_id_from_keyword](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:101), [get_a_keyword_from_keyword_id](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:112), [get_school_adm_crit](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:125), [get_cost_info](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:155), [get_all_npt_info](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:180), [get_tuition_info](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:203), [get_city_state](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:222), [get_school_url](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:242), [get_sat_crit](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:255), [get_school_act_crit](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:278), [get_school_list_from_satscores](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:301), [get_bracket](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:319), [get_npt](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:348), [get_programs_from_cipcode](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:360), [get_mdn_earnings](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:376), [get_program_id_fom_unit_and_cip](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:388), [get_unit_and_cip_from_program_id](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:400), [get_best_progs_from_cip](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:413), [get_major_id_from_cipcode](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:435), [get_cipcode_from_major_id](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:448), [get_school_id_from_unitid](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:461), [get_unitid_from_school_id](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:474), [get_recent_chatlog](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:487), [get_a_page](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:500), [paginate](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:518), [scan_entire_table](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:530), [get_page_schools](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:573), [get_a_program](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:589), [get_page_programs](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:654), [validate_program_filters](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:828), [get_page_majors](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:908), [get_page_program_recs](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:938), [get_page_program_favs](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:973), [get_page_major_recs](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1008), [get_page_major_favs](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1039), [get_user_keywords](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1055), [get_keywords](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1067), [get_user](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1076), [save_chat_turn](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1089), [remove_user](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1186), [remove_from_major_fav](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1194), [remove_major_rec](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1203), [remove_school_fav](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1212), [remove_program_rec](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1221), [delete_chatlog](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1230), [remove_user_keyword](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1238), [get_major_info](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1247), [warm_database_connections](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1259), [_rank_majors_from_keywords](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1267), [get_recommendations_for_keywords](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1349), [_refresh_user_recommendations](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1361), [create_recommendations](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1419), [get_recommendations](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1439), [create_guest_session](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1491), [get_guest_session](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1517), [save_guest_session](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1534), [delete_expired_guest_sessions](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1560), [get_major_favorites](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1572), [get_comparison_favorites](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1590), [is_program_favorite](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1635), [get_program_favorites](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1645), [get_major_name_suggestions](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1662), [get_major_catalog_page](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_functions.py:1676).

- [db_setup.py](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_setup.py)

  Definitions: [main](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/db_setup.py:9).

- [degree_path/__init__.py](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/__init__.py)

  Definitions: [create_app](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/__init__.py:14), [protect_forms](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/__init__.py:66), [template_helpers](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/__init__.py:75), [money](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/__init__.py:84), [http_error](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/__init__.py:88), [response_headers](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/__init__.py:94), [cleanup_guests](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/__init__.py:109).

- [degree_path/auth.py](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/auth.py)

  Definitions: [establish_login](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/auth.py:13), [expire_login](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/auth.py:65), [get_current_user](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/auth.py:72).

- [degree_path/chat_schemas.py](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/chat_schemas.py)

  Definitions: [KeywordAddition](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/chat_schemas.py:4), [AdvisorTurn](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/chat_schemas.py:10), [GeminiKeywordAddition](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/chat_schemas.py:17), [GeminiAdvisorTurn](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/chat_schemas.py:28).

- [degree_path/chat_service.py](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/chat_service.py)

  Definitions: [InvalidAdvisorResponse](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/chat_service.py:17), [_keyword_rows](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/chat_service.py:21), [interpret_message](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/chat_service.py:42).

- [degree_path/comparison.py](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/comparison.py)

  Definitions: [comparison_payload](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/comparison.py:39).

- [degree_path/forms.py](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/forms.py)

  Definitions: [TextInputForm](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/forms.py:6), [validate_text](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/forms.py:10).

- [degree_path/guest_state.py](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/guest_state.py)

  Definitions: [get_or_create_guest_session](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/guest_state.py:8).

- [degree_path/prompts/advisor.txt](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/prompts/advisor.txt)
- [degree_path/routes.py](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py)

  Definitions: [database_errors](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:17), [wrapped](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:20), [normalize](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:29), [college_website_url](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:32), [format_program_cards](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:52), [catalog_majors](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:90), [program_page](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:104), [program](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:124), [recommendations](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:171), [positive_arg](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:196), [text_value](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:208), [home](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:214), [chat](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:220), [reset_chat](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:230), [questionnaire](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:234), [explore](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:238), [program_details](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:343), [start](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:350), [profile](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:359), [settings](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:364), [legacy_page](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:369), [health](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:380), [programs_api](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:384), [search_api](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:389), [recommendations_api](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:398), [api_chat](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:410), [apply_guest_chat_turn](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:540), [favorites](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:581), [favorites_api](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:589), [auth_session_api](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:645), [logout](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:657), [compare](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:664), [compare_api](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:669), [program_favorite_api](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:686), [program_favorites_api](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:714), [major_names_api](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:731), [explore_major_catalog](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/routes.py:744).

- [degree_path/static/css/app.css](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/css/app.css)
- [degree_path/static/css/compare.css](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/css/compare.css)
- [degree_path/static/css/explore.css](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/css/explore.css)
- [degree_path/static/css/favorites.css](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/css/favorites.css)
- [degree_path/static/css/guided-chat.css](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/css/guided-chat.css)
- [degree_path/static/css/home.css](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/css/home.css)
- [degree_path/static/css/profile.css](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/css/profile.css)
- [degree_path/static/css/program-details.css](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/css/program-details.css)
- [degree_path/static/css/theme.css](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/css/theme.css)
- [degree_path/static/img/favicon.png](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/img/favicon.png)
- [degree_path/static/js/account-auth.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/js/account-auth.js)
- [degree_path/static/js/chat-api.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/js/chat-api.js)
- [degree_path/static/js/clerk-config.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/js/clerk-config.js)
- [degree_path/static/js/compare.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/js/compare.js)
- [degree_path/static/js/comparison-values.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/js/comparison-values.js)
- [degree_path/static/js/explore.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/js/explore.js)
- [degree_path/static/js/favorites.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/js/favorites.js)
- [degree_path/static/js/forms.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/js/forms.js)
- [degree_path/static/js/guided-chat.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/js/guided-chat.js)
- [degree_path/static/js/home.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/js/home.js)
- [degree_path/static/js/major-card-favorites.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/js/major-card-favorites.js)
- [degree_path/static/js/program-card-favorites.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/js/program-card-favorites.js)
- [degree_path/static/js/program-favorite.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/static/js/program-favorite.js)
- [degree_path/templates/_explore_tabs.html](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/templates/_explore_tabs.html)
- [degree_path/templates/_favorites_signin.html](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/templates/_favorites_signin.html)
- [degree_path/templates/_navigation.html](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/templates/_navigation.html)
- [degree_path/templates/base.html](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/templates/base.html)
- [degree_path/templates/chat.html](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/templates/chat.html)
- [degree_path/templates/compare.html](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/templates/compare.html)
- [degree_path/templates/error.html](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/templates/error.html)
- [degree_path/templates/explore.html](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/templates/explore.html)
- [degree_path/templates/explore_majors.html](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/templates/explore_majors.html)
- [degree_path/templates/favorites.html](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/templates/favorites.html)
- [degree_path/templates/guided_chat.html](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/templates/guided_chat.html)
- [degree_path/templates/home.html](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/templates/home.html)
- [degree_path/templates/profile.html](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/templates/profile.html)
- [degree_path/templates/program_details.html](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/templates/program_details.html)
- [degree_path/templates/settings.html](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/degree_path/templates/settings.html)
- [requirements.txt](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/requirements.txt)
- [schemas/all_schema.sql](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/schemas/all_schema.sql)
- [schemas/app_runtime_perms.sql](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/schemas/app_runtime_perms.sql)
- [schemas/data_schema.sql](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/schemas/data_schema.sql)
- [schemas/user_schema.sql](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/schemas/user_schema.sql)
- [tables/adm_crit.csv](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tables/adm_crit.csv)
- [tables/base_major_info.csv](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tables/base_major_info.csv)
- [tables/cost_info.csv](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tables/cost_info.csv)
- [tables/kwd_list.csv](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tables/kwd_list.csv)
- [tables/kwd_pairs.csv](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tables/kwd_pairs.csv)
- [tables/major_info.csv](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tables/major_info.csv)
- [tables/major_keywords.csv](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tables/major_keywords.csv)
- [tables/majors.csv](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tables/majors.csv)
- [tables/majors_excelsheet.xlsx](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tables/majors_excelsheet.xlsx)
- [tables/majors_with_keywords_and_descriptions_corrected.xlsx](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tables/majors_with_keywords_and_descriptions_corrected.xlsx)
- [tables/program_rank_crit.csv](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tables/program_rank_crit.csv)
- [tables/programs.csv](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tables/programs.csv)
- [tables/schools.csv](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tables/schools.csv)
- [tests/test_account_auth.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_account_auth.js)
- [tests/test_chat_service.py](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_chat_service.py)

  Definitions: [ChatServiceTests](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_chat_service.py:14), [setUp](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_chat_service.py:15), [call_service](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_chat_service.py:24), [test_valid_turn_and_request_context](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_chat_service.py:32), [test_invalid_responses_are_rejected](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_chat_service.py:41), [test_unknown_name_and_invented_evidence_are_rejected](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_chat_service.py:46), [test_conflicting_changes_are_rejected](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_chat_service.py:61), [test_existing_additions_can_update_evidence](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_chat_service.py:65), [test_only_saved_keywords_can_be_removed](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_chat_service.py:75), [test_provider_failure_propagates](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_chat_service.py:81), [test_import_does_not_load_database_module](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_chat_service.py:87).

- [tests/test_compare_ui.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_compare_ui.js)
- [tests/test_comparison_data.py](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_comparison_data.py)

  Definitions: [ComparisonDataTests](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_comparison_data.py:11), [setUp](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_comparison_data.py:12), [test_only_owned_favorites_and_missing_optional_data](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_comparison_data.py:45), [test_program_save_is_idempotent_and_removal_is_scoped](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_comparison_data.py:58), [test_program_favorites_list_is_scoped_and_preserves_credential](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_comparison_data.py:68), [test_decimal_rates_and_partial_scores](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_comparison_data.py:75), [test_program_major_filters_exact_name_union_and_empty](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_comparison_data.py:86), [test_major_suggestions_match_names_and_escape_wildcards](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_comparison_data.py:109), [test_major_catalog_filters_sort_pagination_and_user_scope](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_comparison_data.py:115), [test_program_school_search_and_sort_remain_program_specific](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_comparison_data.py:141).

- [tests/test_comparison_values.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_comparison_values.js)
- [tests/test_explore_filters.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_explore_filters.js)
- [tests/test_favorites_ui.js](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_favorites_ui.js)
- [tests/test_session_auth.py](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py)

  Definitions: [SessionAuthTests](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:9), [setUpClass](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:11), [setUp](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:31), [login](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:42), [test_verified_login_and_cookie_only_favorites](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:50), [test_login_persists_for_24_hours_without_sliding_expiration](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:62), [test_navigation_uses_session](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:84), [test_invalid_token_and_untrusted_user_id_cannot_login](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:93), [test_csrf_required_for_login_and_logout](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:100), [test_logout_clears_account](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:107), [test_expired_login_and_stale_tab_rejected](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:120), [test_account_switch_rejects_old_tab](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:129), [test_chat_and_explore_skip_account_choice](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:135), [test_guest_favorites_has_signin_and_home_without_data_requests](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:149), [test_comparison_requires_login_and_valid_kind](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:163), [test_comparison_reads_only_session_user](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:176), [test_program_favorite_requires_login_and_csrf](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:186), [test_program_favorite_list_uses_session_and_returns_links](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:203), [test_explore_cards_offer_favorites_for_guests_and_users](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:215), [test_explore_major_search_and_favorite_selection_persist](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:226), [test_major_name_api_short_query_needs_no_database](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:251), [test_explore_tabs_separate_catalogs_and_keep_major_filters](/Users/bryanbegley/Documents/Programming/Capstone1/CSC400-Capstone-newtestbranch/tests/test_session_auth.py:257).

