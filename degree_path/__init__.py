"""Flask application for our db_functions.py database."""
import os
import secrets
import certifi
from pathlib import Path
from flask import Flask, render_template, request, session, abort, jsonify
from flask.cli import load_dotenv
from werkzeug.exceptions import HTTPException
from .services.database_ui import DatabaseUI, DataAccessError # type: ignore



def create_app(test_config=None):    
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    os.environ.setdefault('SSL_CERT_FILE', certifi.where())
    os.environ.setdefault('REQUESTS_CA_BUNDLE', certifi.where())
    private = os.environ.get('PRIVATE_IP', 'false').strip().lower()
    if private not in ('false', 'true'):
        raise ValueError('PRIVATE_IP must be true or false.')
    os.environ['PRIVATE_IP'] = private

    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        MAX_CONTENT_LENGTH=65536,
    )
    if test_config:
        app.config.update(test_config)
    app.extensions['database_ui'] = DatabaseUI()

    @app.before_request
    def protect_forms(): #helping to protect site from CRSF attacks
        if request.method == 'POST':
            expected = session.get('csrf', '')
            actual = request.form.get('X-CRSF_Token', '') if request.is_json else request.form.get('csrf_token', '')
            if not expected or not secrets.compare_digest(expected.encode(), actual.encode()):
                abort(400, description='Reload the page and try again.')

    
    @app.context_processor
    def template_helpers(): # look into this to see if its needed
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(24)
        return {
            'csrf_token': session['csrf'],
            'source_note': 'Database catalog. Confirm current information with the college.',
        }
    
    @app.template_filter('money')
    def money(value):
        return f'${value:,.0f}' if value is not None else 'Not available'

    
    @app.errorhandler(DataAccessError)
    def database_error(error):
        message = 'Database unavailable. Check Google authentication, certificates, connection settings, and schema.'
        if request.path.startswith('/api/'):
            return jsonify(error=message), 503
        return render_template('error.html', title='Database unavailable', error=message), 503
    
    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith('/api/'):
            return jsonify(error=error.description), error.code
        return render_template('error.html', title='Unable to open this page', error=error.description), error.code
    
    @app.after_request
    def response_headers(response):
        if request.endpoint != 'static':
            response.headers['Cache-Control'] = 'no-store' # doesnt store sensitive data 
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    from .routes import web
    app.register_blueprint(web)
    return app
