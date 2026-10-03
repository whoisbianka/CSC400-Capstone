# CSC400 Capstone — Degree Path

The Flask site queries the PostgreSQL catalog on Google Cloud SQL through `db_functions.py` and `cloud_sql_connection.py`. Database failures display an error. Catalog results and ranked college examples come from the connected database.

## Run locally

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
gcloud auth application-default login
python app.py
```

Keep connection settings in the private `.env` beside `app.py`; use `.env.example` for the required names. Do not commit credentials. The instance connection name has the form `project:region:instance`.

Open http://127.0.0.1:8000/ for the homepage, `/questionnaire` for guided chat, and `/explore` for the catalog. The guided chat maps interests to exploration terms, then requests actual majors and ranked colleges from `/api/recommendations`. Location and cost preferences are not applied to that ranking. Answers reset on reload.

The catalog pages and recommendation endpoints perform read-only queries. Profile authentication is separate from catalog access; favorites and chat persistence are not integrated.

UPDATE October 3rd, 2026 — Changes from this date reflect feedback from the October 1 class meeting.
