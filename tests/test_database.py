"""Offline contract tests. These do not claim to connect to PostgreSQL or Cloud SQL."""
import sqlite3
import unittest
from importlib.metadata import version, PackageNotFoundError
from unittest.mock import MagicMock, patch
from degree_path import create_app
from degree_path.database import Database, DatabaseUnavailable
from degree_path.repositories.postgres import PostgresProgramRepository
from degree_path.services.search import search


class SqliteCatalog:
    """Execute catalog SELECTs against an isolated schema-shaped SQL fixture."""
    def __init__(self):
        self.connection = sqlite3.connect(':memory:')
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript('''
        CREATE TABLE programs(program_id INTEGER, unitid INTEGER, cipcode INTEGER, credlev INTEGER);
        CREATE TABLE schools(unitid INTEGER, instnm TEXT, stabbr TEXT, city TEXT);
        CREATE TABLE majors(cipcode INTEGER, cipdesc TEXT);
        CREATE TABLE cost_info(cost_id INTEGER, unitid INTEGER, tuitionfee_in INTEGER, tuitionfee_out INTEGER);
        INSERT INTO schools VALUES (10, 'Test College', 'CT', 'New Haven');
        INSERT INTO majors VALUES (1107, 'Computer Science');
        INSERT INTO programs VALUES (1,10,1107,3), (2,10,1107,2);
        INSERT INTO cost_info VALUES (1,10,100,200),(2,10,12000,24000);
        ''')

    def select(self, sql, params=None):
        return self.connection.execute(sql.replace('public.', ''), params or {}).fetchall()


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.database = SqliteCatalog()
        self.repo = PostgresProgramRepository(self.database)
        self.addCleanup(self.database.connection.close)

    def test_join_mapping_and_duplicate_cost_rows(self):
        rows = self.repo.all()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['state'], 'Connecticut')
        self.assertEqual(rows[0]['tuition'], 12000)
        self.assertEqual(rows[0]['format'], '')
        self.assertEqual(rows[0]['type'], '')
        self.assertEqual(rows[0]['degree'], "Bachelor's degree")
        self.assertEqual(rows[0]['id'], '1')
        self.assertEqual(PostgresProgramRepository(self.database, 'out_of_state').get('1')['tuition'], 24000)

    def test_missing_cost_and_invalid_ids(self):
        self.database.connection.execute('DELETE FROM cost_info')
        self.assertIsNone(self.repo.get('1')['tuition'])
        for identifier in ['1 OR 1=1', '-1', '999999999999999', '١', '404']:
            self.assertIsNone(self.repo.get(identifier))

    def test_real_data_labels_and_filters(self):
        result = search('computer science in Connecticut under 20k', self.repo.all(), demo=False, tuition_label=self.repo.tuition_label)
        self.assertEqual(len(result['rows']), 2)
        self.assertFalse(result['demo'])
        self.assertNotIn('demo', result['message'])
        self.assertIn('in-state', result['filters'][-1])
        self.assertIn('unavailable', search('online computer science', self.repo.all(), demo=False)['message'])

    def test_flask_adapter_pages_and_api(self):
        app = create_app({'TESTING': True, 'PROGRAM_DATA_SOURCE': 'demo'})
        app.extensions['program_repository'] = self.repo
        client = app.test_client()
        self.assertFalse(client.get('/api/programs').json['demo'])
        self.assertFalse(client.post('/api/search', json={'question':'computer science'}).json['demo'])
        page = client.get('/explore').text
        self.assertIn('Database catalog', page)
        self.assertIn('in-state', page)
        self.assertIn('Not available', page)
        self.assertNotIn('fictional', page)
        self.assertNotIn('Fictional', client.get('/programs/1').text)


try:
    for package in ('SQLAlchemy', 'pg8000', 'cloud-sql-python-connector'):
        version(package)
    DATABASE_DEPS = True
except PackageNotFoundError:
    DATABASE_DEPS = False


