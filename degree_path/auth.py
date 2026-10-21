import time
import secrets

import httpx

from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from flask import abort, current_app, request, session

import db_functions


def establish_login():
    authorization = request.headers.get("Authorization")

    if authorization is None:
        abort(401, description="A Clerk sign-in token is required.")

    parts = authorization.split()

    if (
        len(parts) != 2
        or parts[0].lower() != "bearer"
        or not parts[1]
    ):
        abort(401, description="Invalid authorization header.")

    clerk_request = httpx.Request(
        method=request.method,
        url=request.url,
        headers={"Authorization": authorization},
    )

    with Clerk(
        bearer_auth=current_app.config["CLERK_SECRET_KEY"]
    ) as clerk:
        auth_state = clerk.authenticate_request(
            clerk_request,
            AuthenticateRequestOptions(
                authorized_parties=current_app.config[
                    "CLERK_AUTHORIZED_PARTIES"
                ],
            ),
        )

    if not auth_state.is_signed_in:
        abort(401, description="Your login expired. Please sign in again.")

    payload = auth_state.payload or {}
    clerk_user_id = payload.get("sub")

    if not isinstance(clerk_user_id, str) or not clerk_user_id.startswith("user_"):
        abort(401, description="Invalid user identity.")

    user = db_functions.create_or_update_user(clerk_user_id)
    session["user_id"] = user["id"]
    session["clerk_user_id"] = clerk_user_id
    session.permanent = True
    lifetime = int(current_app.permanent_session_lifetime.total_seconds())
    session["login_expires_at"] = int(time.time()) + lifetime
    session["csrf"] = secrets.token_urlsafe(24)
    return user


def expire_login():
    """Enforce the fixed login deadline even if other session data changes."""
    if "user_id" in session and session.get("login_expires_at", 0) <= time.time():
        for key in ("user_id", "clerk_user_id", "login_expires_at"):
            session.pop(key, None)


def get_current_user():
    """Read the verified Flask session; no Clerk or database calls."""
    user_id = session.get("user_id")
    expected_user = request.headers.get("X-App-User-ID")
    # A stale tab must not read or write data for a newly signed-in account.
    # This header is only a consistency check, never proof of identity.
    if expected_user is not None and expected_user != str(user_id or ""):
        abort(401, description="Your sign-in changed or expired. Reload the page.")
    if user_id is None:
        return None
    return {"id": user_id, "clerk_user_id": session["clerk_user_id"]}
