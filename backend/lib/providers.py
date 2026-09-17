import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from emergentintegrations.llm.chat import LlmChat, StreamDone, TextDelta, UserMessage

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


# These identifiers are internal routing nodes. They are never returned as vendor claims.
OPTIONAL_PROVIDERS: dict[str, dict[str, str]] = {
    "gemini": {"name": "Google Gemini", "method": "Admin OAuth", "color": "#4285F4"},
    "openai": {"name": "OpenAI", "method": "Admin API key", "color": "#10A37F"},
    "anthropic": {"name": "Anthropic", "method": "Admin API key", "color": "#D97757"},
    "groq": {"name": "Groq", "method": "Admin API key", "color": "#F59E0B"},
}
ENGINE_ID = "statx-engine"
ENGINE_NAME = "StatNex AI Engine"


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
    if provider_id == ENGINE_ID:
        return bool(os.environ.get("EMERGENT_LLM_KEY")) or os.environ.get("DEMO_MODE", "false").lower() == "true"
    if _has_env(provider_id):
        return True
    return await _connection(user_id, provider_id) is not None


async def provider_statuses(user_id: str, selected: list[str]) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    health = {x["provider_id"]: x async for x in db.provider_health.find({"user_id": user_id})}
    health_row = health.get(ENGINE_ID, {})
    cooldown = health_row.get("cooldown_until")
    if cooldown and cooldown.tzinfo is None:
        cooldown = cooldown.replace(tzinfo=timezone.utc)
    if cooldown and cooldown <= now:
        cooldown = None
    configured = await is_configured(user_id, ENGINE_ID)
    status = "connected" if configured else "unavailable"
    detail = "Ready for secure routing" if configured else "The authorized backend engine is not configured"
    if cooldown:
        status, detail = "cooling_down", "Temporarily paused after an engine error"
    return [{
        "id": ENGINE_ID,
        "name": ENGINE_NAME,
        "method": "Authorized backend AI",
        "status": status,
        "configured": configured,
        "selected": ENGINE_ID in selected or not selected,
        "fallback_enabled": True,
        "priority": 0,
        "cooldown_until": cooldown,
        "detail": detail,
    }]


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


async def _call_platform_engine(session_id: str, messages: list[dict[str, str]]) -> str:
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise ProviderError(ENGINE_ID, "StatNex AI is temporarily unavailable", retryable=False, cooldown_seconds=30)
    context = "\n\n".join(f"{message['role'].title()}: {message['content']}" for message in _history_prompt(messages))
    system = "You are StatNex AI. Be accurate, useful, and transparent about uncertainty. Do not mention internal providers, keys, or platform infrastructure."
    chat = LlmChat(api_key=key, session_id=f"statx:{session_id}", system_message=system).with_model("openai", os.environ.get("ENGINE_MODEL", "gpt-5.4"))
    chunks: list[str] = []
    try:
        async for event in chat.stream_message(UserMessage(text=context)):
            if isinstance(event, TextDelta):
                chunks.append(event.content)
            elif isinstance(event, StreamDone):
                break
    except Exception as exc:
        raise ProviderError(ENGINE_ID, "StatNex AI is temporarily unavailable", retryable=True, cooldown_seconds=60) from exc
    text = "".join(chunks).strip()
    if not text:
        raise ProviderError(ENGINE_ID, "StatNex AI returned no response", retryable=True, cooldown_seconds=30)
    return text


