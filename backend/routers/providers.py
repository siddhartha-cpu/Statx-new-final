import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from lib.db import db
from lib.providers import OPTIONAL_PROVIDERS, provider_statuses
from lib.security import encrypt_token, user_id_from_request
from models import ProviderPreferences, ProviderStatus, SetupRequest

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=list[ProviderStatus])
async def list_providers(request: Request):
    user_id = user_id_from_request(request)
    prefs = await db.provider_preferences.find_one({"user_id": user_id})
    return await provider_statuses(user_id, (prefs or {}).get("provider_ids", []))


@router.get("/preferences", response_model=ProviderPreferences)
async def get_preferences(request: Request):
    user_id = user_id_from_request(request)
    prefs = await db.provider_preferences.find_one({"user_id": user_id})
    return ProviderPreferences(provider_ids=(prefs or {}).get("provider_ids", []), fallback_enabled=(prefs or {}).get("fallback_enabled", True))


@router.patch("/preferences", response_model=ProviderPreferences)
async def update_preferences(payload: ProviderPreferences, request: Request):
    user_id = user_id_from_request(request)
    values = payload.model_dump()
    values["user_id"] = user_id
    await db.provider_preferences.update_one({"user_id": user_id}, {"$set": values}, upsert=True)
    await db.users.update_one({"id": user_id}, {"$set": {"setup_complete": True}})
    return payload


@router.post("/setup", response_model=ProviderPreferences)
async def finish_setup(payload: SetupRequest, request: Request):
    return await update_preferences(ProviderPreferences(provider_ids=payload.provider_ids, fallback_enabled=True), request)


@router.get("/{provider_id}/connect")
async def connect_provider(provider_id: str, request: Request):
    user_id = user_id_from_request(request)
    if provider_id != "gemini":
        if provider_id not in OPTIONAL_PROVIDERS:
            raise HTTPException(status_code=404, detail="Unknown provider")
        return {"provider_id": provider_id, "authorization_url": None, "message": "This provider uses a server-side API credential configured by the administrator."}
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")
    if not client_id or not redirect_uri:
        raise HTTPException(status_code=503, detail="Gemini OAuth is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_REDIRECT_URI.")
    state = secrets.token_urlsafe(32)
    await db.oauth_states.insert_one({"state": state, "user_id": user_id, "provider_id": "gemini", "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)})
    params = {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code", "scope": "https://www.googleapis.com/auth/generative-language.retriever", "access_type": "offline", "prompt": "consent", "state": state}
    return {"provider_id": "gemini", "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)}


@router.get("/{provider_id}/disconnect", status_code=204)
async def disconnect_provider(provider_id: str, request: Request):
    user_id = user_id_from_request(request)
    await db.provider_connections.delete_one({"user_id": user_id, "provider_id": provider_id})


@router.get("/gemini/callback")
async def gemini_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    frontend = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    if error or not code or not state:
        return RedirectResponse(f"{frontend}/app/providers?oauth=cancelled")
    oauth_state = await db.oauth_states.find_one({"state": state})
    state_expiry = oauth_state.get("expires_at") if oauth_state else None
    if state_expiry and state_expiry.tzinfo is None:
        state_expiry = state_expiry.replace(tzinfo=timezone.utc)
    if not oauth_state or not state_expiry or state_expiry < datetime.now(timezone.utc):
        return RedirectResponse(f"{frontend}/app/providers?oauth=invalid")
    client_id, client_secret, redirect_uri = (os.environ.get(x) for x in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI"))
    if not client_id or not client_secret or not redirect_uri:
        return RedirectResponse(f"{frontend}/app/providers?oauth=missing_config")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post("https://oauth2.googleapis.com/token", data={"code": code, "client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect_uri, "grant_type": "authorization_code"})
    if response.status_code >= 400:
        return RedirectResponse(f"{frontend}/app/providers?oauth=failed")
    token = response.json()
    await db.provider_connections.update_one({"user_id": oauth_state["user_id"], "provider_id": "gemini"}, {"$set": {"user_id": oauth_state["user_id"], "provider_id": "gemini", "access_token": encrypt_token(token["access_token"]), "refresh_token": encrypt_token(token["refresh_token"]) if token.get("refresh_token") else None, "expires_at": datetime.now(timezone.utc) + timedelta(seconds=int(token.get("expires_in", 3600))), "updated_at": datetime.now(timezone.utc)}}, upsert=True)
    await db.oauth_states.delete_one({"state": state})
    return RedirectResponse(f"{frontend}/app/providers?oauth=success")
