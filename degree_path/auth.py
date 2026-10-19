import httpx

from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from flask import abort, current_app, request

import db_functions


def get_current_user():
    authorization = request.headers.get("Authorization")

    # This API uses explicit bearer tokens.
    # No Authorization header means a guest request.
    if authorization is None:
        return None

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

    return db_functions.create_or_update_user(clerk_user_id)