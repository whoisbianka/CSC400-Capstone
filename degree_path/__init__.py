import os
import secrets
from collections import OrderedDict
from flask import Flask, render_template, request, session, abort, jsonify
from werkzeug.exceptions import HTTPException

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        MAX_CONTENT_LENGTH=65536,
    )
    if test_config:
        app.config.update(test_config)

    app.extensions['ui_states'] = OrderedDict()

    @app.before_request
    def protect_forms():
        if request.method == 'POST' and not request.path.startswith('/api/'):
            expected = session.get('csrf', '')
            actual = request.form.get('csrf_token', '')
            if not expected or not secrets.compare_digest(expected.encode(), actual.encode()):
                abort(400, description='This form expired. Reload the page and try again.')

    @app.context_processor
    def template_helpers():
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(24)

        return {
            'csrf_token': session['csrf'],
            'source_note': 'College search is not connected yet.',
            'tuition_label': 'Annual tuition',
        }
    
    @app.template_filter('college_groups')
    def college_groups(programs):
        groups = {}
        for program in programs:
            groups.setdefault(program['college'], []).append(program)
        return groups.items()

    @app.template_filter('money')
    def money(value):
        return f'${value:,.0f}' if value is not None else 'Not available'

    @app.after_request
    def response_headers(response):
        if request.endpoint != 'static':
            response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith('/api/'):
            return jsonify(error=error.description), error.code
        return render_template('error.html', title='Unable to open this page', error=error.description), error.code

    from .routes import web
    app.register_blueprint(web)
    return app
