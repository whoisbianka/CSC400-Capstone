"""Run with python -m unittest discover -s tests from python-demo-flask."""
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from degree_path import create_app
from degree_path.favorites import favorites_engine as favorites_engine_original


class FavoritesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only'})
        self.app.extensions['clerk_jwks'] = SimpleNamespace(
            get_signing_key_from_jwt=lambda token: SimpleNamespace(key=self.private_key.public_key()))
        self.engine = create_engine('sqlite://')
        with self.engine.begin() as connection:
            connection.execute(text('CREATE TABLE majors (cipcode INTEGER PRIMARY KEY, cipdesc TEXT)'))
            connection.execute(text("INSERT INTO majors VALUES (1107, 'Computer Science')"))
            connection.execute(text('''CREATE TABLE saved_majors (
                clerk_user_id TEXT, cipcode INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (clerk_user_id, cipcode))'''))
        self.engine_patch = patch('degree_path.favorites.favorites_engine', return_value=self.engine)
        self.engine_patch.start()
        self.addCleanup(self.engine_patch.stop)
        self.addCleanup(self.engine.dispose)
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session['csrf'] = 'test-csrf'

    def headers(self, user='user_alice', **overrides):
        now = int(time.time())
        claims = dict(sub=user, iss='https://supreme-grub-6049.clerk.accounts.dev',
                      azp='http://localhost', iat=now, nbf=now, exp=now + 60)
        claims.update(overrides)
        token = jwt.encode(claims, self.private_key, algorithm='RS256')
        return {'Authorization': 'Bearer ' + token, 'X-CSRF-Token': 'test-csrf'}

    def save(self, user='user_alice', saved=True, cipcode=1107):
        return self.client.post(f'/api/saved-majors/{cipcode}', json={'saved': saved}, headers=self.headers(user))

    def test_guest_and_invalid_token_rejected(self):
        self.assertEqual(self.client.get('/api/saved-majors').status_code, 401)
        self.assertEqual(self.client.post('/api/saved-majors/1107', json={'saved': True},
            headers={'X-CSRF-Token': 'test-csrf'}).status_code, 401)
        self.assertEqual(self.client.get('/api/saved-majors', headers={
            'Authorization': 'Bearer forged'}).status_code, 401)

    def test_expired_wrong_issuer_and_wrong_origin_rejected(self):
        for overrides in [{'exp': int(time.time()) - 30}, {'iss': 'https://other.example'},
                          {'azp': 'https://other.example'}]:
            with self.subTest(overrides=overrides):
                self.assertEqual(self.client.get('/api/saved-majors', headers=self.headers(**overrides)).status_code, 401)

    def test_save_duplicate_and_remove(self):
        self.assertEqual(self.save().status_code, 200)
        self.assertEqual(self.save().status_code, 200)
        response = self.client.get('/api/saved-majors', headers=self.headers())
        self.assertEqual(response.json['majors'], [{'cipcode': 1107, 'name': 'Computer Science'}])
        self.assertEqual(self.save(saved=False).status_code, 200)
        self.assertEqual(self.client.get('/api/saved-majors', headers=self.headers()).json['majors'], [])

    def test_account_ownership(self):
        self.save()
        self.assertEqual(self.client.get('/api/saved-majors', headers=self.headers('user_bob')).json['majors'], [])
        self.save(user='user_bob', saved=False)
        self.assertEqual(len(self.client.get('/api/saved-majors', headers=self.headers()).json['majors']), 1)

    def test_csrf_input_validation_and_missing_major(self):
        headers = self.headers()
        del headers['X-CSRF-Token']
        self.assertEqual(self.client.post('/api/saved-majors/1107', json={'saved': True}, headers=headers).status_code, 400)
        self.assertEqual(self.client.post('/api/saved-majors/1107', json={'saved': 'true'}, headers=self.headers()).status_code, 400)
        self.assertEqual(self.save(cipcode=9999).status_code, 404)

    def test_saved_page_has_navigation_and_signin_script(self):
        response = self.client.get('/saved-majors')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="saved-majors-list"', response.data)
        self.assertIn(b'js/favorites.js', response.data)
        self.assertIn(b'csrf-token', response.data)

    def test_existing_table_needs_no_runtime_schema_permissions(self):
        # Use the real setup function instead of the ordinary test shortcut.
        with self.app.app_context(), patch('db_functions.engine', self.engine), \
                patch.object(self.engine, 'begin', side_effect=AssertionError('Unexpected schema creation')):
            self.assertIs(favorites_engine_original(), self.engine)

    def test_missing_setup_permissions_return_a_specific_error(self):
        from degree_path import favorites
        original = Exception({'C': '42501', 'M': 'permission denied for table majors'})
        denied = DBAPIError('CREATE TABLE', {}, original)
        with patch.object(favorites, 'inspect', side_effect=denied), \
                self.app.app_context(), self.assertLogs(self.app.logger, level='ERROR') as logs:
            # Re-enable the real setup function for this authenticated request.
            with patch.object(favorites, 'favorites_engine', favorites_engine_original):
                response = self.save()
        self.assertEqual(response.status_code, 503)
        self.assertIn('Saving majors is not set up yet', response.json['error'])
        self.assertNotIn('permission denied', response.json['error'])
        self.assertIn('schemas/saved_majors.sql', logs.output[0])


if __name__ == '__main__':
    unittest.main()
