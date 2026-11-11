# Add to your existing .env

DATABASE_MODE=local

LOCAL_DB_HOST=127.0.0.1
LOCAL_DB_PORT=5433
LOCAL_DB_NAME=capstone_local

LOCAL_DB_USER=python_connection
LOCAL_DB_PASSWORD=local_postgres_password

LOCAL_DB_ADMIN_USER=postgres
LOCAL_DB_ADMIN_PASSWORD=postgres_pw

# ---------------------------

# Download and Install Docker

https://www.docker.com/products/docker-desktop/

# Open a terminal within the Directory containing app.py and compose.yml

# Run the following commands on first startup

```sh
# Create the virtual environment if it does not already exist.
python3 -m venv .venv

source .venv/bin/activate
python -m pip install -r requirements.txt

docker compose up -d
DATABASE_MODE=local python -m database.db_init
DATABASE_MODE=local python3 app.py
```

# Use the following commands upon returning

```sh
source .venv/bin/activate
docker compose up -d
DATABASE_MODE=local python3 app.py
```

# Use the Website

Navigate to http://127.0.0.1:8000

# Stopping the program

Use Control + C in the terminal running the Flask server to stop it

Use the following command to stop the docker container:

```sh
docker compose down
```

to reset the container completely use:

```sh
docker compose down -v
```

You can then start a fresh container.
