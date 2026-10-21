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

Before using account-owned saved majors, run `schemas/saved_majors.sql` as the owner of `public.majors` or a database administrator. The script creates only the saved-major table and grants SELECT, INSERT, and DELETE to the existing `app_runtime` role. It does not reset the catalog or existing saved selections. The application connection must inherit that runtime role, as configured in `schemas/app_runtime_perms.sql`.

Catalog access can work while saving fails: SELECT on `majors` does not grant the REFERENCES permission required to create its foreign key. Creating the table as its owner avoids giving the runtime account schema-management privileges. Once the table exists, the app uses it without attempting schema creation. Reload and retry saving after the migration; failed setup is not cached.

Do not run `all_schema.sql`, `data_schema.sql`, or `user_schema.sql` to enable saving; those scripts reset data. Repeating `gcloud auth application-default login` does not resolve missing PostgreSQL table permissions.

UPDATE October 3rd, 2026 — Changes from this date reflect feedback from the October 1 class meeting.
