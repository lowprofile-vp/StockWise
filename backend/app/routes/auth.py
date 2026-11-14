import hashlib
import secrets
import smtplib
from datetime import timedelta
from email.message import EmailMessage

from flask import Blueprint, current_app, g, jsonify, request
from flask_jwt_extended import get_jwt, verify_jwt_in_request

from app.errors import APIError
from app.extensions import db
from app.models import Business, PasswordResetToken, TokenBlocklist, User, utcnow
from app.services.supabase_auth import verify_access_token
from app.utils.auth import hash_password, issue_token, login_required, uses_supabase, verify_password
from app.utils.parsing import json_body, parse_email, parse_password, clean_text
from app.utils.serialize import user_payload

bp = Blueprint("auth", __name__)


@bp.post("/register")
def register():
    _local_auth_only()
    data = json_body()
    name = clean_text(data.get("name"), "Full name", minimum=2, maximum=120)
    email = parse_email(data.get("email"))
    password = parse_password(data.get("password"))
    if data.get("confirm_password") != password:
        raise APIError("Password and confirmation do not match.")
    role = data.get("role") or "admin"
    if role not in {"admin", "staff"}:
        raise APIError("Role must be admin or staff.")
    if User.query.filter_by(email=email).first():
        raise APIError("An account with this email already exists.", 409)

    if role == "admin":
        business_name = clean_text(data.get("business_name"), "Business name", minimum=2, maximum=150)
        business = Business(
            business_name=business_name,
            business_type="Unspecified",
            currency="INR",
            join_code=_unique_join_code(),
            setup_complete=False,
            restock_budget=0,
        )
        db.session.add(business)
        db.session.flush()
        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role="admin",
            business_id=business.business_id,
        )
        db.session.add(user)
        db.session.flush()
        business.owner_id = user.user_id
    else:
        code = str(data.get("join_code") or "").strip().upper()
        if not code:
            raise APIError("A workspace code from the owner is required for a staff account.")
        business = Business.query.filter_by(join_code=code).first()
        if business is None:
            raise APIError("That workspace code was not found.")
        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role="staff",
            business_id=business.business_id,
        )
        db.session.add(user)
    db.session.commit()
    return jsonify({"access_token": issue_token(user, remember=True), "user": user_payload(user, business)}), 201


@bp.post("/login")
def login():
    _local_auth_only()
    data = json_body()
    email = parse_email(data.get("email"))
    password = data.get("password")
    if not isinstance(password, str) or not password:
        raise APIError("Password is required.")
    user = User.query.filter_by(email=email).first()
    if user is None or not verify_password(user.password_hash, password):
        raise APIError("Email or password is incorrect.", 401)
    if not user.is_active:
        raise APIError("This account is inactive. Ask the workspace owner to restore it.", 403)
    business = db.session.get(Business, user.business_id) if user.business_id else None
    token = issue_token(user, remember=bool(data.get("remember_me")))
    return jsonify({"access_token": token, "user": user_payload(user, business)})


@bp.post("/provision")
def provision():
    if not uses_supabase():
        raise APIError("Supabase auth is not configured.", 404)
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        raise APIError("Login required.", 401)
    payload = verify_access_token(header.split(" ", 1)[1].strip())
    uid = str(payload.get("sub") or "")
    email = parse_email(payload.get("email"))
    user = User.query.filter_by(supabase_uid=uid).first() or User.query.filter_by(email=email).first()
    if user is not None:
        if not user.is_active:
            raise APIError("This account is inactive. Ask the workspace owner to restore it.", 403)
        if not user.supabase_uid:
            user.supabase_uid = uid
            db.session.commit()
        business = db.session.get(Business, user.business_id) if user.business_id else None
        return jsonify({"user": user_payload(user, business)})

    data = json_body()
    metadata = payload.get("user_metadata") if isinstance(payload.get("user_metadata"), dict) else {}
    name = clean_text(data.get("name") or metadata.get("name"), "Full name", minimum=2, maximum=120)
    role = data.get("role") or metadata.get("role") or "admin"
    if role not in {"admin", "staff"}:
        raise APIError("Role must be admin or staff.")
    from app.data.api import provision_profile

    if role == "admin":
        business_name = clean_text(
            data.get("business_name") or metadata.get("business_name"),
            "Business name",
            minimum=2,
            maximum=150,
        )
        user, business = provision_profile(name, "admin", business_name, None)
    else:
        code = str(data.get("join_code") or metadata.get("join_code") or "").strip().upper()
        if not code:
            raise APIError("A workspace code from the owner is required for a staff account.")
        user, business = provision_profile(name, "staff", None, code)
    return jsonify({"user": user_payload(user, business)}), 201


