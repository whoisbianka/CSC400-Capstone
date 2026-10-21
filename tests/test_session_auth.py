"""Offline login/session integration tests; Clerk and the database are mocked."""
import sys
import time
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch


class SessionAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = ModuleType('db_functions')
        cls.database.create_or_update_user = Mock()
        cls.database.get_major_favorites = Mock()
        for name in ('get_major_catalog_page', 'get_program_favorites', 'get_comparison_favorites', 'is_program_favorite', 'add_program_fav', 'remove_school_fav'):
            setattr(cls.database, name, Mock())
        # Import the app with no Cloud SQL initialization.
        cls.modules_patch = patch.dict(sys.modules, {'db_functions': cls.database})
        cls.modules_patch.start()
        cls.addClassCleanup(cls.modules_patch.stop)
        from degree_path import create_app
        cls.app = create_app({
            'TESTING': True,
            'SECRET_KEY': 'offline-test-secret',
            'CLERK_SECRET_KEY': 'offline-test-key',
            'CLERK_PUBLISHABLE_KEY': 'pk_test_example',
            'CLERK_AUTHORIZED_PARTIES': ['http://localhost'],
            'SESSION_COOKIE_SECURE': False,
        })

    def setUp(self):
        self.client = self.app.test_client()
        self.database.create_or_update_user.reset_mock()
        self.database.get_major_favorites.reset_mock()
        for name in ('get_major_catalog_page', 'get_program_favorites', 'get_comparison_favorites', 'is_program_favorite', 'add_program_fav', 'remove_school_fav'):
            getattr(self.database, name).reset_mock()
        self.database.create_or_update_user.return_value = {'id': 42, 'clerk_user_id': 'user_test'}
        self.database.get_major_favorites.return_value = []
        with self.client.session_transaction() as s:
            s['csrf'] = 'test-csrf'

    def login(self, signed_in=True):
        state = SimpleNamespace(is_signed_in=signed_in, payload={'sub': 'user_test'})
        with patch('degree_path.auth.Clerk') as clerk:
            clerk.return_value.__enter__.return_value.authenticate_request.return_value = state
            return self.client.post('/api/auth/session', json={}, headers={
                'Authorization': 'Bearer offline-token', 'X-CSRF-Token': 'test-csrf',
            })

    def test_verified_login_and_cookie_only_favorites(self):
        self.assertEqual(self.login().status_code, 200)
        with self.client.session_transaction() as s:
            self.assertEqual(s['user_id'], 42)
            self.assertNotEqual(s['csrf'], 'test-csrf')
        with patch('degree_path.auth.Clerk', side_effect=AssertionError('Unexpected Clerk call')):
            for _ in range(2):
                response = self.client.get('/api/favorites', headers={'X-App-User-ID': '42'})
                self.assertEqual(response.status_code, 200)
        self.database.create_or_update_user.assert_called_once_with('user_test')
        self.database.get_major_favorites.assert_called_with(42)

    def test_login_persists_for_24_hours_without_sliding_expiration(self):
        started = int(time.time())
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIn('Expires=', response.headers['Set-Cookie'])
        with self.client.session_transaction() as s:
            self.assertTrue(s.permanent)
            expires = s['login_expires_at']
            self.assertGreaterEqual(expires, started + 86400)
            self.assertLessEqual(expires, int(time.time()) + 86400)
        # A new browser client retaining the persistent cookie stays logged in.
        cookie_name = self.app.config['SESSION_COOKIE_NAME']
        cookie = self.client.get_cookie(cookie_name)
        self.assertIsNotNone(cookie.expires)
        reopened = self.app.test_client()
        reopened.set_cookie(cookie_name, cookie.value)
        response = reopened.get('/api/favorites', headers={'X-App-User-ID': '42'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Set-Cookie', response.headers)
        with reopened.session_transaction() as s:
            self.assertEqual(s['login_expires_at'], expires)

    def test_navigation_uses_session(self):
        html = self.client.get('/favorites').get_data(as_text=True)
        self.assertIn('data-auth-action="login"', html)
        self.assertNotIn('>Profile</a>', html)
        self.login()
        html = self.client.get('/favorites').get_data(as_text=True)
        self.assertIn('data-auth-action="logout"', html)
        self.assertNotIn('data-auth-action="login"', html)

    def test_invalid_token_and_untrusted_user_id_cannot_login(self):
        self.assertEqual(self.login(False).status_code, 401)
        response = self.client.post('/api/auth/session', json={'user_id': 42}, headers={'X-CSRF-Token': 'test-csrf'})
        self.assertEqual(response.status_code, 401)
        self.database.create_or_update_user.assert_not_called()
        self.assertEqual(self.client.get('/api/favorites').status_code, 401)

    def test_csrf_required_for_login_and_logout(self):
        self.assertEqual(self.client.post('/api/auth/session', json={}).status_code, 400)
        self.login()
        self.assertEqual(self.client.post('/logout').status_code, 400)
        with self.client.session_transaction() as s:
            self.assertEqual(s['user_id'], 42)

    def test_logout_clears_account(self):
        self.login()
        with self.client.session_transaction() as s:
            csrf = s['csrf']
            s['guest_id'] = 'old-guest'
            s['extra_state'] = 'old-state'
        response = self.client.post('/logout', data={'csrf_token': csrf})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Max-Age=0', response.headers['Set-Cookie'])
        with self.client.session_transaction() as s:
            self.assertEqual(dict(s), {})
        self.assertEqual(self.client.get('/api/favorites').status_code, 401)

    def test_expired_login_and_stale_tab_rejected(self):
        self.login()
        with self.client.session_transaction() as s:
            s['login_expires_at'] = time.time() - 1
        response = self.client.get('/api/chat', headers={'X-App-User-ID': '42'})
        self.assertEqual(response.status_code, 401)
        html = self.client.get('/favorites').get_data(as_text=True)
        self.assertIn('data-auth-action="login"', html)

    def test_account_switch_rejects_old_tab(self):
        self.login()
        response = self.client.get('/api/favorites', headers={'X-App-User-ID': '99'})
        self.assertEqual(response.status_code, 401)
        self.database.get_major_favorites.assert_not_called()

    def test_chat_and_explore_skip_account_choice(self):
        for destination, expected in [('questionnaire', '/questionnaire'), ('explore', '/explore')]:
            response = self.client.get('/start/' + destination)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers['Location'], expected)
        self.assertEqual(self.client.get('/start/evil').status_code, 404)
        html = self.client.get('/').get_data(as_text=True)
        self.assertNotIn('/start/', html)
        self.assertIn('href="/questionnaire"', html)
        self.assertIn('href="/explore"', html)
        html = self.client.get('/questionnaire').get_data(as_text=True)
        self.assertIn('id="guided-chat"', html)
        self.assertNotIn('How would you like to continue', html)

    def test_guest_favorites_has_signin_and_home_without_data_requests(self):
        html = self.client.get('/favorites').get_data(as_text=True)
        self.assertIn('Back to home', html)
        self.assertIn('data-auth-action="login"', html)
        self.assertNotIn('js/favorites.js', html)
        self.assertNotIn('Loading favorites', html)
        self.database.get_major_favorites.assert_not_called()
        self.login()
        html = self.client.get('/favorites').get_data(as_text=True)
        self.assertIn('js/favorites.js', html)
        self.assertIn('data-favorite-kind="majors"', html)
        self.assertIn('data-favorite-kind="programs"', html)
        self.assertNotIn('Back to home', html)

    def test_comparison_requires_login_and_valid_kind(self):
        self.assertEqual(self.client.get('/api/compare').status_code, 401)
        self.assertEqual(self.client.get('/api/compare?kind=invalid').status_code, 400)
        html = self.client.get('/compare').get_data(as_text=True)
        self.assertIn('Back to home', html)
        self.assertIn('data-auth-action="login"', html)
        self.assertNotIn('js/compare.js', html)
        self.login()
        html = self.client.get('/compare').get_data(as_text=True)
        self.assertIn('data-compare-kind="majors"', html)
        self.assertIn('data-compare-kind="programs"', html)
        self.database.get_comparison_favorites.assert_not_called()

    def test_comparison_reads_only_session_user(self):
        self.login()
        self.database.get_comparison_favorites.return_value = [{'id': 7, 'name': 'Biology', 'earnings': None}]
        result = self.client.get('/api/compare?kind=majors&user_id=99')
        self.assertEqual(result.status_code, 200)
        self.database.get_comparison_favorites.assert_called_once_with(42, 'majors')
        self.assertIsNone(result.json['items'][0]['earnings'])
        self.assertEqual(result.json['metrics'][0]['direction'], 'higher')
        self.assertEqual(self.client.get('/api/compare', headers={'X-App-User-ID': '99'}).status_code, 401)

    def test_program_favorite_requires_login_and_csrf(self):
        self.assertEqual(self.client.get('/api/program-favorites/9').status_code, 401)
        self.login()
        with self.client.session_transaction() as s:
            csrf = s['csrf']
        self.assertEqual(self.client.post('/api/program-favorites/9', json={'favorite': True}).status_code, 400)
        self.database.add_program_fav.return_value = True
        response = self.client.post('/api/program-favorites/9', json={'favorite': True, 'user_id': 99}, headers={'X-CSRF-Token': csrf})
        self.assertEqual(response.status_code, 200)
        self.database.add_program_fav.assert_called_once_with(42, 9)
        response = self.client.post('/api/program-favorites/9', json={'favorite': False}, headers={'X-CSRF-Token': csrf})
        self.assertEqual(response.status_code, 200)
        self.database.remove_school_fav.assert_called_once_with(42, 9)
        self.database.add_program_fav.return_value = False
        self.assertEqual(self.client.post('/api/program-favorites/999', json={'favorite': True}, headers={'X-CSRF-Token': csrf}).status_code, 404)
        self.assertEqual(self.client.post('/api/program-favorites/9', json={'favorite': 'yes'}, headers={'X-CSRF-Token': csrf}).status_code, 400)

    def test_program_favorite_list_uses_session_and_returns_links(self):
        self.assertEqual(self.client.get('/api/program-favorites').status_code, 401)
        self.database.get_program_favorites.assert_not_called()
        self.login()
        self.database.get_program_favorites.return_value = [{'program_id': 10, 'major': 'Biology', 'credlev': 3}]
        response = self.client.get('/api/program-favorites?user_id=99')
        self.assertEqual(response.status_code, 200)
        self.database.get_program_favorites.assert_called_once_with(42)
        self.assertEqual(response.json['favorites'][0]['url'], '/programs/10')
        self.assertEqual(response.json['favorites'][0]['credential'], 'Bachelor’s degree')
        self.assertEqual(self.client.get('/api/program-favorites', headers={'X-App-User-ID': '99'}).status_code, 401)

    def test_explore_cards_offer_favorites_for_guests_and_users(self):
        data = {'page': 1, 'has_next': False, 'rows': [{'id': 10, 'college': 'Test College', 'major': 'Biology', 'city': 'City', 'state': 'NY', 'facts': {}}]}
        with patch('degree_path.routes.program_page', return_value=data):
            html = self.client.get('/explore').get_data(as_text=True)
            self.assertIn('Favorite program</a>', html)
            self.assertNotIn('js/program-card-favorites.js', html)
            self.login()
            html = self.client.get('/explore').get_data(as_text=True)
            self.assertIn('data-program-favorite="10"', html)
            self.assertIn('js/program-card-favorites.js', html)

    def test_explore_major_search_and_favorite_selection_persist(self):
        data = {'page': 1, 'has_next': True, 'rows': []}
        with patch('degree_path.routes.program_page', return_value=data) as get_page:
            response = self.client.get('/explore?major_filter=name&major_name=Biology&state=NY')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(get_page.call_args.args[3], {'state': 'NY', 'major_name': 'Biology'})
            self.assertIn('major_name=Biology', response.get_data(as_text=True))
            self.assertEqual(self.client.get('/explore?major_filter=favorites').status_code, 302)
            self.login()
            self.database.get_major_favorites.return_value = [{'cipcode':7, 'major':'Biology'}, {'cipcode':8, 'major':'Art'}]
            response = self.client.get('/explore?major_filter=favorites&favorite_major=7&favorite_major=8&degrees=3')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(get_page.call_args.args[3]['cipcodes'], [7, 8])
            self.assertEqual(get_page.call_args.args[2], (3,))
            html = response.get_data(as_text=True)
            self.assertIn('favorite_major=7', html)
            self.assertIn('favorite_major=8', html)
            self.assertIn('value="7" checked', html)
            self.client.get('/explore?major_filter=favorites')
            self.assertEqual(get_page.call_args.args[3]['cipcodes'], [])
            self.assertEqual(self.client.get('/explore?major_filter=favorites&favorite_major=999').status_code, 400)
            self.assertEqual(self.client.get('/explore?major_filter=favorites&favorite_major=oops').status_code, 400)
            self.assertEqual(self.client.get('/explore?major_filter=invalid').status_code, 400)
            self.assertEqual(self.client.get('/explore?major_filter=name').status_code, 400)

    def test_major_name_api_short_query_needs_no_database(self):
        response = self.client.get('/api/major-names?q=b')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'majors': []})
        self.assertEqual(self.client.get('/api/major-names?q=' + 'a' * 201).status_code, 400)

    def test_explore_tabs_separate_catalogs_and_keep_major_filters(self):
        self.database.get_major_catalog_page.return_value = {
            'page': 1, 'has_next': True, 'rows': [{'cipcode':7, 'major':'Biology', 'earnings':None,
             'program_count':2, 'school_count':1, 'description':None, 'description_source':None, 'is_favorite':False}]}
        with patch('degree_path.routes.program_page') as programs:
            response = self.client.get('/explore?view=majors&q=bio&sort=earnings_desc&earnings_min=100&has_programs=1')
            self.assertEqual(response.status_code, 200)
            programs.assert_not_called()
            self.database.get_major_catalog_page.assert_called_once_with(1, query='bio', sort='earnings_desc', earnings_min=100, favorites_only=False, has_programs=True, user_id=None)
            html = response.get_data(as_text=True)
            self.assertIn('Explore majors</h1>', html)
            self.assertIn('q=bio', html)
            self.assertIn('sort=earnings_desc', html)
            self.assertIn('cipcode=7', html)
            self.assertIn('view=programs', html)
        self.assertEqual(self.client.get('/explore?view=invalid').status_code, 400)
        self.assertEqual(self.client.get('/explore?view=majors&favorites_only=1').status_code, 302)
        self.login()
        response = self.client.get('/explore?view=majors&favorites_only=1&user_id=99')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.database.get_major_catalog_page.call_args.kwargs['user_id'], 42)
        self.assertIn('data-major-favorite="7"', response.get_data(as_text=True))
        self.database.get_major_favorites.return_value = []
        with patch('degree_path.routes.program_page', return_value={'page':1,'rows':[],'has_next':True}) as programs:
            response = self.client.get('/explore?view=programs&school_name=College&sort=net_price_asc&cipcode=7')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(programs.call_args.args[1], 7)
            self.assertEqual(programs.call_args.args[3]['school_name'], 'College')
            self.assertEqual(programs.call_args.kwargs, {'sort_option':'npt4', 'sort_order':'ASC'})
            self.assertIn('sort=net_price_asc', response.get_data(as_text=True))
        self.assertEqual(self.client.get('/explore?sort=invalid').status_code, 400)


if __name__ == '__main__':
    unittest.main()
