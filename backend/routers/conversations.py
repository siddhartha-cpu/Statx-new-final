import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from lib.db import db
from lib.providers import ProviderError, route_with_fallback
from lib.search import SearchError, search_web, should_search
from lib.security import user_id_from_request
from models import ChatRequest, ChatResponse, Citation, ConversationDetail, ConversationSummary, CreateConversationRequest, Message

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _dt(value):
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(request: Request):
    user_id = user_id_from_request(request)
    docs = await db.conversations.find({"user_id": user_id}).sort("updated_at", -1).to_list(100)
    return [ConversationSummary(id=x["id"], title=x["title"], updated_at=_dt(x["updated_at"]), message_count=x.get("message_count", 0), provider_id=x.get("provider_id")) for x in docs]


@router.post("", response_model=ConversationSummary)
async def create_conversation(payload: CreateConversationRequest, request: Request):
    user_id = user_id_from_request(request)
    now = datetime.now(timezone.utc)
    doc = {"id": str(uuid.uuid4()), "user_id": user_id, "title": payload.title, "created_at": now, "updated_at": now, "message_count": 0, "provider_id": None}
    await db.conversations.insert_one(doc)
    return ConversationSummary(id=doc["id"], title=doc["title"], updated_at=now, message_count=0, provider_id=None)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str, request: Request):
    user_id = user_id_from_request(request)
    conversation = await db.conversations.find_one({"id": conversation_id, "user_id": user_id})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    docs = await db.messages.find({"conversation_id": conversation_id}).sort("created_at", 1).to_list(500)
    messages = [Message(id=x["id"], role=x["role"], content=x["content"], created_at=_dt(x["created_at"]), provider_id=x.get("provider_id"), citations=[Citation(**c) for c in x.get("citations", [])], fallback_notice=x.get("fallback_notice")) for x in docs]
    return ConversationDetail(id=conversation_id, title=conversation["title"], updated_at=_dt(conversation["updated_at"]), message_count=len(messages), provider_id=conversation.get("provider_id"), messages=messages)


@router.post("/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(conversation_id: str, payload: ChatRequest, request: Request):
    user_id = user_id_from_request(request)
    conversation = await db.conversations.find_one({"id": conversation_id, "user_id": user_id})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    now = datetime.now(timezone.utc)
    user_message = {"id": str(uuid.uuid4()), "conversation_id": conversation_id, "role": "user", "content": payload.content, "created_at": now, "citations": []}
    await db.messages.insert_one(user_message)
    previous = await db.messages.find({"conversation_id": conversation_id}).sort("created_at", 1).to_list(100)
    prompt_messages = [{"role": x["role"], "content": x["content"]} for x in previous]
    use_search = payload.search_mode == "web" or (payload.search_mode == "auto" and should_search(payload.content))
    citations: list[Citation] = []
    search_status = "not_used"
    if use_search:
        try:
            results = await search_web(payload.content)
            citations = [Citation(**x) for x in results]
            search_status = "used" if citations else "empty"
            source_context = "\n\nRetrieved web sources (use only these sources for current claims):\n" + "\n".join(f"- {x.title}: {x.url}\n  {x.snippet}" for x in citations)
            prompt_messages[-1]["content"] += source_context
        except SearchError as exc:
            raise HTTPException(status_code=503, detail={"code": "search_unavailable", "message": str(exc)}) from exc
    try:
        result, attempts = await route_with_fallback(user_id, prompt_messages, payload.provider_ids)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail={"code": "providers_unavailable", "message": exc.message}) from exc
    assistant_now = datetime.now(timezone.utc)
    fallback_notice = None
    if len(attempts) > 1:
        fallback_notice = f"{attempts[0].title()} unavailable — switched to {result.provider_id.title()}."
    assistant = {"id": str(uuid.uuid4()), "conversation_id": conversation_id, "role": "assistant", "content": result.text, "created_at": assistant_now, "provider_id": result.provider_id, "citations": [x.model_dump() for x in citations], "fallback_notice": fallback_notice}
    await db.messages.insert_one(assistant)
    title = conversation["title"]
    if title == "New conversation":
        title = payload.content[:48].strip() + ("…" if len(payload.content) > 48 else "")
    await db.conversations.update_one({"id": conversation_id}, {"$set": {"title": title, "updated_at": assistant_now, "message_count": len(previous) + 1, "provider_id": result.provider_id}})
    return ChatResponse(message=Message(id=assistant["id"], role="assistant", content=assistant["content"], created_at=assistant_now, provider_id=result.provider_id, citations=citations, fallback_notice=fallback_notice), search_used=use_search, search_status=search_status, provider_attempts=attempts)
