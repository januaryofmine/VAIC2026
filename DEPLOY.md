# Deploy — Live demo (all free, no credit card)

Kiến trúc (sau khi bỏ model tự-host để tránh phí):

```
UI (Nuxt)  ──►  retrieval-api (Vercel Python, torch-free)  ──►  Supabase (pgvector)
 Vercel          embeddings qua API (provider chọn sau)          DB
                 LLM: Anthropic Claude (tóm tắt/hỏi-đáp)
```

- **retrieval-api** không còn nhúng model 5GB → chạy được trên **Vercel Python** (serverless, $0).
- **Embedding provider chọn sau** (`EMBEDDING_PROVIDER`): `gemini` (768d), hoặc HF Inference / Jina / OpenAI…
  Code đã tách provider (`app/services/embed_provider.py`); thêm provider mới = 1 file + 1 nhánh.
- **Reranker (PyTorch)** KHÔNG chạy trên bản cloud (để nhẹ). Vẫn dùng cho bản local/on-prem + bảng eval.

## Trạng thái
- ✅ Supabase project `vaic-paperless` (Tokyo), pgvector + schema đã tạo. `DATABASE_URL` (pooler 5432) đã có.
- ✅ Code cloud (Gemini embedder mẫu, dispatcher, pdfplumber fallback) — provider-agnostic.
- ⏳ **Chốt embedding provider** với team → set env + dim → deploy.

## Bước còn lại (khi đã chốt provider)

### 1. Đổi schema theo dim của provider (nếu ≠ 1024)
```bash
python deploy/load_schema.py --ref <ref> --region ap-northeast-1 \
    --secrets <secrets> --dim 768 --drop      # 768 cho Gemini; DB đang rỗng nên --drop an toàn
```

### 2. Deploy retrieval-api lên Vercel (Python)
```bash
python deploy/build_vercel_api.py               # gom staging (app/ + rag-pipeline/ + entry)
cd deploy/.vercel-api-build && vercel deploy --prod --yes
```
Env cần set trên Vercel project (API):
| Name | Value |
|------|-------|
| `EMBEDDING_PROVIDER` | `gemini` (hoặc provider đã chốt) |
| `GEMINI_API_KEY` | `<key>` (theo provider) |
| `DATABASE_URL` | Supabase pooler URL |
| `CORS_ORIGINS` | `["https://<ui>.vercel.app"]` |
| `ANTHROPIC_API_KEY` | (tùy chọn, cho reformulation) |

> Serverless + DB: nếu tải cao, đổi `DATABASE_URL` sang **transaction pooler (port 6543)**.
> Cho demo tải thấp, session pooler (5432) là đủ.

### 3. Deploy UI (Nuxt) lên Vercel
```bash
cd paperless-ui && vercel deploy --prod --yes
```
Env: `NUXT_RETRIEVAL_API_HOST=https://<api>.vercel.app`, `ANTHROPIC_API_KEY=...`

### 4. Nối dây
Cập nhật `CORS_ORIGINS` ở API cho khớp origin UI → healthcheck `GET /api/healthz` → upload thử 1 PDF.

## Ghi chú
- Không cần `git push` (Vercel CLI deploy từ thư mục local) → né việc chưa có quyền ghi repo.
- Bản Docker/HF Space cũ (`deploy/hf-space/`) giữ lại cho ai muốn self-host đầy đủ (có torch + reranker).
