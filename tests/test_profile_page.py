"""Render the real profile/navigation and session-expiry behavior without cloud services."""
import ast
from html.parser import HTMLParser
from pathlib import Path
import time
import unittest
from flask import Blueprint, Flask, render_template, session

ROOT = Path(__file__).resolve().parents[1]


class ProfileHTML(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.in_nav = False
        self.nav_actions = []
        self.outside_actions = []
        self.feed(html)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == 'nav':
            self.in_nav = True
        if tag == 'button' and attrs.get('data-auth-action') == 'logout':
            (self.nav_actions if self.in_nav else self.outside_actions).append(attrs)

    def handle_endtag(self, tag):
        if tag == 'nav':
            self.in_nav = False


class ProfilePageTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, template_folder=str(ROOT / 'degree_path/templates'),
                         static_folder=str(ROOT / 'degree_path/static'))
        self.app.config.update(TESTING=True, SECRET_KEY='offline-profile')
        web = Blueprint('web', __name__)
        source = ast.parse((ROOT / 'degree_path/routes.py').read_text())
        nodes = [n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'profile']
        exec(compile(ast.Module(body=nodes, type_ignores=[]), 'routes.py', 'exec'),
             dict(web=web, render_template=render_template))
        for endpoint in ('home', 'explore', 'saved_majors_page', 'settings', 'favorites', 'compare'):
            web.add_url_rule('/' + endpoint, endpoint, lambda: '')
        self.app.register_blueprint(web)
        auth = ast.parse((ROOT / 'degree_path/auth.py').read_text())
        expire = [n for n in auth.body if isinstance(n, ast.FunctionDef) and n.name == 'expire_login']
        ns = dict(session=session, time=time)
        exec(compile(ast.Module(body=expire, type_ignores=[]), 'auth.py', 'exec'), ns)
        self.app.before_request(ns['expire_login'])
        self.app.context_processor(lambda: dict(csrf_token='offline', clerk_publishable_key=''))
        self.client = self.app.test_client()

    def sign_in(self, expires=None):
        with self.client.session_transaction() as state:
            state.update(user_id=42, clerk_user_id='user_expected',
                         login_expires_at=expires or time.time() + 3600)

    def test_signed_in_profile_shows_status_and_navbar_only_signout(self):
        self.sign_in()
        response = self.client.get('/profile')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('You’re signed in', html)
        self.assertIn('data-clerk-user-id="user_expected"', html)
        self.assertIn('id="profile-name-value"', html)
        self.assertIn('id="profile-email-value"', html)
        self.assertNotIn('bianka@example.com', html)
        controls = ProfileHTML(html)
        self.assertEqual(len(controls.nav_actions), 1)
        self.assertEqual(controls.outside_actions, [])

    def test_guest_profile_offers_nav_signin_without_private_details(self):
        html = self.client.get('/profile').get_data(as_text=True)
        self.assertIn('You’re signed out', html)
        self.assertIn('data-auth-action="login"', html)
        self.assertNotIn('id="profile-email-value"', html)
        self.assertNotIn('data-auth-action="logout"', html)

    def test_expired_session_returns_guest_profile(self):
        self.sign_in(time.time() - 1)
        html = self.client.get('/profile').get_data(as_text=True)
        self.assertIn('You’re signed out', html)
        self.assertNotIn('user_expected', html)
        self.assertNotIn('data-auth-action="logout"', html)


if __name__ == '__main__':
    unittest.main()
