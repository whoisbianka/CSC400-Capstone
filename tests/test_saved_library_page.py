"""The old favorites URL and both save types share saved_majors.html."""
import ast
from pathlib import Path
import unittest
from flask import Blueprint, Flask, redirect, render_template, request, url_for

ROOT = Path(__file__).resolve().parents[1]


class SavedLibraryPageTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, template_folder=str(ROOT / 'degree_path/templates'),
                         static_folder=str(ROOT / 'degree_path/static'))
        self.app.config.update(TESTING=True, SECRET_KEY='offline-saved-library')
        web = Blueprint('web', __name__)
        source = ast.parse((ROOT / 'degree_path/routes.py').read_text())
        nodes = [n for n in source.body if isinstance(n, ast.FunctionDef) and
                 n.name in ('favorites', 'saved_majors_page')]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), 'routes.py', 'exec'),
             dict(web=web, redirect=redirect, render_template=render_template,
                  request=request, url_for=url_for))
        for endpoint in ('home', 'explore', 'profile', 'settings', 'compare'):
            web.add_url_rule('/' + endpoint, endpoint, lambda: '')
        self.app.register_blueprint(web)
        self.app.context_processor(lambda: dict(csrf_token='offline', clerk_publishable_key=''))
        self.client = self.app.test_client()

    def test_old_page_redirects_instead_of_rendering_standalone_favorites(self):
        self.assertEqual(self.client.get('/favorites').headers['Location'], '/saved-majors')
        response = self.client.get('/favorites?kind=programs')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/saved-majors?view=programs')
        self.assertFalse((ROOT / 'degree_path/templates/favorites.html').exists())

    def test_programs_open_in_shared_saved_majors_template(self):
        with self.client.session_transaction() as state:
            state['user_id'] = 42
        html = self.client.get('/saved-majors?view=programs').get_data(as_text=True)
        self.assertIn('<h1 id="page-title">Saved majors</h1>', html)
        self.assertIn('data-initial-saved-view="programs"', html)
        self.assertIn('id="saved-majors-panel" hidden', html)
        self.assertIn('id="saved-programs-panel"', html)
        self.assertIn('js/saved-programs.js', html)
        self.assertNotIn('js/favorites.js', html)

    def test_guest_has_no_program_library_or_private_data_requests(self):
        html = self.client.get('/saved-majors?view=programs').get_data(as_text=True)
        self.assertIn('data-auth-action="login"', html)
        self.assertNotIn('id="saved-programs-panel"', html)
        self.assertNotIn('js/saved-programs.js', html)


if __name__ == '__main__':
    unittest.main()
