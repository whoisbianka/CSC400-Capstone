import secrets

from flask import session

import db_functions


def get_or_create_guest_session():
    guest_id = session.get("guest_id")

    if isinstance(guest_id, str):
        guest = db_functions.get_guest_session(guest_id)

        if guest is not None:
            return guest_id, guest

    # Missing or expired session: generate a new identity.
    guest_id = secrets.token_urlsafe(32)
    guest = db_functions.create_guest_session(guest_id)

    session["guest_id"] = guest_id
    session.permanent = True

    return guest_id, guest