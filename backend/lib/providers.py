import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from lib.db import db
from lib.security import decrypt_token, encrypt_token


class ProviderError(Exception):
    def __init__(self, provider_id: str, message: str, retryable: bool = True, cooldown_seconds: int = 60):
        super().__init__(message)
        self.provider_id = provider_id
        self.message = message
        self.retryable = retryable
        self.cooldown_seconds = cooldown_seconds


@dataclass
class ProviderResult:
    provider_id: str
    text: str


PROVIDERS: dict[str, dict[str, str]] = {
    "gemini": {"name": "Gemini", "method": "Google OAuth", "color": "#4285F4"},
    "openai": {"name": "OpenAI", "method": "Server API key", "color": "#10A37F"},
    "anthropic": {"name": "Anthropic", "method": "Server API key", "color": "#D97757"},
    "groq": {"name": "Groq", "method": "Server API key", "color": "#F59E0B"},
}


def _has_env(provider_id: str) -> bool:
    return {
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "groq": bool(os.environ.get("GROQ_API_KEY")),
        "gemini": bool(os.environ.get("GEMINI_API_KEY")),
    }.get(provider_id, False)


async def _connection(user_id: str, provider_id: str) -> dict[str, Any] | None:
    return await db.provider_connections.find_one({"user_id": user_id, "provider_id": provider_id})


async def is_configured(user_id: str, provider_id: str) -> bool:
    if _has_env(provider_id):
        return True
    return await _connection(user_id, provider_id) is not None


async def provider_statuses(user_id: str, selected: list[str]) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    health = {x["provider_id"]: x async for x in db.provider_health.find({"user_id": user_id})}
    rows: list[dict[str, Any]] = []
    for priority, provider_id in enumerate(["gemini", "openai", "anthropic", "groq"]):
        meta = PROVIDERS[provider_id]
        configured = await is_configured(user_id, provider_id)
        health_row = health.get(provider_id, {})
        cooldown = health_row.get("cooldown_until")
        if cooldown and cooldown.tzinfo is None:
            cooldown = cooldown.replace(tzinfo=timezone.utc)
        if cooldown and cooldown <= now:
            cooldown = None
        status = "connected" if configured else "unavailable"
        detail = "Ready for routing" if configured else "Add the server credential or connect OAuth"
        if cooldown:
            status, detail = "cooling_down", "Temporarily paused after a provider error"
        rows.append({
            "id": provider_id,
            "name": meta["name"],
            "method": meta["method"],
            "status": status,
            "configured": configured,
            "selected": provider_id in selected,
            "fallback_enabled": True,
            "priority": priority,
            "cooldown_until": cooldown,
            "detail": detail,
        })
    if os.environ.get("DEMO_MODE", "false").lower() == "true" and not any(x["configured"] for x in rows):
        rows.append({"id": "demo", "name": "Statx Demo", "method": "Local mock", "status": "connected", "configured": True, "selected": True, "fallback_enabled": True, "priority": 99, "cooldown_until": None, "detail": "Demo mode only — configure a real provider for production"})
    return rows


async def mark_provider_failure(user_id: str, provider_id: str, cooldown_seconds: int) -> None:
    now = datetime.now(timezone.utc)
    await db.provider_health.update_one(
        {"user_id": user_id, "provider_id": provider_id},
        {"$set": {"user_id": user_id, "provider_id": provider_id, "cooldown_until": now + timedelta(seconds=cooldown_seconds), "last_error_at": now}},
        upsert=True,
    )


async def mark_provider_success(user_id: str, provider_id: str) -> None:
    await db.provider_health.update_one({"user_id": user_id, "provider_id": provider_id}, {"$set": {"cooldown_until": None, "last_success_at": datetime.now(timezone.utc)}}, upsert=True)


def _history_prompt(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    return [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] in {"user", "assistant"}]


