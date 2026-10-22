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
        for name in ('get_program_preferences', 'save_program_preferences', 'reset_user_preferences', 'reset_user_chat', 'get_major_catalog_page', 'get_major_details', 'get_recommendations', 'get_guest_session', 'get_program_favorites', 'get_comparison_favorites', 'is_program_favorite', 'add_program_fav', 'remove_school_fav'):
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
        for name in ('get_program_preferences', 'save_program_preferences', 'reset_user_preferences', 'reset_user_chat', 'get_major_catalog_page', 'get_major_details', 'get_recommendations', 'get_guest_session', 'get_program_favorites', 'get_comparison_favorites', 'is_program_favorite', 'add_program_fav', 'remove_school_fav'):
            getattr(self.database, name).reset_mock()
        self.database.create_or_update_user.return_value = {'id': 42, 'clerk_user_id': 'user_test'}
        self.database.get_program_preferences.return_value = {}
        self.database.get_major_favorites.return_value = []
        self.database.get_recommendations.return_value = []
        self.database.get_guest_session.return_value = None
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
        for destination, expected in [('questionnaire', '/chat'), ('explore', '/explore')]:
            response = self.client.get('/start/' + destination)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers['Location'], expected)
        self.assertEqual(self.client.get('/start/evil').status_code, 404)
        html = self.client.get('/').get_data(as_text=True)
        self.assertNotIn('/start/', html)
        self.assertIn('href="/chat"', html)
        self.assertIn('href="/explore"', html)
        legacy = self.client.get('/questionnaire')
        self.assertEqual(legacy.status_code, 301)
        self.assertEqual(legacy.headers['Location'], '/chat')
        html = self.client.get('/chat').get_data(as_text=True)
        for element in ('chatMessages', 'userInput', 'sendButton', 'resetAdvisorChat',
                        'recommendationsPanel', 'recommendationCards', 'reloadChat', 'chatStorageNote'):
            self.assertIn('id="' + element + '"', html)
        self.assertIn('js/chat-api.js', html)
        self.assertIn('js/guided-chat.js', html)
        self.assertIn('class="chat-workspace"', html)
        self.assertLess(html.index('>Chat</a>'), html.index('>Explore</a>'))
        self.assertLess(html.index('>Explore</a>'), html.index('>Favorites</a>'))
        self.assertNotIn('href="/questionnaire"', html)
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
            self.assertEqual(self.client.get('/explore?major_filter=favorites&favorite_major=7').status_code, 302)
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
            response = self.client.get('/explore?major_name=Biology&favorite_major=8&state=NY')
            self.assertEqual(get_page.call_args.args[3], {'major_name': 'Biology', 'cipcodes': [8], 'state': 'NY'})
            html = response.get_data(as_text=True)
            self.assertIn('<summary>Majors</summary>', html)
            self.assertNotIn('id="major-filter"', html)
            self.assertNotIn('data-filter-toggle="program-school-search"', html)
            self.assertIn('favorite_major=8', html)
            self.assertIn('major_name=Biology', html)
            self.client.get('/explore?preferences_applied=1&major_name=&school_name=&city=&state=')
            self.assertEqual(get_page.call_args.args[3], {})

            self.client.get('/explore?major_filter=favorites')
            self.assertEqual(get_page.call_args.args[3], {})
            self.assertEqual(self.client.get('/explore?major_filter=favorites&favorite_major=999').status_code, 400)
            self.assertEqual(self.client.get('/explore?major_filter=favorites&favorite_major=oops').status_code, 400)
            self.assertEqual(self.client.get('/explore?major_filter=invalid').status_code, 400)
            self.assertEqual(self.client.get('/explore?major_filter=name').status_code, 200)

    def test_favorites_detail_cards_use_owned_database_rows(self):
        self.login()
        self.database.get_comparison_favorites.return_value = [
            {'id': 7, 'name': 'Biology', 'earnings': 50000, 'description': 'Study life'}
        ]
        response = self.client.get('/api/favorites?details=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['favorites'][0]['cipcode'], 7)
        self.assertEqual(response.json['favorites'][0]['earnings'], 50000)
        self.database.get_comparison_favorites.assert_called_with(42, 'majors')
        response = self.client.get('/api/program-favorites?details=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['favorites'][0]['program_id'], 7)
        self.assertIn('/7', response.json['favorites'][0]['url'])
        self.database.get_comparison_favorites.assert_called_with(42, 'programs')

    def test_major_details_page_and_missing_major(self):
        self.database.get_major_details.return_value = {
            'cipcode': 7, 'major': 'Biology', 'description': 'Study living organisms.',
            'earnings': None, 'school_count': 4, 'is_favorite': False,
        }
        response = self.client.get('/majors/7')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Study living organisms.', html)
        self.assertIn('Sign in to save favorites', html)
        self.assertIn('cipcode=7', html)
        self.database.get_major_details.assert_called_with(7, None)
        self.login()
        response = self.client.get('/majors/7')
        self.assertIn('data-major-favorite="7"', response.get_data(as_text=True))
        self.database.get_major_details.assert_called_with(7, 42)
        self.database.get_major_details.return_value = None
        self.assertEqual(self.client.get('/majors/999').status_code, 404)
        self.assertEqual(self.client.get('/majors/0').status_code, 404)

    def test_major_matching_interests_are_private_and_optional(self):
        self.database.get_major_details.return_value = {
            'cipcode': 7, 'major': 'Biology', 'description': None,
            'earnings': None, 'school_count': 4, 'is_favorite': False,
        }
        rec = {'cipcode': 7, 'matching_keywords': 1,
               'evidence': [{'keyword': 'Biology', 'evidence': 'I enjoy <biology>.'}]}
        html = self.client.get('/majors/7').get_data(as_text=True)
        self.assertNotIn('matching-interests-title', html)
        self.database.get_guest_session.assert_not_called()
        self.login()
        self.database.get_recommendations.return_value = [rec]
        html = self.client.get('/majors/7?user_id=99').get_data(as_text=True)
        self.assertIn('1 matching interest', html)
        self.assertIn('I enjoy &lt;biology&gt;.', html)
        self.database.get_recommendations.assert_called_with(42)
        self.database.get_recommendations.return_value = [{**rec, 'cipcode': 8}]
        self.assertNotIn('matching-interests-title', self.client.get('/majors/7').get_data(as_text=True))
        with self.client.session_transaction() as session:
            session.pop('user_id', None)
            session['guest_id'] = 'my-guest'
        self.database.get_guest_session.return_value = {'state': {'recommendations': [rec]}}
        html = self.client.get('/majors/7').get_data(as_text=True)
        self.assertIn('1 matching interest', html)
        self.database.get_guest_session.assert_called_with('my-guest')
        self.database.get_guest_session.return_value = None
        self.assertNotIn('matching-interests-title', self.client.get('/majors/7').get_data(as_text=True))

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
            self.database.get_major_catalog_page.assert_called_once_with(1, query='bio', sort='earnings_desc', earnings_min=100, favorites_only=False, user_id=None)
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
        self.database.get_program_preferences.return_value = {}
        self.database.get_major_favorites.return_value = []
        with patch('degree_path.routes.program_page', return_value={'page':1,'rows':[],'has_next':True}) as programs:
            response = self.client.get('/explore?view=programs&school_name=College&sort=net_price_asc&cipcode=7')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(programs.call_args.args[1], 7)
            self.assertEqual(programs.call_args.args[3]['school_name'], 'College')
            self.assertEqual(programs.call_args.kwargs, {'sort_option':'npt4', 'sort_order':'ASC'})
            self.assertIn('sort=net_price_asc', response.get_data(as_text=True))
        self.assertEqual(self.client.get('/explore?sort=invalid').status_code, 400)






    def test_explore_preferences_save_restore_reset_and_identity(self):
        self.login()
        with self.client.session_transaction() as state:
            csrf = state['csrf']
        filters = {'state': ['NY'], 'city': ['Albany'], 'net_price_max': ['0'],
                   'degree_form': ['1'], 'degree': ['2', '3'], 'tuition_out_max': ['25000'],
                   'sort': ['earnings_desc'], 'major_filter': ['all']}
        body = {'action': 'save', 'view': 'programs', 'filters': filters, 'user_id': 99}
        self.assertEqual(self.client.post('/api/explore/preferences', json=body).status_code, 400)
        response = self.client.post('/api/explore/preferences', json=body, headers={'X-CSRF-Token': csrf})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.database.save_program_preferences.call_args.args[0], 42)
        self.assertEqual(self.database.save_program_preferences.call_args.args[1]['degrees'], ['2,3'])
        self.assertIn('tuition_out_max=25000', response.json['url'])
        self.database.get_program_preferences.return_value = {'state':['NY'], 'city':['Albany'], 'net_price_max':['0'], 'degrees':['2,3']}
        response = self.client.get('/explore?cipcode=7')
        self.assertEqual(response.status_code, 302)
        self.assertIn('cipcode=7', response.location)
        self.assertIn('tuition_out_max=25000', response.location)
        response = self.client.post('/api/explore/preferences', json={'action':'reset'}, headers={'X-CSRF-Token': csrf})
        self.assertEqual(response.status_code, 200)
        self.database.reset_user_preferences.assert_called_once_with(42)
        with self.client.session_transaction() as state:
            self.assertNotIn('explore_preferences', state)

    def test_guest_preferences_and_chat_reset_preserve_other_state(self):
        state = {'messages': [{'role':'user','content':'hello'}], 'keywords':[{'keyword_id':1}],
                 'recommendations':[{'cipcode':7}], 'explore_preferences': {'majors':{'q':['bio']}}}
        with patch('degree_path.routes.get_or_create_guest_session', return_value=('g', {'state':state,'version':4})), \
             patch.object(self.database, 'save_guest_session', create=True, return_value=5) as save:
            response = self.client.post('/api/explore/preferences', json={'action':'save', 'view':'programs',
                'filters':{'state':['NY']}}, headers={'X-CSRF-Token':'test-csrf'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(save.call_args.args[1]['messages'], state['messages'])
            response = self.client.post('/api/chat/reset', json={}, headers={'X-CSRF-Token':'test-csrf'})
            self.assertEqual(response.status_code, 200)
            updated = save.call_args.args[1]
            self.assertEqual(updated['messages'], [])
            self.assertEqual(updated['keywords'], [])
            self.assertEqual(updated['recommendations'], [])
            self.assertEqual(updated['explore_preferences'], state['explore_preferences'])
            self.assertEqual(state['keywords'], [{'keyword_id':1}])
            save.return_value = None
            self.assertEqual(self.client.post('/api/chat/reset', json={}, headers={'X-CSRF-Token':'test-csrf'}).status_code, 409)

    def test_account_chat_reset_requires_csrf_and_uses_session(self):
        self.login()
        with self.client.session_transaction() as state:
            csrf = state['csrf']
        self.assertEqual(self.client.post('/api/chat/reset', json={}).status_code, 400)
        response = self.client.post('/api/chat/reset', json={'user_id':99}, headers={'X-CSRF-Token':csrf})
        self.assertEqual(response.status_code, 200)
        self.database.reset_user_chat.assert_called_once_with(42)

    def test_explore_preference_validation_and_major_view(self):
        from degree_path.preferences import validate_explore_preferences
        for values in [{'degree':['5'], 'degree_form':['1']}, {'acceptance_min':['90'], 'acceptance_max':['10']},
                       {'sort':['sql']}, {'net_price_max':['-1']}, {'extra':['x']}]:
            with self.assertRaises(ValueError):
                validate_explore_preferences('programs', values)
        self.assertEqual(validate_explore_preferences('majors', {'q':['bio'], 'earnings_min':['0']}),
                         {'q':['bio'], 'earnings_min':['0']})
        self.login()
        with self.client.session_transaction() as state:
            csrf = state['csrf']
        response = self.client.post('/api/explore/preferences', json={'action':'save','view':'majors',
            'filters':{'q':['bio'], 'sort':['earnings_desc']}}, headers={'X-CSRF-Token':csrf})
        self.assertEqual(response.status_code, 200)
        self.assertIn('q=bio', self.client.get('/explore?view=majors').location)
        self.database.save_program_preferences.assert_not_called()

    def test_missing_preferences_do_not_block_explore_or_check_filters(self):
        self.login()
        data = {'page':1, 'has_next':False, 'rows':[]}
        with patch('degree_path.routes.program_page', return_value=data) as query:
            for preferences in ({}, {'state':[''], 'city':[''], 'degrees':[''], 'net_price_max':['']},
                                {'state':[None], 'degrees':[None]}):
                self.database.get_program_preferences.return_value = preferences
                response = self.client.get('/explore')
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertNotRegex(html, r'<input[^>]*\schecked(?:\s|>)')
                self.assertEqual(query.call_args.args[2], ())
            self.database.get_program_preferences.side_effect = RuntimeError('Optional profile unavailable')
            try:
                with self.assertLogs(self.app.logger, level='ERROR'):
                    self.assertEqual(self.client.get('/explore').status_code, 200)
            finally:
                self.database.get_program_preferences.side_effect = None

    def test_visible_preferences_are_checked_and_used_for_program_query(self):
        self.login()
        self.database.get_program_preferences.return_value = {'state':['NY'], 'city':['Albany'],
            'degrees':['3'], 'net_price_max':['0']}
        data = {'page':1, 'has_next':False, 'rows':[]}
        with patch('degree_path.routes.program_page', return_value=data) as query:
            response = self.client.get('/explore', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(query.call_args.args[2], (3,))
            self.assertEqual(query.call_args.args[3]['state'], 'NY')
            self.assertEqual(query.call_args.args[3]['net_price_max'], 0)
            html = response.get_data(as_text=True)
            self.assertNotIn('data-filter-toggle="filter-state"', html)
            self.assertNotIn('data-filter-toggle=', html)
            self.assertNotRegex(html, r"<details[^>]*\bopen\b")
            self.assertIn('value="3" checked', html)
            self.assertNotIn('data-filter-toggle="filter-tuition_in_max" checked', html)
            self.client.get('/explore?preferences_applied=1')
            self.assertEqual(query.call_args.args[3], {})
            self.assertEqual(query.call_args.args[2], ())


if __name__ == '__main__':
    unittest.main()
