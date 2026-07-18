# retrieval-api + rag-pipeline (ingest) as one container for Hugging Face Spaces.
# Build context = this staging dir, which contains retrieval-api/ and rag-pipeline/.
FROM python:3.12-slim

# poppler-utils provides `pdftotext`, used by rag-pipeline/parse.py for PDF text.
RUN apt-get update && apt-get install -y --no-install-recommends \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces runs the container as uid 1000 — create that user so runtime caches
# (model downloads) land in a writable home.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1

WORKDIR /home/user/app

# CPU-only torch (no CUDA) — smaller and matches HF Spaces free (CPU).
RUN pip install --no-cache-dir --user torch --index-url https://download.pytorch.org/whl/cpu

# Union of retrieval-api + rag-pipeline runtime deps (+ python-multipart for uploads).
RUN pip install --no-cache-dir --user \
        fastapi "uvicorn[standard]" "psycopg[binary]" pgvector pydantic-settings \
        sentence-transformers anthropic python-multipart python-docx

# App code. rag-pipeline modules are imported by retrieval-api's ingest endpoint.
COPY --chown=user retrieval-api/ /home/user/app/retrieval-api/
COPY --chown=user rag-pipeline/  /home/user/app/rag-pipeline/

ENV RAG_PIPELINE_DIR=/home/user/app/rag-pipeline

# Pre-download the embedding model so the first request isn't a ~2GB cold start.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-large')"

WORKDIR /home/user/app/retrieval-api
EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
