"""Request authentication helpers."""

from datetime import timedelta
from functools import wraps

from flask import current_app, g, request
from flask_jwt_extended import create_access_token, get_jwt_identity, verify_jwt_in_request
from werkzeug.security import check_password_hash, generate_password_hash

from app.errors import APIError
from app.extensions import db
from app.models import Business, User


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password_hash, password):
    return check_password_hash(password_hash, password)


def issue_token(user, remember=False):
    if remember:
        expires = timedelta(days=current_app.config["REMEMBER_DAYS"])
    else:
        expires = current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    return create_access_token(
        identity=str(user.user_id),
        additional_claims={"role": user.role, "business_id": user.business_id},
        expires_delta=expires,
    )


def uses_supabase():
    if current_app.config.get("TESTING"):
        return False
    return bool(current_app.config.get("SUPABASE_URL") and current_app.config.get("SUPABASE_PUBLISHABLE_KEY"))


def _bearer_token():
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        raise APIError("Login required.", 401)
    token = header.split(" ", 1)[1].strip()
    if not token:
        raise APIError("Login required.", 401)
    return token


def _load_user():
    if uses_supabase():
        from app.services.supabase_auth import verify_access_token

        payload = verify_access_token(_bearer_token())
        uid = str(payload.get("sub") or "")
        email = str(payload.get("email") or "").lower()
        user = User.query.filter_by(supabase_uid=uid).first() if uid else None
        if user is None and email:
            user = User.query.filter_by(email=email).first()
            if user is not None and uid and not user.supabase_uid:
                user.supabase_uid = uid
                db.session.commit()
        if user is None:
            raise APIError(
                "This Supabase account has no StockWise workspace yet.",
                401,
                details={"code": "profile_required"},
            )
        if not user.is_active:
            raise APIError("This account is inactive. Ask the workspace owner to restore it.", 403)
        return user

    verify_jwt_in_request()
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError) as exc:
        raise APIError("Invalid session. Please log in again.", 401) from exc
    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        raise APIError("Account is inactive or missing.", 401)
    return user


def _attach_workspace(user, allow_incomplete):
    if not user.business_id:
        raise APIError("No workspace is attached to this account.", 403)
    business = db.session.get(Business, user.business_id)
    if business is None:
        raise APIError("Workspace not found.", 403)
    if not allow_incomplete and not business.setup_complete:
        raise APIError(
            "Complete business setup first.",
            409,
            details={"code": "setup_required"},
        )
    g.user = user
    g.business = business


def login_required(fn=None, *, allow_incomplete=False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _attach_workspace(_load_user(), allow_incomplete)
            return func(*args, **kwargs)

        return wrapper

    if fn is None:
        return decorator
    return decorator(fn)


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = _load_user()
        _attach_workspace(user, allow_incomplete=False)
        if user.role != "admin":
            raise APIError("Only the workspace owner can do that.", 403)
        return fn(*args, **kwargs)

    return wrapper
