"""Account-owned major favorites, independent of the legacy users schema."""
from functools import wraps
import os

from flask import abort, current_app, g, jsonify, render_template, request
from sqlalchemy import inspect, text

from .routes import web, database_errors


def require_account(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        token = request.headers.get('Authorization', '').removeprefix('Bearer ')
        if not token or not request.headers.get('Authorization', '').startswith('Bearer '):
            abort(401, description='Sign in or create an account to save majors.')
        import jwt
        issuer = os.environ.get('CLERK_ISSUER', 'https://supreme-grub-6049.clerk.accounts.dev').rstrip('/')
        client = current_app.extensions.setdefault('clerk_jwks', jwt.PyJWKClient(issuer + '/.well-known/jwks.json', timeout=10))
        try:
            key = client.get_signing_key_from_jwt(token).key
            claims = jwt.decode(token, key, algorithms=['RS256'], issuer=issuer,
                                options={'require': ['exp', 'iat', 'nbf', 'sub', 'iss'], 'verify_aud': False})
        except jwt.PyJWKClientConnectionError:
            abort(503, description='Sign-in verification is unavailable. Try again shortly.')
        except jwt.PyJWTError:
            abort(401, description='Please sign in again.')
        allowed = os.environ.get('CLERK_AUTHORIZED_PARTIES', request.host_url.rstrip('/')).split(',')
        if claims.get('azp') not in [value.strip() for value in allowed] or not claims['sub'].startswith('user_'):
            abort(401, description='Please sign in again.')
        g.clerk_user_id = claims['sub']
        return function(*args, **kwargs)
    return wrapped


def favorites_engine():
    import db_functions
    if 'favorites_storage' not in current_app.extensions:
        catalog = inspect(db_functions.engine)
        # Keep compatibility with installations already using standalone saves.
        if catalog.has_table('saved_majors'):
            storage = 'saved_majors'
        elif (catalog.has_table('users') and catalog.has_table('major_fav')
              and 'clerk_user_id' in {column['name'] for column in catalog.get_columns('users')}):
            # The original application maps a verified Clerk identity to an
            # integer users.id and stores its selections in major_fav.
            storage = 'major_fav'
        else:
            current_app.logger.error('No compatible saved-major storage exists in the configured database.')
            abort(503, description='Saving majors is not configured. Please contact the site administrator.')
        current_app.extensions['favorites_storage'] = storage
    return db_functions.engine


@web.get('/saved-majors')
def saved_majors_page():
    return render_template('saved_majors.html', title='Saved majors')


@web.get('/api/saved-majors')
@require_account
@database_errors
def saved_majors_api():
    with favorites_engine().connect() as connection:
        if current_app.extensions.get('favorites_storage') == 'major_fav':
            query = '''SELECT m.cipcode, m.cipdesc AS name
                FROM major_fav f JOIN users u ON u.id = f.user_id
                JOIN majors m ON m.cipcode = f.cipcode
                WHERE u.clerk_user_id = :user_id ORDER BY m.cipdesc, m.cipcode'''
        else:
            query = '''SELECT m.cipcode, m.cipdesc AS name
                FROM saved_majors f JOIN majors m ON m.cipcode = f.cipcode
                WHERE f.clerk_user_id = :user_id ORDER BY f.created_at DESC, m.cipcode'''
        rows = connection.execute(text(query), {'user_id': g.clerk_user_id}).mappings()
        return jsonify(majors=[dict(row) for row in rows])


@web.post('/api/saved-majors/<int:cipcode>')
@require_account
@database_errors
def save_major_api(cipcode):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or type(body.get('saved')) is not bool:
        abort(400, description='Choose whether to save or remove this major.')
    if not 0 < cipcode <= 2147483647:
        abort(404, description='Major not found.')
    with favorites_engine().begin() as connection:
        if not connection.execute(text('SELECT 1 FROM majors WHERE cipcode = :cipcode'), {'cipcode': cipcode}).scalar():
            abort(404, description='Major not found.')
        params = {'user_id': g.clerk_user_id, 'cipcode': cipcode}
        if current_app.extensions.get('favorites_storage') == 'major_fav':
            if body['saved']:
                connection.execute(text('''INSERT INTO users (clerk_user_id)
                    VALUES (:user_id) ON CONFLICT (clerk_user_id) DO NOTHING'''), params)
                connection.execute(text('''INSERT INTO major_fav (user_id, cipcode)
                    SELECT id, :cipcode FROM users WHERE clerk_user_id = :user_id
                    ON CONFLICT (user_id, cipcode) DO NOTHING'''), params)
            else:
                connection.execute(text('''DELETE FROM major_fav WHERE cipcode = :cipcode
                    AND user_id IN (SELECT id FROM users WHERE clerk_user_id = :user_id)'''), params)
        elif body['saved']:
            connection.execute(text('''INSERT INTO saved_majors (clerk_user_id, cipcode)
                VALUES (:user_id, :cipcode) ON CONFLICT DO NOTHING'''), params)
        else:
            connection.execute(text('''DELETE FROM saved_majors
                WHERE clerk_user_id = :user_id AND cipcode = :cipcode'''), params)
    return jsonify(saved=body['saved'])


@web.get('/api/account')
@require_account
def account_api():
    # Only the server-verified Clerk subject establishes account identity.
    return jsonify(clerk_user_id=g.clerk_user_id, provider='Clerk', verified=True)


from . import saved_comparison  # Register after the shared account verifier.
