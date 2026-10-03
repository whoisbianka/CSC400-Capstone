This branch runs the Flask college and major explorer against the populated PostgreSQL catalog on Google Cloud SQL. 

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


UPDATE October 3rd, 2026 - everything that was committed from this day forward is based on feedback that we got from the meeting during class on 10/1, everything beforehand will get deleted!
