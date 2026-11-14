"""Offline secret-loading tests. Never contact Google or the database."""
import ast
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import secret_loader


class SecretLoaderTests(unittest.TestCase):
    def setUp(self):
        secret_loader.read_secret.cache_clear()
        self.addCleanup(secret_loader.read_secret.cache_clear)
        self.references = {
            key + "_SECRET_VERSION": "projects/test/secrets/" + key.lower() + "/versions/1"
            for key in ("GEMINI_API_KEY", "CLERK_SECRET_KEY", "CLERK_PUBLISHABLE_KEY", "SECRET_KEY")
        }

    def test_read_decodes_and_caches_each_version(self):
        with patch.object(secret_loader.secretmanager, "SecretManagerServiceClient") as factory:
            client = factory.return_value.__enter__.return_value
            client.access_secret_version.return_value = SimpleNamespace(payload=SimpleNamespace(data=b"actual-key"))
            path = self.references["GEMINI_API_KEY_SECRET_VERSION"]
            self.assertEqual(secret_loader.read_secret(path), "actual-key")
            self.assertEqual(secret_loader.read_secret(path), "actual-key")
            client.access_secret_version.assert_called_once_with(request={"name": path}, timeout=15)
            secret_loader.read_secret(path.replace('/1', '/2'))
            self.assertEqual(client.access_secret_version.call_count, 2)

    def test_reference_values_replace_stale_environment_keys(self):
        with patch.dict(os.environ, {**self.references, 'GEMINI_API_KEY':'old-key'}, clear=True):
            with patch.object(secret_loader, 'read_secret', side_effect=lambda path: 'value-' + path.split('/')[-3]):
                secret_loader.load_application_secrets()
            for name in ('GEMINI_API_KEY','CLERK_SECRET_KEY','CLERK_PUBLISHABLE_KEY','SECRET_KEY'):
                self.assertEqual(os.environ[name], 'value-' + name.lower())
                self.assertEqual(os.environ[name + '_SECRET_VERSION'], self.references[name + '_SECRET_VERSION'])

    def test_missing_reference_fails_before_any_network_request(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(secret_loader, 'read_secret') as read:
            with self.assertRaisesRegex(RuntimeError, 'GEMINI_API_KEY_SECRET_VERSION'):
                secret_loader.load_application_secrets()
            read.assert_not_called()

    def test_failed_fetch_does_not_partially_update_environment(self):
        with patch.dict(os.environ, {**self.references,'GEMINI_API_KEY':'old-key'}, clear=True):
            with patch.object(secret_loader, 'read_secret', side_effect=['new-key', PermissionError('denied')]):
                with self.assertRaises(PermissionError):
                    secret_loader.load_application_secrets()
            self.assertEqual(os.environ['GEMINI_API_KEY'], 'old-key')
            self.assertNotIn('SECRET_KEY', os.environ)

    def test_empty_secret_rejected_and_not_cached(self):
        with patch.object(secret_loader.secretmanager, 'SecretManagerServiceClient') as factory:
            client = factory.return_value.__enter__.return_value
            client.access_secret_version.return_value = SimpleNamespace(payload=SimpleNamespace(data=b''))
            with self.assertRaises(RuntimeError): secret_loader.read_secret('projects/test/secrets/key/versions/1')
            client.access_secret_version.return_value = SimpleNamespace(payload=SimpleNamespace(data=b'valid'))
            self.assertEqual(secret_loader.read_secret('projects/test/secrets/key/versions/1'), 'valid')
            self.assertEqual(client.access_secret_version.call_count, 2)

    def test_database_password_uses_shared_loader(self):
        path = Path(__file__).resolve().parents[1] / 'cloud_sql_connection.py'
        tree = ast.parse(path.read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'get_database_password')
        read = Mock(return_value='db-password')
        namespace = {'os':os, 'read_secret':read}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
        with patch.dict(os.environ, {'DB_PASSWORD_SECRET_VERSION':'projects/test/secrets/db/versions/1'}):
            self.assertEqual(namespace['get_database_password'](), 'db-password')
        read.assert_called_once_with('projects/test/secrets/db/versions/1')

    def test_app_startup_resolves_keys_before_config_and_tests_skip_fetch(self):
        # Isolate imports from the other route tests and mock every external service.
        import subprocess
        import sys
        code = """
import os, sys
from types import ModuleType
from unittest.mock import Mock, patch
from flask import Blueprint
import degree_path
fake_db = ModuleType('db_functions')
fake_db.engine = object()
fake_db.warm_database_connections = Mock()
auth = ModuleType('degree_path.auth')
auth.expire_login = lambda: None
routes = ModuleType('degree_path.routes')
routes.web = Blueprint('web', __name__)
comparison = ModuleType('degree_path.saved_comparison')
def load():
    os.environ.update(SECRET_KEY='resolved-flask', CLERK_SECRET_KEY='resolved-clerk',
                      CLERK_PUBLISHABLE_KEY='resolved-public')
with patch.dict(sys.modules, {'db_functions':fake_db,'degree_path.auth':auth,
                             'degree_path.routes':routes,'degree_path.saved_comparison':comparison}), \
     patch.dict(os.environ, {'CLERK_AUTHORIZED_PARTIES':'http://localhost'}, clear=True), \
     patch.object(degree_path, 'load_dotenv'), \
     patch.object(degree_path, 'load_application_secrets', side_effect=load) as loader:
    app = degree_path.create_app()
    loader.assert_called_once()
    assert app.config['SECRET_KEY'] == 'resolved-flask'
    assert app.config['CLERK_SECRET_KEY'] == 'resolved-clerk'
    assert app.config['CLERK_PUBLISHABLE_KEY'] == 'resolved-public'
    fake_db.warm_database_connections.assert_called_once()
    loader.reset_mock()
    degree_path.create_app({'TESTING':True})
    loader.assert_not_called()
"""
        result = subprocess.run([sys.executable, '-c', code],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
