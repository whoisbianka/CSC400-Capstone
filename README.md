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

## Saved-major database setup

The existing application database stores Clerk identities in `users.clerk_user_id` and saved majors in `major_fav`. The saved-major API supports this schema directly, preserving prior selections. It maps only the verified Clerk token's user ID to `users.id`, creates an account row when needed on save, and uses the existing unique `(user_id, cipcode)` constraint to prevent duplicates. No new table or permission changes are required for this database.

Installations that already have the standalone `saved_majors` table continue to use it. Storage is detected once per app instance; requests do not create or migrate tables. `schemas/saved_majors.sql` is optional for a separate standalone-storage installation, not required for the existing `users`/`major_fav` schema.

Do not run `all_schema.sql`, `data_schema.sql`, or `user_schema.sql` to resolve a saving error; those scripts reset data. Repeating `gcloud auth application-default login` does not resolve a storage-schema mismatch. Restart Flask after updating the save-major backend.

UPDATE October 3rd, 2026 — Changes from this date reflect feedback from the October 1 class meeting.
