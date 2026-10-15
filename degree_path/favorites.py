"""Account-owned major favorites, independent of the legacy users schema."""
from functools import wraps
import os

from flask import abort, current_app, g, jsonify, render_template, request
from sqlalchemy import text

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
    # Additive setup: does not drop or alter existing catalog/account tables.
    if not current_app.extensions.get('saved_majors_ready'):
        with db_functions.engine.begin() as connection:
            connection.execute(text('''CREATE TABLE IF NOT EXISTS saved_majors (
                clerk_user_id TEXT NOT NULL,
                cipcode INTEGER NOT NULL REFERENCES majors(cipcode),
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (clerk_user_id, cipcode)
            )'''))
        current_app.extensions['saved_majors_ready'] = True
    return db_functions.engine


@web.get('/saved-majors')
def saved_majors_page():
    return render_template('saved_majors.html', title='Saved majors')


@web.get('/api/saved-majors')
@require_account
@database_errors
def saved_majors_api():
    with favorites_engine().connect() as connection:
        rows = connection.execute(text('''SELECT m.cipcode, m.cipdesc AS name
            FROM saved_majors f JOIN majors m ON m.cipcode = f.cipcode
            WHERE f.clerk_user_id = :user_id ORDER BY f.created_at DESC, m.cipcode'''),
            {'user_id': g.clerk_user_id}).mappings()
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
        if body['saved']:
            connection.execute(text('''INSERT INTO saved_majors (clerk_user_id, cipcode)
                VALUES (:user_id, :cipcode) ON CONFLICT DO NOTHING'''), params)
        else:
            connection.execute(text('''DELETE FROM saved_majors
                WHERE clerk_user_id = :user_id AND cipcode = :cipcode'''), params)
    return jsonify(saved=body['saved'])
