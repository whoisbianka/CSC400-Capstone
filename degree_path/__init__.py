"""Flask application for our db_functions.py database."""
import os
import secrets
import certifi
from pathlib import Path
from flask import Flask, render_template, request, session, abort, jsonify
from flask.cli import load_dotenv
from werkzeug.exceptions import HTTPException
from datetime import timedelta




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
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        MAX_CONTENT_LENGTH=65536,
        # Reload edited HTML templates without restarting the local server.
        TEMPLATES_AUTO_RELOAD=True,
        SESSION_COOKIE_SECURE=(
        os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
        ),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
        SESSION_REFRESH_EACH_REQUEST=False,

        CLERK_SECRET_KEY=os.environ.get("CLERK_SECRET_KEY"),
        CLERK_PUBLISHABLE_KEY=os.environ.get("CLERK_PUBLISHABLE_KEY"),

        CLERK_AUTHORIZED_PARTIES=[
            origin.strip()
            for origin in os.environ.get(
                "CLERK_AUTHORIZED_PARTIES", ""
            ).split(",")
            if origin.strip()
        ],
    )
    if test_config:
        app.config.update(test_config)

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY is required.")

    if not app.config["CLERK_SECRET_KEY"]:
        raise RuntimeError("CLERK_SECRET_KEY is required.")

    if not app.config["CLERK_AUTHORIZED_PARTIES"]:
        raise RuntimeError("CLERK_AUTHORIZED_PARTIES is required.")

    if not app.config["CLERK_PUBLISHABLE_KEY"]:
        raise RuntimeError("CLERK_PUBLISHABLE_KEY is required.")

    from .auth import expire_login
    app.before_request(expire_login)

    @app.before_request
    def protect_forms(): #helping to protect site from CRSF attacks
        if request.method == 'POST':
            expected = session.get('csrf', '')
            actual = request.headers.get('X-CSRF-Token', '') if request.is_json else request.form.get('csrf_token', '')
            if not expected or not secrets.compare_digest(expected.encode(), actual.encode()):
                abort(400, description='Reload the page and try again.')

    
    @app.context_processor
    def template_helpers(): # look into this to see if its needed
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(24)
        return {
            "csrf_token": session["csrf"],
            "clerk_publishable_key": app.config["CLERK_PUBLISHABLE_KEY"],
        }
    
    @app.template_filter('money')
    def money(value):
        return f'${value:,.0f}' if value is not None else 'Not available'

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

    #initialize database connection on initial connection to website
    if not app.config.get("TESTING"):
        import db_functions
        db_functions.warm_database_connections(db_functions.engine,size=5)

    @app.cli.command("cleanup-guests")
    def cleanup_guests():
        import db_functions

        deleted = db_functions.delete_expired_guest_sessions()
        print(f"Deleted {deleted} expired guest sessions.")    

    return app
