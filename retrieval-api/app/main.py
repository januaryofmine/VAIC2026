import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers.documents import router as documents_router
from app.routers.ingest import router as ingest_router
from app.routers.retrieve import router as retrieve_router

logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(title="Paperless Meetings — Retrieval API", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(documents_router, prefix="/api")
app.include_router(retrieve_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")


@app.middleware("http")
async def api_key_guard(request: Request, call_next):
    """S1: when api_key is set, gate every /api route except the healthcheck.
    Empty api_key (local dev) leaves everything open."""
    key = settings.api_key
    path = request.url.path
    if key and path.startswith("/api") and path != "/api/healthz":
        if request.headers.get("x-api-key") != key:
            return JSONResponse(
                status_code=401, content={"detail": "invalid or missing API key"}
            )
    return await call_next(request)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.error("Unhandled error: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
