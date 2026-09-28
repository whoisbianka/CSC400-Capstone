import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

from backend.search import load_programs, search
from backend.server import Handler


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


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path, body=None, content_type='application/json'):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        conn.request(method, path, body, {'Content-Type': content_type})
        response = conn.getresponse()
        status, data = response.status, response.read()
        conn.close()
        return status, data

    def test_catalog_and_search(self):
        status, data = self.request('GET', '/api/programs')
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(data)['programs']), 15)
        status, data = self.request('POST', '/api/search', json.dumps({'question': 'computer science'}))
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(data)['rows']), 3)

    def test_invalid_requests(self):
        for body in ('{', '[]', '{}', '{"question": 12}', '{"question":" "}', json.dumps({'question': 'x' * 12001})):
            with self.subTest(body=body[:40]):
                self.assertEqual(self.request('POST', '/api/search', body)[0], 400)
        self.assertEqual(self.request('POST', '/api/search', '{}', 'text/plain')[0], 415)
        self.assertEqual(self.request('POST', '/api/search', 'x' * 65537)[0], 413)
        self.assertEqual(self.request('POST', '/api/missing', '{}')[0], 404)

    def test_public_assets_only(self):
        for path in ('/.git/config', '/backend/server.py', '/assets/../backend/server.py', '/assets/%2e%2e/backend/server.py', '/assets/', '/missing'):
            with self.subTest(path=path):
                self.assertEqual(self.request('GET', path)[0], 404)
        self.assertEqual(self.request('GET', '/')[0], 200)
        self.assertIn(b'true', self.request('GET', '/assets/js/backend-config.js')[1])
        self.assertEqual(self.request('GET', '/api/health')[0], 200)


if __name__ == '__main__':
    unittest.main()
