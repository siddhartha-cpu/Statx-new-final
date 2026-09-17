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
    file_name: str | None = None
    file_type: str | None = None
    file_size: int | None = None


class CreateModuleItemRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)


class DocumentActionRequest(BaseModel):
    action: Literal["summary", "notes", "flashcards", "mcqs", "descriptive", "assignment", "ask"]
    prompt: str = Field(default="", max_length=4000)
    marks: Literal[2, 5, 10] | None = None


class DocumentAnalysis(BaseModel):
    id: str
    document_id: str
    action: str
    content: str
    created_at: datetime
    prompt: str | None = None
    marks: int | None = None


class ExamResultRequest(BaseModel):
    analysis_id: str
    correct: int = Field(ge=0)
    total: int = Field(ge=1)


class ExamResult(BaseModel):
    id: str
    document_id: str
    document_title: str
    analysis_id: str
    kind: str
    correct: int
    total: int
    percentage: int
    submitted_at: datetime
    feedback: str | None = None
