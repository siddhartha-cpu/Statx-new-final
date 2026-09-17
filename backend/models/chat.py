from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SearchMode = Literal["auto", "web", "ai-only"]


class Citation(BaseModel):
    title: str
    url: str
    domain: str
    snippet: str = ""
    published_at: str | None = None


class ProviderStatus(BaseModel):
    id: str
    name: str
    method: str
    status: str
    configured: bool
    selected: bool = False
    fallback_enabled: bool = True
    priority: int = 0
    cooldown_until: datetime | None = None
    detail: str = ""


class ProviderPreferences(BaseModel):
    provider_ids: list[str] = Field(default_factory=list)
    fallback_enabled: bool = True


class ConversationSummary(BaseModel):
    id: str
    title: str
    updated_at: datetime
    message_count: int = 0
    provider_id: str | None = None


class Message(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime
    provider_id: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    fallback_notice: str | None = None


class ConversationDetail(ConversationSummary):
    messages: list[Message] = Field(default_factory=list)


class CreateConversationRequest(BaseModel):
    title: str = Field(default="New conversation", max_length=120)


class ChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=12000)
    search_mode: SearchMode = "auto"
    provider_ids: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    message: Message
    search_used: bool = False
    search_status: str = "not_used"
    provider_attempts: list[str] = Field(default_factory=list)


class ModuleItem(BaseModel):
    id: str
    kind: str
    title: str
    description: str = ""
    status: str = "active"
    updated_at: datetime


class CreateModuleItemRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
