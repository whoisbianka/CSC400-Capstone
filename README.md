# CSC400 Capstone — Cloud SQL integration

This branch runs the Flask college and major explorer against the populated PostgreSQL catalog on Google Cloud SQL. Cloud SQL is the default; fictional data is available only to automated tests. Connection failures display an error and never substitute demo records.

## Here is how you run locally

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
gcloud auth application-default login
python -m flask --app degree_path check-database (optional, you can just go straight to running python app.py)
python app.py
```

Before checking the connection, put your teammate's connection details in a private `.env` beside `app.py`. Use `.env.example` as a reference; do not overwrite an existing credentials file. The connection name must contain three parts: `project:region:instance`.

Open http://127.0.0.1:8000/explore. See [connection setup](DATABASE-CONNECTION.md) for configuration, certificates, schema mapping, and limitations, and [application architecture](PYTHON-DEMO.md) for the Flask flows.

All catalog queries are read-only. This integration never runs setup scripts or changes the shared database. User profiles, favorites, and chat persistence are not integrated; questionnaire answers and search history remain temporary server sessions.
