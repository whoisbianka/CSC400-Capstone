"""Search regression checks against an isolated catalog, without Cloud SQL."""
import importlib
import sys
import unittest
from html.parser import HTMLParser
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import create_engine, text

# Prevent the application module's import-time engine initialization from
# contacting Secret Manager or Cloud SQL during this offline test run.
_original_connector = sys.modules.get('cloud_sql_connection')
sys.modules['cloud_sql_connection'] = SimpleNamespace(
    connect_with_connector=lambda: create_engine('sqlite://'),
    close_connector=lambda: None)
try:
    db = importlib.import_module('db_functions')
    from degree_path import create_app
finally:
    if _original_connector is None:
        sys.modules.pop('cloud_sql_connection', None)
    else:
        sys.modules['cloud_sql_connection'] = _original_connector


class Links(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.anchors = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            attributes = dict(attrs)
            self.links.append(attributes.get('href', ''))
            self.anchors.append(attributes)


class ExploreSearchTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'search-test-only'})
        self.client = self.app.test_client()

    def test_query_combines_with_filters_and_survives_pagination(self):
        data = {'rows': [{'id': 1, 'cipcode': 1107, 'major': 'Computer Science',
                         'college': 'Elmwood', 'city': 'New Haven', 'state': 'CT',
                         'facts': {}}], 'page': 1, 'has_next': True}
        with patch('degree_path.routes.program_page', return_value=data) as search:
            response = self.client.get('/explore', query_string={
                'q': ' Computer Science ', 'state': 'CT', 'degrees': '3', 'cipcode': 1107})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(search.call_args.args[1:4],
                         (1107, (3,), {'q': 'Computer Science', 'state': 'CT'}))
        html = response.get_data(as_text=True)
        self.assertIn('form="degree-filter-form" type="search" name="q"', html)
        self.assertIn('value="Computer Science"', html)
        next_page = next(url for url in Links(html).links
                         if parse_qs(urlsplit(url).query).get('page') == ['2'])
        params = parse_qs(urlsplit(next_page).query)
        for key, value in {'q': 'Computer Science', 'state': 'CT',
                           'degrees': '3', 'cipcode': '1107'}.items():
            self.assertEqual(params[key], [value])

    def test_oversized_search_rejected_before_database_access(self):
        with patch('degree_path.routes.program_page') as search:
            response = self.client.get('/explore', query_string={'q': 'x' * 201})
        self.assertEqual(response.status_code, 400)
        search.assert_not_called()

    def test_blank_query_does_not_add_a_search_filter(self):
        with patch('degree_path.routes.program_page', return_value={
                'rows': [], 'page': 1, 'has_next': False}) as search:
            self.assertEqual(self.client.get('/explore?q=   ').status_code, 200)
        self.assertEqual(search.call_args.args[3], {})

    def test_removing_one_filter_preserves_the_others_and_resets_page(self):
        with patch('degree_path.routes.program_page', return_value={
                'rows': [], 'page': 2, 'has_next': False}):
            response = self.client.get('/explore', query_string={
                'q': 'UConn', 'state': 'CT', 'degrees': '2,3',
                'cipcode': 1107, 'net_price_max': 0, 'page': 2})
        parser = Links(response.get_data(as_text=True))
        chips = {a['aria-label']: a['href'] for a in parser.anchors
                 if a.get('aria-label', '').startswith('Remove ')}
        without_state = parse_qs(urlsplit(chips['Remove State: CT']).query)
        self.assertNotIn('state', without_state)
        self.assertNotIn('page', without_state)
        self.assertEqual(without_state['q'], ['UConn'])
        self.assertEqual(without_state['degrees'], ['2,3'])
        self.assertEqual(without_state['net_price_max'], ['0'])
        self.assertEqual(without_state['cipcode'], ['1107'])
        without_associate = parse_qs(urlsplit(chips['Remove Associate degree']).query)
        self.assertEqual(without_associate['degrees'], ['3'])
        self.assertEqual(without_associate['state'], ['CT'])
        self.assertIn('Remove Cost after aid up to: $0', chips)

    def test_cards_show_college_ownership_and_keep_score_details_collapsed(self):
        data = {'rows': [{'id': 1, 'cipcode': 1107, 'major': 'Computer Science',
                         'college': 'Elmwood', 'city': None, 'state': None,
                         'facts': {'adm_rate': 0.6, 'credlev': 3,
                                   'satmt25': 500, 'satmt75': 650}}],
                'page': 1, 'has_next': False}
        with patch('degree_path.routes.program_page', return_value=data):
            response = self.client.get('/explore')
        html = response.get_data(as_text=True)
        card = html.split('<article class="program-card">', 1)[1].split('</article>', 1)[0]
        self.assertLess(card.index('Elmwood'), card.index('Computer Science'))
        self.assertIn('Program at this college', card)
        self.assertIn('program-college-header', card)
        self.assertIn('Avg. yearly cost after aid', card)
        self.assertIn('Not reported', card)
        self.assertIn('Location not reported', card)
        summary = card.index('<summary>More details</summary>')
        self.assertLess(card.index('Accepted by the college'), summary)
        self.assertGreater(card.index('SAT Math'), summary)
        self.assertIn('View program', card)
        self.assertNotIn('active-filters', html)


class ProgramSearchQueryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        self.addCleanup(self.engine.dispose)
        patcher = patch.object(db, 'engine', self.engine)
        patcher.start()
        self.addCleanup(patcher.stop)
        with self.engine.begin() as c:
            c.execute(text('CREATE TABLE schools (unitid INTEGER PRIMARY KEY, instnm TEXT, city TEXT, stabbr TEXT, insturl TEXT)'))
            c.execute(text("INSERT INTO schools VALUES (1, 'Elmwood Institute', 'New Haven', 'CT', NULL), (2, 'Westbridge', 'Boston', 'MA', NULL), (3, '100% College', 'Boston', 'MA', NULL), (4, 'Under_score College', 'Boston', 'MA', NULL)"))
            c.execute(text('CREATE TABLE majors (cipcode INTEGER PRIMARY KEY, cipdesc TEXT)'))
            c.execute(text("INSERT INTO majors VALUES (1107, 'Computer Science'), (2601, 'Biology')"))
            c.execute(text('CREATE TABLE programs (program_id INTEGER PRIMARY KEY, unitid INTEGER, cipcode INTEGER, credlev INTEGER)'))
            c.execute(text('INSERT INTO programs VALUES (:id, 1, 1107, 3)'), [{'id': i} for i in range(1, 28)])
            c.execute(text('INSERT INTO programs VALUES (28,2,2601,2), (29,3,2601,3), (30,4,2601,3)'))
            c.execute(text("INSERT INTO schools VALUES (5, 'University of Connecticut', 'Storrs', 'CT', NULL), (6, 'University of Connecticut-Stamford', 'Stamford', 'CT', NULL), (7, 'Connecticut College', 'New London', 'CT', NULL), (8, 'Massachusetts Institute of Technology', 'Cambridge', 'MA', NULL)"))
            c.execute(text('INSERT INTO programs VALUES (31,5,2601,3), (32,6,1107,3), (33,7,2601,3), (34,8,1107,3)'))
            c.execute(text('CREATE TABLE cost_info (id INTEGER, unitid INTEGER, npt4 INTEGER, tuitionfee_in INTEGER, tuitionfee_out INTEGER)'))
            c.execute(text('CREATE TABLE program_rank_crit (program_id INTEGER, earn_mdn_4yr_nat INTEGER)'))
            c.execute(text('CREATE TABLE adm_crit (id INTEGER, unitid INTEGER, adm_rate NUMERIC, satmt25 INTEGER, satmt75 INTEGER, satvr25 INTEGER, satvr75 INTEGER, actmt25 INTEGER, actmt75 INTEGER, acten25 INTEGER, acten75 INTEGER)'))

    def search(self, query, page=1, **filters):
        return db.get_page_programs(page=page, filters={'q': query, **filters})

    def test_school_and_major_matches_before_pagination(self):
        first = self.search('ELMWOOD computer')
        second = self.search('ELMWOOD computer', page=2)
        self.assertEqual(len(first['rows']), 25)
        self.assertTrue(first['has_next'])
        self.assertEqual([r['id'] for r in second['rows']], [26, 27])
        self.assertFalse(second['has_next'])
        self.assertEqual([r['id'] for r in self.search('westbridge')['rows']], [28])

    def test_combines_with_degree_and_location(self):
        self.assertEqual([r['id'] for r in self.search('biology', degrees=(2,), state='MA')['rows']], [28])
        self.assertEqual(self.search('biology', state='CT', degrees=(2,))['rows'], [])

    def test_literal_wildcards_and_sql_like_input(self):
        self.assertEqual([r['id'] for r in self.search('%')['rows']], [29])
        self.assertEqual([r['id'] for r in self.search('_')['rows']], [30])
        self.assertEqual(self.search("' OR 1=1 --")['rows'], [])

    def test_database_helper_validates_search_input(self):
        for query in (None, 12, 'x' * 201):
            with self.subTest(query=query), self.assertRaises(ValueError):
                self.search(query)

    def test_nickname_matches_full_school_name_and_campuses(self):
        for query in ('UConn', 'uconn', 'U.Conn.'):
            with self.subTest(query=query):
                self.assertEqual([r['id'] for r in self.search(query)['rows']], [31, 32])
        self.assertEqual([r['id'] for r in self.search('MIT')['rows']], [34])

    def test_nickname_combines_with_major_and_existing_filters(self):
        self.assertEqual([r['id'] for r in self.search('UConn biology')['rows']], [31])
        self.assertEqual([r['id'] for r in self.search('UConn computer', state='CT', degrees=(3,))['rows']], [32])
        self.assertEqual(self.search('UConn', state='MA')['rows'], [])


if __name__ == '__main__':
    unittest.main()
