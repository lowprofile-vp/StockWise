"""Supabase Auth.

Passwords live in Supabase. StockWise stores the workspace role and business
on its own users row, matched by the Supabase user id (the JWT sub). Tokens
are verified with the project's public signing keys. The publishable key is
only used to call the project; it does not bypass Row Level Security.
"""

import jwt
from flask import current_app
from jwt import PyJWKClient

from app.errors import APIError

PASSWORD_MARKER = "supabase-managed"
_jwks_clients = {}


def configured():
    return bool(current_app.config.get("SUPABASE_URL") and current_app.config.get("SUPABASE_PUBLISHABLE_KEY"))


def verify_access_token(token):
    if not configured():
        raise APIError("Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY.", 500)
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise APIError("Invalid session. Please log in again.", 401) from exc
    algorithm = header.get("alg")
    if algorithm == "HS256":
        raise APIError(
            "This Supabase project signs tokens with a shared secret. StockWise verifies tokens from the project's public signing keys.",
            401,
        )
    url = f"{current_app.config['SUPABASE_URL']}/auth/v1/.well-known/jwks.json"
    try:
        client = _jwks_clients.get(url)
        if client is None:
            client = PyJWKClient(
                url,
                headers={
                    "apikey": current_app.config["SUPABASE_PUBLISHABLE_KEY"],
                    "Authorization": f"Bearer {current_app.config['SUPABASE_PUBLISHABLE_KEY']}",
                },
            )
            _jwks_clients[url] = client
        key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            key.key,
            algorithms=[algorithm],
            audience="authenticated",
            leeway=10,
        )
    except jwt.ExpiredSignatureError as exc:
        raise APIError("Session expired. Please log in again.", 401) from exc
    except jwt.InvalidTokenError as exc:
        raise APIError("Invalid session. Please log in again.", 401) from exc
    except APIError:
        raise
    except Exception as exc:
        current_app.logger.exception("Supabase token verification failed")
        if exc.__class__.__name__ == "MissingCryptographyError":
            raise APIError("The API cannot verify this Supabase session yet.", 500) from exc
        raise APIError("Could not verify the Supabase session.", 401) from exc
    if not payload.get("sub"):
        raise APIError("Invalid session. Please log in again.", 401)
    return payload
