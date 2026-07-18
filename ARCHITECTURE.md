# Kiến trúc & Tech Stack — Paperless Meetings (VAIC2026)

Tài liệu này (1) mô tả tech stack, (2) cách **giám khảo chạy & test** hệ thống, (3) chỗ
thành phần **PyTorch** (reranker) nằm trong kiến trúc. Phục vụ yêu cầu nộp bài #5.

## 1. Tech stack

| Tầng | Công nghệ | Vai trò |
|------|-----------|---------|
| Frontend | **Nuxt 4** + @nuxt/ui + Tailwind 4 + Vue 3 | Giao diện upload / tóm tắt / chat-trong-tài-liệu |
| LLM orchestration | **Vercel AI SDK** + **Anthropic Claude** (Haiku=map, Sonnet=reduce & chat) | Tóm tắt có cấu trúc, giải thích thuật ngữ, sinh câu hỏi, trả lời Q&A |
| Retrieval API | **FastAPI** (Python 3.12) | `/api/retrieve` (Q&A), `/api/documents` (full doc) |
| Query embedding | **multilingual-e5-large** (1024d, sentence-transformers) | Vector hoá câu hỏi, khớp e5 lúc ingest |
| **Reranker (PyTorch)** | **bge-reranker-v2-m3** fine-tune (xem `finetune/`) | Tầng 2: re-score top-30 → top-5, tăng độ chính xác trích dẫn |
| Vector DB | **Postgres 17 + pgvector** (HNSW cosine) | Lưu chunk + embedding, retrieval scope theo tài liệu |
| Ingest pipeline | **Python** (pdfplumber/pdftotext) → chunk → embed | Giữ metadata `page` + `Điều/Khoản` cho citation |
| Đóng gói | **Docker Compose** | Chạy toàn hệ thống bằng 1 lệnh |

```
┌────────────┐   HTTPS   ┌─────────────────┐   HTTP    ┌────────────────────┐
│  Browser   │──────────▶│  paperless-ui    │──────────▶│  retrieval-api     │
│ (giám khảo)│           │  Nuxt 4 (SSR)    │  /retrieve │  FastAPI            │
└────────────┘           │  + Vercel AI SDK │◀──────────│  ├─ e5 embed        │
                         │  → Anthropic     │  chunks    │  ├─ pgvector top-30 │
                         └───────┬──────────┘  +citation │  └─ RERANKER (torch)│──▶ top-5
                                 │                        └─────────┬──────────┘
                                 │ ingest (subprocess)              │ SQL
                                 ▼                                  ▼
                         ┌──────────────┐                  ┌─────────────────┐
                         │ rag-pipeline │─────ingest──────▶│ Postgres+pgvector│
                         │ parse/chunk  │  chunks+vectors  └─────────────────┘
                         └──────────────┘
```

## 2. Hai cách triển khai để giám khảo test

### Tier 1 — Chạy 1 lệnh trên máy (khuyến nghị cho Vòng 1/2, reproducible, $0 hạ tầng)
```bash
git clone <repo> && cd VAIC2026
cp .env.sample .env          # điền ANTHROPIC_API_KEY
docker compose up            # postgres + retrieval-api + paperless-ui + seed sẵn 1 tài liệu 59 trang
# mở http://localhost:3000
```
- Giám khảo chỉ cần **Docker**. Không cài Python/Node.
- Có **seed sẵn** tài liệu mẫu 59 trang (QĐ 56/2026 Điện Biên) để test ngay, hoặc tự upload.
- Reranker chạy CPU (đủ nhanh cho demo); bật bằng `RERANKER_ENABLED=true`.

### Tier 2 — Live demo URL (khuyến nghị cho nộp online, giám khảo chỉ cần click)
| Thành phần | Nền tảng | Chi phí |
|-----------|----------|---------|
| paperless-ui | **Vercel** | Free |
| retrieval-api + reranker | **Hugging Face Space** (FastAPI, CPU) hoặc Render | Free tier |
| Postgres + pgvector | **Supabase** (pgvector built-in) hoặc Neon | Free tier |
| Reranker model | **Hugging Face Hub** (`honglongdng/bge-reranker-dienbien`) | Free |
| LLM | Anthropic (đặt spending cap) | ~$ theo lượt |
→ Ra 1 URL công khai, giám khảo mở là dùng, không cài gì.

## 3. Kịch bản kiểm thử (bám 5 yêu cầu chức năng)
1. **Upload** 1 PDF 40+ trang → nhận **tóm tắt có cấu trúc < 60s** (bối cảnh / nội dung / điểm quyết định / tác động).
2. Xem **≥10 thuật ngữ** được highlight + giải thích inline.
3. Xem **≥5 câu hỏi phản biện** hệ thống tự sinh.
4. **Hỏi tiếng Việt tự nhiên** trong tài liệu → câu trả lời **trích dẫn trang + Điều/Khoản** cụ thể.
5. (Kỹ thuật) So sánh **bảng eval reranker** (Recall@k/MRR/nDCG: e5 → +reranker → +fine-tuned).

## 4. Điểm mạnh kỹ thuật
- **Grounding & độ tin cậy:** mọi câu trả lời truy vết được tới trang/Điều nhờ metadata citation + reranker hai tầng.
- **Chiều sâu kỹ thuật:** pipeline RAG 2 tầng với model reranker **tự huấn luyện bằng PyTorch**, đóng gói chạy bằng 1 lệnh.
- **Khả thi triển khai:** chạy được trên hạ tầng chi phí thấp; hỗ trợ self-host on-premise phù hợp bài toán dữ liệu pháp lý nhạy cảm.

## 5. Bảo mật & triển khai on-premise
Văn bản pháp lý nhạy cảm → kiến trúc hỗ trợ **on-premise hoàn toàn**: Postgres + retrieval-api +
reranker chạy nội bộ; chỉ bước gọi LLM là ra ngoài (có thể thay bằng model mở self-host ở giai đoạn 2).