@unittest.skipUnless(DATABASE_DEPS, 'Install requirements-database.txt for connection tests')
class ConnectionTests(unittest.TestCase):
    def test_demo_default_does_not_initialize_database(self):
        with patch('degree_path.database.Database._engine', side_effect=AssertionError('Must not connect')):
            app = create_app({'TESTING': True, 'PROGRAM_DATA_SOURCE':'demo'})
            self.assertEqual(app.test_client().get('/').status_code, 200)
            result = app.test_cli_runner().invoke(args=['check-database'])
            self.assertEqual(result.exit_code, 0)
            self.assertIn('no database connection', result.output)

    def test_cloudsql_is_default_and_demo_is_test_only(self):
        with patch('degree_path.dotenv_values', return_value={}), patch.dict('os.environ', {}, clear=True):
            app = create_app()
        self.assertFalse(app.extensions['program_repository'].is_demo)
        self.assertEqual(app.config['PROGRAM_DATA_SOURCE'], 'cloudsql')
        with self.assertRaisesRegex(ValueError, 'automated tests'):
            create_app({'PROGRAM_DATA_SOURCE': 'demo'})

    def test_malformed_instance_name_is_actionable(self):
        config = dict(PROGRAM_DATA_SOURCE='cloudsql', DB_USER='user', DB_PASS='secret',
                      DB_NAME='db', INSTANCE_CONNECTION_NAME='project:instance')
        db = Database(config)
        self.addCleanup(db.close)
        with self.assertRaisesRegex(DatabaseUnavailable, 'project:region:instance'):
            db.select('SELECT 1')

    def test_missing_credentials_503_and_cli_failure(self):
        app = create_app({'TESTING': True, 'PROGRAM_DATA_SOURCE':'cloudsql', 'DB_USER':'', 'DB_PASS':'', 'DB_NAME':'', 'INSTANCE_CONNECTION_NAME':''})
        client = app.test_client()
        self.assertEqual(client.get('/api/health').status_code, 200) # Liveness only.
        response = client.get('/api/programs')
        self.assertEqual(response.status_code, 503)
        self.assertIn('Missing database settings', response.json['error'])
        self.assertEqual(client.get('/explore').status_code, 503)
        self.assertNotEqual(app.test_cli_runner().invoke(args=['check-database']).exit_code, 0)

    def test_reads_run_in_read_only_transaction_and_bind_ids(self):
        db = Database({'PROGRAM_DATA_SOURCE':'postgres'})
        self.addCleanup(db.close)
        connection = MagicMock()
        connection.execute.return_value.mappings.return_value = []
        db.engine = MagicMock()
        db.engine.connect.return_value.__enter__.return_value = connection
        db.select('SELECT :program_id', {'program_id':123})
        calls = connection.execute.call_args_list
        self.assertEqual(str(calls[0].args[0]), 'SET TRANSACTION READ ONLY')
        self.assertIn('statement_timeout', str(calls[1].args[0]))
        self.assertEqual(calls[2].args[1], {'program_id':123})

    def test_driver_errors_do_not_expose_credentials(self):
        db = Database({'PROGRAM_DATA_SOURCE':'postgres'})
        self.addCleanup(db.close)
        db.engine = MagicMock()
        db.engine.connect.side_effect = RuntimeError('password=super-secret')
        with self.assertRaises(DatabaseUnavailable) as raised:
            db.select('SELECT 1')
        self.assertNotIn('super-secret', str(raised.exception))

    def test_cloud_private_false_and_lazy_connector(self):
        config = dict(PROGRAM_DATA_SOURCE='cloudsql', DB_USER='user', DB_PASS='secret', DB_NAME='db', INSTANCE_CONNECTION_NAME='project:region:instance', PRIVATE_IP='false')
        with patch('google.cloud.sql.connector.Connector') as connector, patch('sqlalchemy.create_engine') as engine:
            db = Database(config)
            self.addCleanup(db.close)
            connector.assert_not_called()
            db._engine()
            creator = engine.call_args.kwargs['creator']
            creator()
            from google.cloud.sql.connector import IPTypes
            self.assertEqual(connector.return_value.connect.call_args.kwargs['ip_type'], IPTypes.PUBLIC)

    def test_local_password_is_not_interpolated_into_url(self):
        config = dict(PROGRAM_DATA_SOURCE='postgres', DB_USER='user', DB_PASS='p@ss:/word', DB_NAME='db', DB_HOST='localhost', DB_SSLMODE='disable')
        with patch('sqlalchemy.create_engine') as engine:
            db = Database(config)
            self.addCleanup(db.close)
            db._engine()
            self.assertEqual(engine.call_args.args[0].password, config['DB_PASS'])
            self.assertFalse(engine.call_args.kwargs['connect_args']['ssl_context'])


if __name__ == '__main__':
    unittest.main()
