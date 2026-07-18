from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DocumentChunk(BaseModel):
    id: str
    position: int
    page: int | None
    section: str | None
    text: str
    # NOTE: no `embedding` — this endpoint is plain-fetch, vectors never leave the DB.


class FullDocumentResponse(BaseModel):
    document_id: str
    filename: str
    doc_type: str
    page_count: int | None
    status: str
    chunk_count: int
    chunks: list[DocumentChunk]


class DocumentStatusResponse(BaseModel):
    document_id: str
    filename: str
    doc_type: str
    status: str  # pending | parsing | embedding | ready | failed
    page_count: int | None
    chunk_count: int


class DocumentOwnerResponse(BaseModel):
    document_id: str
    user_id: str | None  # NULL for pre-Slice-18 documents; the BFF treats null as "deny"


class UserUpsertRequest(BaseModel):
    github_id: int
    username: str
    name: str | None = None
    avatar_url: str | None = None


class UserResponse(BaseModel):
    id: str
    github_id: int
    username: str
    name: str | None
    avatar_url: str | None


class DocumentListItem(BaseModel):
    document_id: str
    filename: str
    doc_type: str
    status: str
    page_count: int | None
    chunk_count: int
    size_bytes: int | None
    uploaded_at: str  # ISO 8601


class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem]


class PrepPackResponse(BaseModel):
    document_id: str
    filename: str
    summary: Any | None = None    # cached LLM output; None until computed
    terms: Any | None = None
    questions: Any | None = None


class PrepPackUpsertRequest(BaseModel):
    kind: str  # "summary" | "terms" | "questions" (validated in the service)
    value: Any


class ChatMessage(BaseModel):
    id: str
    role: str  # "user" | "assistant"
    parts: Any  # AI-SDK UIMessage parts
    metadata: Any | None = None  # citations/plan for assistant messages


class ChatMessagesResponse(BaseModel):
    messages: list[ChatMessage]


class ChatMessageAppendRequest(BaseModel):
    id: str
    role: str
    parts: Any
    metadata: Any | None = None


class RetrieveRequest(BaseModel):
    question: str
    document_id: UUID  # Q&A is always scoped to one document
    top_k: int | None = None
    history: list[dict[str, str]] | None = None


class RetrieveChunk(BaseModel):
    id: str
    position: int
    page: int | None
    section: str | None
    text: str
    score: float  # cosine similarity (1 = identical)


class RetrieveResponse(BaseModel):
    chunks: list[RetrieveChunk]
    reformulated_query: str
