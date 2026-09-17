import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet
from fastapi import HTTPException, Request


SESSION_COOKIE = "statx_session"


def _secret() -> str:
    return os.environ.get("SESSION_SECRET", "change-me-in-production-statx")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, salt_raw, digest_raw = encoded.split("$", 2)
        salt = base64.urlsafe_b64decode(salt_raw.encode())
        expected = base64.urlsafe_b64decode(digest_raw.encode())
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_session_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(days=14)}
    return jwt.encode(payload, _secret(), algorithm="HS256")


def user_id_from_request(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Please sign in to continue")
    try:
        payload = jwt.decode(token, _secret(), algorithms=["HS256"])
        user_id = payload.get("sub")
        if not isinstance(user_id, str) or not user_id:
            raise ValueError("missing subject")
        return user_id
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Your session has expired") from exc


def token_cipher() -> Fernet:
    raw = os.environ.get("TOKEN_ENCRYPTION_KEY", "")
    if raw:
        try:
            return Fernet(raw.encode())
        except (ValueError, TypeError):
            pass
    derived = base64.urlsafe_b64encode(hashlib.sha256(_secret().encode()).digest())
    return Fernet(derived)


def encrypt_token(value: str) -> str:
    return token_cipher().encrypt(value.encode()).decode()


def decrypt_token(value: str) -> str:
    return token_cipher().decrypt(value.encode()).decode()


def session_cookie_kwargs() -> dict[str, object]:
    production = os.environ.get("APP_ENV", "development") == "production"
    return {"httponly": True, "secure": production, "samesite": "lax", "max_age": 14 * 24 * 3600, "path": "/"}