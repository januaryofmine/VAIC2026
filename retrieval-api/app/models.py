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
