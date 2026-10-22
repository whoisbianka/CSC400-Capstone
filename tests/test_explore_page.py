"""Exercise production Explore routing, templates, and search SQL without cloud services."""
import ast
from html.parser import HTMLParser
from pathlib import Path
import re
import secrets
from time import perf_counter
import unittest
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

from flask import Flask, Blueprint, abort, current_app, redirect, render_template, request, session, url_for
from sqlalchemy import create_engine, text, bindparam

ROOT = Path(__file__).resolve().parents[1]


def load_functions(path, names, namespace, assignments=()):
    source = ast.parse(path.read_text())
    nodes = [n for n in source.body if
             isinstance(n, ast.FunctionDef) and n.name in names or
             isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in assignments for t in n.targets)]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)


class Links(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.append(dict(attrs).get('href', ''))


class ExplorePageTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, template_folder=str(ROOT / 'degree_path/templates'),
                         static_folder=str(ROOT / 'degree_path/static'))
        self.app.config.update(TESTING=True, SECRET_KEY='offline-explore-test')
        self.page = Mock(return_value={'rows': [{
            'id': 1, 'cipcode': 1107, 'college': 'Aaniiih Nakoda College',
            'major': 'Computer Science', 'city': 'Harlem', 'state': 'MT',
            'facts': {'credlev': 2, 'npt4': 7887, 'adm_rate': None,
                      'tuitionfee_in': 3000, 'website': 'https://example.edu'},
        }], 'page': 1, 'has_next': True})
        database = Mock()
        database.get_major_favorites.return_value = []
        web = Blueprint('web', __name__)
        ns = dict(web=web, abort=abort, current_app=current_app, redirect=redirect,
                  render_template=render_template, request=request, session=session,
                  url_for=url_for, secrets=secrets, db_functions=database,
                  program_page=self.page, explore_major_catalog=Mock(return_value='major catalog'))
        load_functions(ROOT / 'degree_path/routes.py', {'explore', 'positive_arg'}, ns)
        for endpoint in ('home', 'profile', 'settings', 'saved_majors_page', 'favorites'):
            web.add_url_rule('/' + endpoint, endpoint, lambda: '')
        web.add_url_rule('/programs/<int:program_id>', 'program_details', lambda program_id: '')
        self.app.register_blueprint(web)
        self.app.template_filter('money')(lambda n: f'${n:,.0f}')
        self.app.context_processor(lambda: dict(csrf_token='offline', clerk_publishable_key=''))
        self.client = self.app.test_client()

    def test_reference_card_and_search_render_with_live_routes(self):
        response = self.client.get('/explore?q=UConn&state=CT&degree_form=1&degree=3&sort=earnings_desc')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        for value in ('Search majors or colleges', 'program-card-heading', 'program-summary-facts',
                      'Avg. yearly cost after aid', '$7,887', 'Accepted by the college',
                      'Not reported', 'Program at this college', 'More details', 'Apply filters',
                      'data-save-major="1107"', 'College website'):
            self.assertIn(value, html)
        self.assertEqual(self.page.call_args.args[2], (3,))
        self.assertEqual(self.page.call_args.args[3]['q'], 'UConn')
        self.assertEqual(self.page.call_args.kwargs['sort_option'], 'earnings')
        links = [parse_qs(urlsplit(link).query) for link in Links(html).links]
        self.assertTrue(any(p.get('page') == ['2'] and p.get('q') == ['UConn'] and p.get('degrees') == ['3'] for p in links))
        self.assertTrue(any('q' not in p and p.get('state') == ['CT'] and p.get('sort') == ['earnings_desc'] for p in links))

    def test_search_validation_and_separate_major_catalog(self):
        self.assertEqual(self.client.get('/explore?q=' + 'x' * 201).status_code, 400)
        self.assertEqual(self.client.get('/explore?acceptance_min=80&acceptance_max=20').status_code, 400)
        self.assertEqual(self.client.get('/explore?view=majors').get_data(as_text=True), 'major catalog')
        self.page.assert_not_called()

    def test_existing_major_filter_and_zero_values_survive_pagination(self):
        html = self.client.get('/explore?cipcode=1107&net_price_max=0').get_data(as_text=True)
        self.assertIn('Cost after aid up to: $0', html)
        links = [parse_qs(urlsplit(link).query) for link in Links(html).links]
        self.assertTrue(any(p.get('page') == ['2'] and p.get('cipcode') == ['1107'] and p.get('net_price_max') == ['0'] for p in links))


class ExploreSearchTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        self.addCleanup(self.engine.dispose)
        self.ns = dict(engine=self.engine, text=text, bindparam=bindparam, perf_counter=perf_counter, re=re)
        load_functions(ROOT / 'db_functions.py', {'get_page_programs', 'validate_program_filters'},
                       self.ns, ('SCHOOL_SEARCH_ALIASES',))
        with self.engine.begin() as c:
            for sql in [
                'CREATE TABLE schools (unitid INTEGER, instnm TEXT, city TEXT, stabbr TEXT, insturl TEXT)',
                'CREATE TABLE majors (cipcode INTEGER, cipdesc TEXT)',
                'CREATE TABLE programs (program_id INTEGER, unitid INTEGER, cipcode INTEGER, credlev INTEGER)',
                'CREATE TABLE program_rank_crit (program_id INTEGER, earn_mdn_4yr_nat INTEGER)',
                'CREATE TABLE cost_info (unitid INTEGER, npt4 INTEGER, tuitionfee_in INTEGER, tuitionfee_out INTEGER)',
                'CREATE TABLE adm_crit (unitid INTEGER, adm_rate NUMERIC, ' + ', '.join(k + ' INTEGER' for k in ('satmt25','satmt75','satvr25','satvr75','actmt25','actmt75','acten25','acten75')) + ')',
                "INSERT INTO schools VALUES (1,'University of Connecticut','Storrs','CT',NULL),(2,'Literal %_ College','Boston','MA',NULL)",
                "INSERT INTO majors VALUES (1107,'Computer Science'),(4201,'Psychology')",
                'INSERT INTO programs VALUES (1,1,1107,3),(2,1,4201,3),(3,2,4201,2)',
            ]:
                c.execute(text(sql))

    def search(self, q, **filters):
        return self.ns['get_page_programs'](filters={'q': q, **filters})['rows']

    def test_alias_and_major_search_combine_with_existing_filters(self):
        self.assertEqual([p['id'] for p in self.search('U.Conn. computer', state='CT', degrees=(3,))], [1])
        self.assertEqual([p['id'] for p in self.search('psych', cipcodes=[4201], degrees=(2,))], [3])
        self.assertEqual(self.search('UConn', state='MA'), [])

    def test_wildcards_and_sql_like_input_are_literal(self):
        self.assertEqual([p['id'] for p in self.search('%_')], [3])
        self.assertEqual(self.search("' OR 1=1 --"), [])
        for q in (None, 12, 'x' * 201):
            with self.subTest(q=q), self.assertRaises(ValueError):
                self.search(q)


if __name__ == '__main__':
    unittest.main()
