import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from pymongo.errors import DuplicateKeyError

from lib.db import db
from lib.security import SESSION_COOKIE, create_session_token, hash_password, session_cookie_kwargs, user_id_from_request, verify_password
from models import LoginRequest, RegisterRequest, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])
PROFILE_DIR = Path(os.environ.get("UPLOAD_DIR", "/tmp/statx-uploads")) / "profiles"


def _public(doc: dict) -> UserPublic:
    version = doc.get("profile_version", "0")
    return UserPublic(id=doc["id"], email=doc["email"], display_name=doc["display_name"], created_at=doc["created_at"], setup_complete=doc.get("setup_complete", False), avatar_url=f"/api/auth/profile/avatar?v={version}" if doc.get("avatar_path") else None, banner_url=f"/api/auth/profile/banner?v={version}" if doc.get("banner_path") else None)


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


async def _save_profile_image(user_id: str, kind: str, file: UploadFile) -> tuple[str, str]:
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Use a JPG, PNG, or WebP image")
    folder = PROFILE_DIR / user_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / kind
    size = 0
    with path.open("wb") as target:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > 8 * 1024 * 1024:
                path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="Profile images must be 8 MB or smaller")
            target.write(chunk)
    return str(path), file.content_type


@router.post("/profile/images", response_model=UserPublic)
async def update_profile_images(request: Request, avatar: UploadFile | None = File(None), banner: UploadFile | None = File(None)):
    user_id = user_id_from_request(request)
    updates: dict[str, str] = {}
    if avatar:
        updates["avatar_path"], updates["avatar_type"] = await _save_profile_image(user_id, "avatar", avatar)
    if banner:
        updates["banner_path"], updates["banner_type"] = await _save_profile_image(user_id, "banner", banner)
    if not updates:
        raise HTTPException(status_code=422, detail="Choose a profile or banner image")
    updates["profile_version"] = str(time.time_ns())
    await db.users.update_one({"id": user_id}, {"$set": updates})
    doc = await db.users.find_one({"id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Account not found")
    return _public(doc)


@router.get("/profile/{kind}")
async def profile_image(kind: str, request: Request):
    if kind not in {"avatar", "banner"}:
        raise HTTPException(status_code=404, detail="Image not found")
    user_id = user_id_from_request(request)
    doc = await db.users.find_one({"id": user_id})
    path = Path((doc or {}).get(f"{kind}_path", ""))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, media_type=doc.get(f"{kind}_type", "image/jpeg"), headers={"Cache-Control": "private, max-age=300"})
