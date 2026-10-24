# CSC400 Capstone — Degree Path

The Flask site queries the PostgreSQL catalog on Google Cloud SQL through `db_functions.py` and `cloud_sql_connection.py`. Database failures display an error. Catalog results and ranked college examples come from the connected database.

## Run locally

```sh
python3 -m venv .venv (do this if you dont have this environmental variable already)
source .venv/bin/activate
python -m pip install -r requirements.txt (important to run the program)
gcloud auth application-default login (important for the database)
python app.py
```

Keep connection settings in the private `.env` beside `app.py`; use `.env.example` for the required names. Do not commit credentials. The instance connection name has the form `project:region:instance`.

Homepage cards offer sign-in or guest access before continuing to the selected destination. Clerk authentication is separate from catalog access; favorites and chat persistence are not integrated.

UPDATE October 3rd, 2026 — Changes from this date reflect feedback from the October 1 class meeting.

## Saved library

Saved majors shows one general field-of-study card per saved major, matching Explore majors: description, aggregate catalog counts, source information, and reported earnings. It does not automatically display college programs or comparison controls. Find colleges for this major opens Explore only when requested.

Favorited programs is a separate tab on the same Saved majors page and contains only the specific programs saved with a heart. Old Favorites links redirect to this shared page. The separate Compare page remains available.