async def _call_openai_compatible(provider_id: str, messages: list[dict[str, str]], api_key: str, endpoint: str, model: str) -> str:
    payload = {"model": model, "messages": _history_prompt(messages), "temperature": 0.2}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(endpoint, json=payload, headers=headers)
    if response.status_code >= 400:
        retryable = response.status_code in {408, 409, 429, 500, 502, 503, 504}
        raise ProviderError(provider_id, f"{provider_id} returned {response.status_code}", retryable=retryable, cooldown_seconds=120 if response.status_code == 429 else 60)
    try:
        return str(response.json()["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ProviderError(provider_id, "Provider returned an unreadable response", cooldown_seconds=30) from exc


async def _call_anthropic(messages: list[dict[str, str]], api_key: str) -> str:
    payload = {"model": os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"), "max_tokens": 1200, "messages": _history_prompt(messages)}
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
    if response.status_code >= 400:
        raise ProviderError("anthropic", f"anthropic returned {response.status_code}", cooldown_seconds=120 if response.status_code == 429 else 60)
    try:
        return str(response.json()["content"][0]["text"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ProviderError("anthropic", "Provider returned an unreadable response", cooldown_seconds=30) from exc


async def _gemini_access_token(user_id: str, connection: dict[str, Any]) -> str:
    access_token = decrypt_token(connection["access_token"])
    expires_at = connection.get("expires_at")
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at > datetime.now(timezone.utc) + timedelta(seconds=60):
        return access_token
    refresh_token = connection.get("refresh_token")
    if not refresh_token:
        raise ProviderError("gemini", "Gemini authorization expired; reconnect Gemini", retryable=False, cooldown_seconds=30)
    try:
        refresh_value = decrypt_token(refresh_token)
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post("https://oauth2.googleapis.com/token", data={"client_id": os.environ.get("GOOGLE_CLIENT_ID", ""), "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""), "refresh_token": refresh_value, "grant_type": "refresh_token"})
        if response.status_code >= 400:
            raise ProviderError("gemini", "Gemini authorization refresh failed; reconnect Gemini", retryable=False, cooldown_seconds=60)
        token = response.json()
        access_token = token["access_token"]
        await db.provider_connections.update_one({"user_id": user_id, "provider_id": "gemini"}, {"$set": {"access_token": encrypt_token(access_token), "expires_at": datetime.now(timezone.utc) + timedelta(seconds=int(token.get("expires_in", 3600))), "updated_at": datetime.now(timezone.utc)}})
        return access_token
    except (KeyError, TypeError, ValueError, httpx.HTTPError) as exc:
        raise ProviderError("gemini", "Gemini authorization refresh failed; reconnect Gemini", retryable=False, cooldown_seconds=60) from exc


async def _call_gemini(user_id: str, messages: list[dict[str, str]]) -> str:
    token = os.environ.get("GEMINI_API_KEY")
    headers: dict[str, str] = {"content-type": "application/json"}
    if token:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')}:generateContent?key={token}"
    else:
        connection = await _connection(user_id, "gemini")
        if not connection:
            raise ProviderError("gemini", "Gemini is not connected", retryable=False, cooldown_seconds=30)
        headers["Authorization"] = f"Bearer {await _gemini_access_token(user_id, connection)}"
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')}:generateContent"
    prompt = "\n\n".join(f"{m['role'].title()}: {m['content']}" for m in messages)
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(endpoint, json={"contents": [{"role": "user", "parts": [{"text": prompt}]}]}, headers=headers)
    if response.status_code >= 400:
        raise ProviderError("gemini", f"gemini returned {response.status_code}", cooldown_seconds=120 if response.status_code == 429 else 60)
    try:
        return str(response.json()["candidates"][0]["content"]["parts"][0]["text"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ProviderError("gemini", "Provider returned an unreadable response", cooldown_seconds=30) from exc


async def call_provider(user_id: str, provider_id: str, messages: list[dict[str, str]]) -> ProviderResult:
    if provider_id == "demo":
        question = messages[-1]["content"]
        return ProviderResult(provider_id, f"Demo response from Statx AI. I received: {question}\n\nConfigure OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY, or Gemini OAuth for live provider responses.")
    if provider_id == "openai" and os.environ.get("OPENAI_API_KEY"):
        text = await _call_openai_compatible("openai", messages, os.environ["OPENAI_API_KEY"], "https://api.openai.com/v1/chat/completions", os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    elif provider_id == "groq" and os.environ.get("GROQ_API_KEY"):
        text = await _call_openai_compatible("groq", messages, os.environ["GROQ_API_KEY"], "https://api.groq.com/openai/v1/chat/completions", os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"))
    elif provider_id == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
        text = await _call_anthropic(messages, os.environ["ANTHROPIC_API_KEY"])
    elif provider_id == "gemini":
        text = await _call_gemini(user_id, messages)
    else:
        raise ProviderError(provider_id, "Provider is not configured", retryable=False, cooldown_seconds=30)
    return ProviderResult(provider_id, text)


async def route_with_fallback(user_id: str, messages: list[dict[str, str]], requested: list[str]) -> tuple[ProviderResult, list[str]]:
    preferences = await db.provider_preferences.find_one({"user_id": user_id})
    selected = requested or (preferences or {}).get("provider_ids", [])
    statuses = await provider_statuses(user_id, selected)
    by_id = {x["id"]: x for x in statuses}
    candidates = [x["id"] for x in statuses if x["id"] in selected and x["configured"]]
    if not candidates:
        candidates = [x["id"] for x in statuses if x["configured"]]
    attempts: list[str] = []
    last_error: ProviderError | None = None
    for provider_id in candidates:
        status = by_id[provider_id]
        if status.get("status") == "cooling_down":
            continue
        attempts.append(provider_id)
        try:
            result = await call_provider(user_id, provider_id, messages)
            await mark_provider_success(user_id, provider_id)
            return result, attempts
        except ProviderError as exc:
            last_error = exc
            await mark_provider_failure(user_id, provider_id, exc.cooldown_seconds)
            if not exc.retryable:
                continue
    if last_error:
        raise ProviderError("router", "All eligible AI providers are currently unavailable", retryable=False, cooldown_seconds=30) from last_error
    raise ProviderError("router", "Connect or configure at least one AI provider before chatting", retryable=False, cooldown_seconds=30)