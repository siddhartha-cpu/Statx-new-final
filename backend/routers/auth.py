import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response
from pymongo.errors import DuplicateKeyError

from lib.db import db
from lib.security import SESSION_COOKIE, create_session_token, hash_password, session_cookie_kwargs, user_id_from_request, verify_password
from models import LoginRequest, RegisterRequest, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


def _public(doc: dict) -> UserPublic:
    return UserPublic(id=doc["id"], email=doc["email"], display_name=doc["display_name"], created_at=doc["created_at"], setup_complete=doc.get("setup_complete", False))


def _set_session(response: Response, user_id: str) -> None:
    response.set_cookie(SESSION_COOKIE, create_session_token(user_id), **session_cookie_kwargs())


@router.post("/register", response_model=UserPublic)
async def register(payload: RegisterRequest, response: Response):
    email = str(payload.email).lower().strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    now = datetime.now(timezone.utc)
    doc = {"id": str(uuid.uuid4()), "email": email, "display_name": payload.display_name.strip(), "password_hash": hash_password(payload.password), "created_at": now, "setup_complete": False}
    try:
        await db.users.insert_one(doc)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="An account with that email already exists") from exc
    _set_session(response, doc["id"])
    return _public(doc)


@router.post("/login", response_model=UserPublic)
async def login(payload: LoginRequest, response: Response):
    doc = await db.users.find_one({"email": str(payload.email).lower().strip()})
    if not doc or not verify_password(payload.password, doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    _set_session(response, doc["id"])
    return _public(doc)


@router.get("/me", response_model=UserPublic)
async def me(request: Request):
    user_id = user_id_from_request(request)
    doc = await db.users.find_one({"id": user_id})
    if not doc:
        raise HTTPException(status_code=401, detail="Your session has expired")
    return _public(doc)


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
