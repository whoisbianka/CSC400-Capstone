# Cloud SQL catalog integration

Cloud SQL is the default on `test/python-cloudsql-integration`. Fictional fixtures are restricted to automated tests. The app never falls back to them when a connection fails.

## Enable a database when access is available

From an activated virtual environment in the project folder:

```sh
python -m pip install -r requirements.txt
```

Create `.env` using `.env.example` as a reference only when you do not already have one; otherwise edit the existing file. `.env` is ignored by Git. The application reads this file from the repository root; exported environment variables take priority. Restart Flask after changing settings. Keep passwords in `.env` locally, not in source code or chat.

Choose one connection method:

### Local/direct PostgreSQL

```dotenv
PROGRAM_DATA_SOURCE=postgres
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=your_test_database
DB_USER=your_readonly_user
DB_PASS=your_password
DB_SSLMODE=disable
TUITION_BASIS=in_state
```

`disable` is for local testing. Direct remote connections default to `DB_SSLMODE=verify-full`, using a trusted TLS certificate and hostname verification. The database must already contain the catalog tables from `database-branch`; connection preparation does not install PostgreSQL or populate tables.

### Google Cloud SQL (your teammate's connector pattern)

```dotenv
PROGRAM_DATA_SOURCE=cloudsql
INSTANCE_CONNECTION_NAME=your-project:your-region:your-instance
DB_NAME=your_database
DB_USER=your_readonly_user
DB_PASS=your_password
PRIVATE_IP=false
TUITION_BASIS=in_state
```

This uses Google's Cloud SQL Python Connector and pg8000. Your Google account needs permission to connect (normally Cloud SQL Client), the Cloud SQL Admin API must be enabled, and the database user needs SELECT access to the catalog tables. For local development, configure Google Application Default Credentials:

```sh
gcloud auth application-default login
```

`PRIVATE_IP=true` additionally requires network access to the instance's private network; the connector does not create that network path. `PRIVATE_IP=false` explicitly selects public IP. Authentication/access must be arranged by your teammate or project administrator.

See [Google's connector documentation](https://github.com/GoogleCloudPlatform/cloud-sql-python-connector) for Google setup and network requirements.

## Check before opening the app

```sh
python -m flask --app degree_path check-database
python app.py
```

The check executes a read-only joined catalog query with at most one result, verifying connectivity and the expected schema without displaying records or connection secrets. It exits unsuccessfully on configuration, access, or schema errors. `/api/health` is only application liveness; a successful health response does not prove database connectivity.

Open http://127.0.0.1:8000/explore. Database mode says **Database catalog**, and tuition explicitly says in-state or out-of-state. Start with a major name shown in Explore; the current matcher recognizes catalog major names but does not yet have a database-backed synonym/career dictionary.

## Schema mapping

`degree_path/repositories/postgres.py` queries only `public.programs`, `public.schools`, `public.majors`, and `public.cost_info` from the inspected `database-branch` schema. It uses `programs.program_id` (not `programs.id`) for detail links.

- `schools.instnm` → college.
- `majors.cipdesc` → major.
- `schools.stabbr` → state abbreviation plus expanded US state name.
- `cost_info.tuitionfee_in` or `tuitionfee_out` → institution-level annual tuition and fees.
- `programs.credlev` → associate's/bachelor's label for codes 2/3.

Choose `TUITION_BASIS=in_state` or `out_of_state`. Missing or negative costs stay unavailable; there is no automatic switch to another cost basis. Net price is not substituted for tuition. Because `cost_info.unitid` is not unique in the schema, the adapter selects the highest `id` per institution to avoid duplicate program cards. That is an insertion-order rule, not proof of the newest reporting year.

The schema has no college ownership, study format, keywords, or careers. The adapter leaves these unavailable; it does not invent values. Study-format dropdown options are omitted in database mode and natural-language public/private/format filters explain that those fields are unavailable.

## Behavior and limits

Connections are lazy and pooled. Every query starts a read-only transaction with a ten-second statement timeout. Queries use bound program IDs; no setup scripts, inserts, updates, or deletes run. A failed database connection returns a controlled 503 response and never silently falls back to fictional fixtures. Use a read-only DB account as an additional restriction.

Do not run the branch's `db_setup.py` just to connect: its schema scripts drop and recreate tables. Have your teammate supply a populated test database or a catalog-only export if testing locally.

Explore filters and sorts in PostgreSQL and displays 50 programs per page. The home page fetches only three suggestion names. Chat searches, questionnaire matching, and the legacy full-catalog API still assemble the catalog in memory, now fetched in batches of 2,000; these paths can still be slower on large datasets. Questionnaire sessions remain temporary server memory and are not written to the database.

## Offline tests

```sh
python -m pip install -r requirements-database.txt
python -m unittest discover -s tests -v
```

Adapter tests execute the catalog SELECT against a small SQLite fixture with matching table/column names (removing only the PostgreSQL `public.` qualifier). Connection tests mock SQLAlchemy/Google networking and check read-only transactions, configuration, parameter binding, error handling, and credential redaction. These tests do not replace a real PostgreSQL connection check. Connection-specific tests skip when optional database dependencies are absent.

## macOS certificate troubleshooting

In the activated environment, use the installed certificate bundle in the same terminal before starting Flask:

```sh
export SSL_CERT_FILE="$(python -m certifi)"
export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
python -m flask --app degree_path check-database
python app.py
```

If this works on a hotspot but fails on eduroam, use the working network for local testing and ask campus IT about certificate requirements. Keep TLS verification enabled.

## Database branch synchronization (2026-10-01)

Adapted changes through database-branch commit `19bfcba`: uniform primary-key `id` columns, certificate defaults, page queries, cursor pagination, and batched scanning. This expects the updated deployed schema; no schema scripts are executed. Program URLs continue to use `program_id`, while scans advance by the internal `programs.id`.

`degree_path.repositories.tables.CatalogTables` exposes `get_a_page`, `paginate`, and `scan_entire_table` for schools, majors, and programs. The signatures follow the teammate's helpers; results consistently use mapping rows (`row['id']`). Only allowlisted table/column names are accepted; page sizes and cursor values are validated. Each batch uses the existing read-only transaction and query timeout. Batches do not represent a single database snapshot if the catalog changes during a scan.

For Python exploration without editing files:

```python
from degree_path import create_app
from degree_path.repositories.tables import CatalogTables
app = create_app()
db = app.extensions['program_repository'].database
tables = CatalogTables(db)
print(tables.get_a_page(1, 10, 'schools', 'instnm', 'ASC'))
for row in tables.scan_entire_table('schools'):
    if row['stabbr'] == 'CT':
        print(row['instnm'])
db.close()
```

The Cloud SQL connector defaults to certifi for TLS certificates, without replacing explicitly set `SSL_CERT_FILE` or `REQUESTS_CA_BUNDLE` values. The manual certificate commands above remain useful for diagnosing campus network issues.
