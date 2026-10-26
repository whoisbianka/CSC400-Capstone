"""Render both comparison flows without starting cloud services."""
import ast
from pathlib import Path
import unittest
from flask import Blueprint, Flask, render_template, request

ROOT = Path(__file__).resolve().parents[1]


class ComparisonPageTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, template_folder=str(ROOT / 'degree_path/templates'))
        self.app.config.update(TESTING=True, SECRET_KEY='offline')
        web = Blueprint('web', __name__)
        tree = ast.parse((ROOT / 'degree_path/routes.py').read_text())
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'compare']
        exec(compile(ast.Module(body=functions, type_ignores=[]), 'routes.py', 'exec'),
             dict(web=web, render_template=render_template, request=request))
        for endpoint in ('home','explore','profile','settings','saved_majors_page','compare_api'):
            web.add_url_rule('/' + endpoint, endpoint, lambda: '')
        self.app.register_blueprint(web)
        self.client = self.app.test_client()

    def test_saved_major_program_comparison_is_reachable(self):
        with self.client.session_transaction() as state:
            state['user_id'] = 42
        response = self.client.get('/compare')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        for marker in ('saved-program-groups','saved-differences','saved-comparison-head',
                       'js/saved-major-comparison.js','js/saved-major-controls.js',
                       '/compare?view=favorites'):
            self.assertIn(marker, html)

    def test_existing_favorite_comparisons_remain_available(self):
        with self.client.session_transaction() as state:
            state['user_id'] = 42
        html = self.client.get('/compare?view=favorites').get_data(as_text=True)
        self.assertIn('data-compare-kind="majors"', html)
        self.assertIn('data-compare-kind="programs"', html)
        self.assertIn('js/compare.js', html)
        self.assertNotIn('js/saved-major-comparison.js', html)

    def test_guest_can_open_the_comparison_account_prompt(self):
        response = self.client.get('/compare')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'data-user-id=""', response.data)
        self.assertIn(b'js/saved-major-controls.js', response.data)


if __name__ == '__main__':
    unittest.main()
