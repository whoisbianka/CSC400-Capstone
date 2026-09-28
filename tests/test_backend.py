import unittest
from degree_path import create_app
from degree_path.repositories.programs import DemoProgramRepository
from degree_path.services.search import search

load_programs = DemoProgramRepository().all


class SearchTests(unittest.TestCase):
    def test_documented_queries(self):
        cases = [
            ('Which colleges offer computer science?', 3),
            ('Show nursing programs in Connecticut', 1),
            ('Show online business programs under $20,000', 1),
            ('Compare psychology and sociology', 3),
            ('Show public engineering programs under $20,000', 1),
            ('I enjoy drawing and graphic design', 1),
            ('Show computer science programs in Texas', 0),
            ('Show all programs', 15),
            ('hello there', 0),
        ]
        for question, expected in cases:
            with self.subTest(question=question):
                result = search(question, load_programs())
                self.assertEqual(len(result['rows']), expected)
                self.assertTrue(result['demo'])
                self.assertEqual(result['engine'], 'python')

    def test_budget_boundary_and_missing_cost(self):
        programs = load_programs()[:1]
        self.assertEqual(len(search('computer science under $12,000', programs)['rows']), 0)
        self.assertEqual(len(search('computer science up to 12k', programs)['rows']), 1)
        programs[0]['tuition'] = None
        self.assertEqual(len(search('computer science under $20,000', programs)['rows']), 0)

    def test_campus_format_and_state_abbreviation(self):
        rows = search('computer science on campus in CT', load_programs())['rows']
        self.assertEqual([p['id'] for p in rows], ['demo-1'])


class FlaskTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only', 'PROGRAM_DATA_SOURCE': 'demo'})
        self.client = self.app.test_client()

    def post(self, path, data, client=None):
        client = client or self.client
        client.get('/')
        with client.session_transaction() as session:
            token = session['csrf']
        return client.post(path, data={**data, 'csrf_token': token}, follow_redirects=True)

    def complete_questionnaire(self, answer='computer science'):
        for step in range(5):
            response = self.post(f'/questionnaire/{step}', {'answer': answer})
            self.assertEqual(response.status_code, 200)
        return self.client.get('/questionnaire/results')

    def test_pages_and_static_assets(self):
        for path in ['/', '/explore', '/questionnaire', '/profile', '/settings', '/programs/demo-1', '/static/js/forms.js']:
            with self.subTest(path=path):
                response = self.client.get(path, follow_redirects=True)
                self.assertEqual(response.status_code, 200)
                response.close()
        for path in ['/.git/config', '/degree_path/routes.py', '/data/demo_programs.json', '/static/../routes.py', '/programs/missing']:
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_chat_without_javascript_and_reload(self):
        response = self.post('/', {'question': 'computer science'})
        self.assertIn(b'3 demo programs matched.', response.data)
        self.assertIn(b'/programs/demo-1', response.data)
        self.assertEqual(self.client.get('/').data.count(b'3 demo programs matched.'), 1)
        self.assertNotIn(b'3 demo programs matched.', self.app.test_client().get('/').data)
        self.assertNotIn(b'3 demo programs matched.', self.post('/chat/reset', {}).data)

    def test_validation_and_escaping(self):
        for value in ['', ' ', 'a' * 2001]:
            self.assertEqual(self.post('/', {'question': value}).status_code, 400)
        response = self.post('/', {'question': '<script>alert(1)</script>'})
        self.assertNotIn(b'<script>alert(1)</script>', response.data)
        self.assertIn(b'&lt;script&gt;', response.data)
        self.assertEqual(self.post('/questionnaire/0', {'answer': ' '}).status_code, 400)

    def test_csrf_and_no_state_mutation(self):
        self.client.get('/')
        for token in ['', 'wrong', 'é']:
            response = self.client.post('/', data={'question': 'computer science', 'csrf_token': token})
            self.assertEqual(response.status_code, 400)
        self.assertNotIn(b'3 demo programs matched.', self.client.get('/').data)

    def test_questionnaire_review_edit_filter_reset(self):
        self.assertEqual(self.client.get('/questionnaire/results').status_code, 302)
        response = self.complete_questionnaire()
        self.assertIn(b'3 demo programs matched.', response.data)
        self.assertIn(b'computer science', self.client.get('/questionnaire/review').data)
        filtered = self.client.get('/questionnaire/results?format=Online')
        self.assertIn(b'Pinecrest Demo College', filtered.data)
        self.assertNotIn(b'Harbor Demo University', filtered.data)
        # A changed answer is included in the newly calculated result.
        self.post('/questionnaire/0', {'answer': 'computer science in Texas'})
        self.assertIn(b'No demo programs match', self.client.get('/questionnaire/results').data)
        self.post('/questionnaire/reset', {})
        self.assertEqual(self.client.get('/questionnaire/results').status_code, 302)

    def test_large_answers_stay_out_of_cookie(self):
        response = self.complete_questionnaire('computer science ' + 'x' * 1900)
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session:
            self.assertEqual(set(session), {'csrf', 'demo_id'})
        other = self.app.test_client()
        self.assertEqual(other.get('/questionnaire/results').status_code, 302)

    def test_explore_filter_and_sort(self):
        response = self.client.get('/explore?q=computer+science&format=Online')
        self.assertIn(b'Pinecrest Demo College', response.data)
        self.assertNotIn(b'Harbor Demo University', response.data)
        response = self.client.get('/explore?q=computer+science&sort=tuition&direction=desc')
        self.assertLess(response.data.index(b'Pinecrest Demo College'), response.data.index(b'Harbor Demo University'))
        self.assertIn(b'No programs match', self.client.get('/explore?q=unmatchable').data)
        self.assertEqual(self.client.get('/explore?sort=invalid').status_code, 200)

    def test_legacy_links(self):
        self.assertEqual(self.client.get('/index.html?mode=guided').location, '/questionnaire')
        self.assertEqual(self.client.get('/explore.html').location, '/explore')
        self.assertEqual(self.client.get('/profile.html').location, '/profile')

    def test_api_contract(self):
        self.assertEqual(self.client.get('/api/health').json['framework'], 'flask')
        self.assertEqual(len(self.client.get('/api/programs').json['programs']), 15)
        response = self.client.post('/api/search', json={'question': 'computer science'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['rows']), 3)
        self.assertTrue(response.json['demo'])

    def test_api_errors_are_json(self):
        for body in [[], {}, {'question': 12}, {'question': ' '}, {'question': 'x' * 12001}]:
            response = self.client.post('/api/search', json=body)
            self.assertEqual(response.status_code, 400)
            self.assertIn('error', response.json)
        response = self.client.post('/api/search', data='{', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post('/api/search', data='{}').status_code, 415)
        self.assertEqual(self.client.post('/api/search', data='x' * 65537, content_type='application/json').status_code, 413)
        self.assertEqual(self.client.get('/api/missing').status_code, 404)


if __name__ == '__main__':
    unittest.main()