async def _call_openai_compatible(provider_id: str, messages: list[dict[str, str]], api_key: str, endpoint: str, model: str) -> str:
    payload = {"model": model, "messages": _history_prompt(messages), "temperature": 0.2}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(endpoint, json=payload, headers=headers)
    if response.status_code >= 400:
        retryable = response.status_code in {408, 409, 429, 500, 502, 503, 504}
        raise ProviderError(provider_id, "Optional backend route failed", retryable=retryable, cooldown_seconds=120 if response.status_code == 429 else 60)
    try:
        return str(response.json()["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ProviderError(provider_id, "Optional backend route returned an unreadable response", cooldown_seconds=30) from exc


async def _call_anthropic(messages: list[dict[str, str]], api_key: str) -> str:
    payload = {"model": os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"), "max_tokens": 1200, "messages": _history_prompt(messages)}
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
    if response.status_code >= 400:
        raise ProviderError("anthropic", "Optional backend route failed", cooldown_seconds=120 if response.status_code == 429 else 60)
    try:
        return str(response.json()["content"][0]["text"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ProviderError("anthropic", "Optional backend route returned an unreadable response", cooldown_seconds=30) from exc


async def _gemini_access_token(user_id: str, connection: dict[str, Any]) -> str:
    access_token = decrypt_token(connection["access_token"])
    expires_at = connection.get("expires_at")
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at > datetime.now(timezone.utc) + timedelta(seconds=60):
        return access_token
    refresh_token = connection.get("refresh_token")
    if not refresh_token:
        raise ProviderError("gemini", "Optional Gemini authorization expired", retryable=False, cooldown_seconds=30)
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post("https://oauth2.googleapis.com/token", data={"client_id": os.environ.get("GOOGLE_CLIENT_ID", ""), "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""), "refresh_token": decrypt_token(refresh_token), "grant_type": "refresh_token"})
        if response.status_code >= 400:
            raise ProviderError("gemini", "Optional Gemini authorization refresh failed", retryable=False, cooldown_seconds=60)
        token = response.json()
        access_token = token["access_token"]
        await db.provider_connections.update_one({"user_id": user_id, "provider_id": "gemini"}, {"$set": {"access_token": encrypt_token(access_token), "expires_at": datetime.now(timezone.utc) + timedelta(seconds=int(token.get("expires_in", 3600))), "updated_at": datetime.now(timezone.utc)}})
        return access_token
    except (KeyError, TypeError, ValueError, httpx.HTTPError) as exc:
        raise ProviderError("gemini", "Optional Gemini authorization refresh failed", retryable=False, cooldown_seconds=60) from exc


async def _call_gemini(user_id: str, messages: list[dict[str, str]]) -> str:
    token = os.environ.get("GEMINI_API_KEY")
    headers: dict[str, str] = {"content-type": "application/json"}
    if token:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')}:generateContent?key={token}"
    else:
        connection = await _connection(user_id, "gemini")
        if not connection:
            raise ProviderError("gemini", "Optional Gemini route is not configured", retryable=False, cooldown_seconds=30)
        headers["Authorization"] = f"Bearer {await _gemini_access_token(user_id, connection)}"
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')}:generateContent"
    prompt = "\n\n".join(f"{m['role'].title()}: {m['content']}" for m in messages)
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(endpoint, json={"contents": [{"role": "user", "parts": [{"text": prompt}]}]}, headers=headers)
    if response.status_code >= 400:
        raise ProviderError("gemini", "Optional Gemini route failed", cooldown_seconds=120 if response.status_code == 429 else 60)
    try:
        return str(response.json()["candidates"][0]["content"]["parts"][0]["text"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ProviderError("gemini", "Optional Gemini route returned an unreadable response", cooldown_seconds=30) from exc


async def call_provider(user_id: str, provider_id: str, messages: list[dict[str, str]], session_id: str) -> ProviderResult:
    if provider_id == ENGINE_ID:
        text = await _call_platform_engine(session_id, messages)
    elif provider_id == "openai" and os.environ.get("OPENAI_API_KEY"):
        text = await _call_openai_compatible("openai", messages, os.environ["OPENAI_API_KEY"], "https://api.openai.com/v1/chat/completions", os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    elif provider_id == "groq" and os.environ.get("GROQ_API_KEY"):
        text = await _call_openai_compatible("groq", messages, os.environ["GROQ_API_KEY"], "https://api.groq.com/openai/v1/chat/completions", os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"))
    elif provider_id == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
        text = await _call_anthropic(messages, os.environ["ANTHROPIC_API_KEY"])
    elif provider_id == "gemini":
        text = await _call_gemini(user_id, messages)
    else:
        raise ProviderError(provider_id, "Optional backend route is not configured", retryable=False, cooldown_seconds=30)
    return ProviderResult(provider_id, text)


async def route_with_fallback(user_id: str, messages: list[dict[str, str]], requested: list[str], session_id: str) -> tuple[ProviderResult, list[str]]:
    preferences = await db.provider_preferences.find_one({"user_id": user_id})
    selected = requested or (preferences or {}).get("provider_ids", [])
    fallback_enabled = (preferences or {}).get("fallback_enabled", True)
    internal_order = [ENGINE_ID, "openai", "anthropic", "groq", "gemini"]
    if selected:
        requested_order = [provider for provider in selected if provider in internal_order]
        internal_order = requested_order + [provider for provider in internal_order if provider not in requested_order]
    candidates = [provider for provider in internal_order if await is_configured(user_id, provider)]
    if not fallback_enabled and candidates:
        candidates = candidates[:1]
    health = {x["provider_id"]: x async for x in db.provider_health.find({"user_id": user_id})}
    attempts: list[str] = []
    last_error: ProviderError | None = None
    for provider_id in candidates:
        cooldown = health.get(provider_id, {}).get("cooldown_until")
        if cooldown and cooldown.tzinfo is None:
            cooldown = cooldown.replace(tzinfo=timezone.utc)
        if cooldown and cooldown > datetime.now(timezone.utc):
            continue
        attempts.append(provider_id)
        try:
            result = await call_provider(user_id, provider_id, messages, session_id)
            await mark_provider_success(user_id, provider_id)
            return result, attempts
        except ProviderError as exc:
            last_error = exc
            await mark_provider_failure(user_id, provider_id, exc.cooldown_seconds)
    if last_error:
        raise ProviderError("router", "All eligible AI routes are temporarily unavailable", retryable=False, cooldown_seconds=30) from last_error
    raise ProviderError("router", "StatNex AI is not configured", retryable=False, cooldown_seconds=30)