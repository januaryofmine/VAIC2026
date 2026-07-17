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
