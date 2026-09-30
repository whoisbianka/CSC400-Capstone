"""Flask application factory for the Python-first demo."""
import os
import secrets
from pathlib import Path
import click
from dotenv import dotenv_values
from .database import Database, DatabaseUnavailable
from collections import OrderedDict
from flask import Flask, render_template, request, session, abort, jsonify
from werkzeug.exceptions import HTTPException
from .repositories.programs import DemoProgramRepository


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        MAX_CONTENT_LENGTH=65536,
    )
    # .env values never override explicitly exported environment variables.
    settings = {**dotenv_values(Path(app.root_path).parent / '.env'), **os.environ}
    for key in ('PROGRAM_DATA_SOURCE', 'TUITION_BASIS', 'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASS', 'DB_SSLMODE', 'INSTANCE_CONNECTION_NAME', 'PRIVATE_IP'):
        if settings.get(key) is not None:
            app.config[key] = settings[key]
    app.config.setdefault('PROGRAM_DATA_SOURCE', 'cloudsql')
    app.config.setdefault('TUITION_BASIS', 'in_state')
    if test_config:
        app.config.update(test_config)
    source = app.config['PROGRAM_DATA_SOURCE']
    if source == 'demo':
        if not app.testing:
            raise ValueError('Demo fixtures are available only during automated tests. Use cloudsql or postgres.')
        app.extensions['program_repository'] = DemoProgramRepository()
    elif source in ('postgres', 'cloudsql'):
        from .repositories.postgres import PostgresProgramRepository
        app.extensions['program_repository'] = PostgresProgramRepository(Database(app.config), app.config['TUITION_BASIS'])
    else:
        raise ValueError('PROGRAM_DATA_SOURCE must be demo, postgres, or cloudsql.')

    @app.cli.command('check-database')
    def check_database():
        """Read one joined catalog row; never modifies tables or prints credentials."""
        repo = app.extensions['program_repository']
        if repo.is_demo:
            click.echo('Demo mode: no database connection attempted.')
            return
        from .repositories.postgres import CATALOG_SQL
        try:
            rows = repo.database.select(CATALOG_SQL + ' LIMIT 1')
        except DatabaseUnavailable as error:
            raise click.ClickException(str(error)) from None
        click.echo('Database connected; catalog query succeeded.' + (' Catalog is empty.' if not rows else ''))

    @app.errorhandler(DatabaseUnavailable)
    def database_error(error):
        if request.path.startswith('/api/'):
            return jsonify(error=str(error)), 503
        return render_template('error.html', title='Database connection unavailable', error=str(error)), 503
    app.extensions['demo_states'] = OrderedDict()

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
        repo = app.extensions['program_repository']
        return {'csrf_token': session['csrf'], 'catalog_demo': repo.is_demo, 'source_note': repo.source_note, 'tuition_label': repo.tuition_label}

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