@bp.post("/logout")
def logout():
    if uses_supabase():
        return jsonify({"message": "You have been logged out."})
    verify_jwt_in_request()
    payload = get_jwt()
    db.session.add(
        TokenBlocklist(
            jti=payload["jti"],
            expires_at=utcnow() + timedelta(seconds=max(int(payload["exp"] - utcnow().timestamp()), 60)),
        )
    )
    db.session.commit()
    return jsonify({"message": "You have been logged out."})


@bp.get("/me")
@login_required(allow_incomplete=True)
def me():
    return jsonify({"user": user_payload(g.user, g.business)})


@bp.post("/forgot-password")
def forgot_password():
    _local_auth_only()
    data = json_body()
    email = parse_email(data.get("email"))
    user = User.query.filter_by(email=email).first()
    message = "If an account exists for that email, a reset link has been created."
    body = {"message": message}
    if user and user.is_active:
        PasswordResetToken.query.filter_by(user_id=user.user_id, used=False).update({"used": True})
        raw = secrets.token_urlsafe(32)
        db.session.add(
            PasswordResetToken(
                user_id=user.user_id,
                token_hash=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                expires_at=utcnow() + timedelta(minutes=30),
                used=False,
            )
        )
        db.session.commit()
        reset_url = f"{current_app.config['FRONTEND_URL'].rstrip('/')}/reset-password?token={raw}"
        emailed = _send_reset_email(user.email, reset_url)
        if current_app.config.get("RETURN_RESET_TOKEN") and not emailed:
            body["dev_reset_url"] = reset_url
            body["reset_token"] = raw
    return jsonify(body)


@bp.post("/reset-password")
def reset_password():
    _local_auth_only()
    data = json_body()
    token = str(data.get("token") or "").strip()
    if not token:
        raise APIError("Reset token is required.")
    password = parse_password(data.get("password"))
    if data.get("confirm_password") not in (None, "") and data.get("confirm_password") != password:
        raise APIError("Password and confirmation do not match.")
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    row = PasswordResetToken.query.filter_by(token_hash=digest, used=False).first()
    expires_at = None if row is None else row.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        from datetime import timezone

        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if row is None or expires_at < utcnow():
        raise APIError("This reset link is invalid or has expired.", 400)
    user = db.session.get(User, row.user_id)
    if user is None:
        raise APIError("Account not found.", 404)
    user.password_hash = hash_password(password)
    row.used = True
    db.session.commit()
    return jsonify({"message": "Password updated. You can log in with the new password."})


@bp.put("/password")
@login_required(allow_incomplete=True)
def change_password():
    _local_auth_only()
    data = json_body()
    current = data.get("current_password")
    if not isinstance(current, str) or not verify_password(g.user.password_hash, current):
        raise APIError("Current password is incorrect.", 400)
    password = parse_password(data.get("new_password"))
    if data.get("confirm_password") not in (None, "") and data.get("confirm_password") != password:
        raise APIError("Password and confirmation do not match.")
    g.user.password_hash = hash_password(password)
    db.session.commit()
    return jsonify({"message": "Password updated."})


def _local_auth_only():
    if uses_supabase():
        raise APIError("Passwords are managed by Supabase Auth.", 400)


def _unique_join_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    for _ in range(20):
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        if Business.query.filter_by(join_code=code).first() is None:
            return code
    raise APIError("Could not create a workspace code. Try again.", 500)


def _send_reset_email(recipient, reset_url):
    host = current_app.config.get("SMTP_HOST") or ""
    if not host:
        return False
    message = EmailMessage()
    message["Subject"] = "Reset your StockWise password"
    message["From"] = current_app.config["SMTP_FROM"]
    message["To"] = recipient
    message.set_content(
        "Use this link to choose a new StockWise password. It expires in 30 minutes.\n\n"
        f"{reset_url}\n"
    )
    try:
        with smtplib.SMTP(host, current_app.config["SMTP_PORT"], timeout=10) as smtp:
            smtp.starttls()
            if current_app.config.get("SMTP_USER"):
                smtp.login(current_app.config["SMTP_USER"], current_app.config["SMTP_PASSWORD"])
            smtp.send_message(message)
        return True
    except OSError:
        current_app.logger.exception("Password reset email failed")
        return False
