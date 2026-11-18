# CSC400 Capstone — Degree Path

Flask website for exploring majors and college programs. Gemini extracts user
interests; database keyword matches rank majors. Chat can create links to
filtered program searches. Guests can chat, and their retained conversation and
interests merge into their account on sign-in. Favorites, saved filters,
comparisons and account chat data are stored in PostgreSQL.

## Run locally

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# Needed for Cloud SQL IAM / Secret Manager access:
gcloud auth application-default login
python app.py
```

Keep connection settings and Secret Manager version references in the private
.env beside app.py. Never commit credentials. Local PostgreSQL is provided by
Docker; Clerk, Gemini and configured Secret Manager references remain external
services. See [LOCAL_DATABASE.md](LOCAL_DATABASE.md).

## Database setup

The original scripts are in `database/`. Run them as modules from the project
root so imports resolve correctly:

```sh
python -m database.db_setup
python -m database.db_init
```

`db_setup` generates seed CSVs from `database/data/` into `database/seed_data/`.
The restored script initializes an admin connection. `db_init` uses the configured
DATABASE_MODE: in cloud mode it resets the schema before importing; in local
mode it appends to the schema created by Docker. Do not rerun a local import on
populated tables. See [LOCAL_DATABASE.md](LOCAL_DATABASE.md) for a fresh local setup.
These scripts do not implement --check or --reset options.
