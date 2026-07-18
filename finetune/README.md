# Fine-tune — Cross-Encoder Reranker (PyTorch)

Mục tiêu: huấn luyện **reranker tiếng Việt cho văn bản pháp lý** làm tầng 2 của retrieval,
vừa tăng độ chính xác citation vừa là thành phần học máy **tự huấn luyện bằng PyTorch** của hệ thống.

```
Retrieval hiện tại:  query → e5 embed → cosine top-5 → answer
Sau khi thêm:        query → e5 embed → cosine top-30 → [RERANKER PyTorch] → top-5 → answer
```

Base model fine-tune: `BAAI/bge-reranker-v2-m3` (cross-encoder đa ngôn ngữ, tiếng Việt tốt, 568M).

## Pipeline

| Bước | Script | Chạy ở đâu | Trạng thái |
|------|--------|-----------|-----------|
| 1. Tải tài liệu pháp quy công khai | `scripts/scrape_docs.py`, `scripts/crawl_congbao.py` | Local | ✅ 6 docs |
| 2. Parse + chunk (page/section) | `scripts/build_chunks.py` | Local | ✅ 129 chunks |
| 3. Sinh QA in-domain (Claude Code) | `scripts/sample_candidates.py` + agent → `data/qa.jsonl` | Local | ✅ 27 cặp |
| 4. Mine hard negatives (BM25) | `scripts/mine_negatives.py` | Local | ✅ |
| 5. Train reranker (PyTorch thuần) | `notebooks/train_reranker.py` | **Kaggle GPU** | ⏳ user chạy |
| 6. Eval Recall@k / MRR / nDCG | `notebooks/eval_reranker.py` | Kaggle/Local | ⏳ user chạy |
| 7. Serving vào retrieval-api | `retrieval-api/app/services/reranking.py` | Local | ✅ (mặc định tắt) |

> Bước 1-4 + 7 đã xong và smoke-test trên CPU. Bước 5-6 chạy trên Kaggle: xem [notebooks/KAGGLE.md](notebooks/KAGGLE.md).

## Cấu trúc thư mục

```
finetune/
  data/
    raw/          # PDF/HTML tải về
    chunks.jsonl  # {doc_id, position, page, section, text}
    qa.jsonl      # {query, positive_chunk_id, doc_id}  (Claude Code sinh)
    train.jsonl   # {query, positive, negatives[]}      (sau mine negatives)
    test.jsonl
  scripts/
  notebooks/
  models/         # checkpoint tải về từ Kaggle
```

## Định dạng dữ liệu

`qa.jsonl` (mỗi dòng 1 cặp):
```json
{"query": "Điều kiện được hưởng trợ cấp là gì?", "positive_chunk_id": "doc3::12", "doc_id": "doc3"}
```

`train.jsonl` (sau khi mine negatives — dùng để train cross-encoder):
```json
{"query": "...", "positive": "văn bản chunk đúng", "negatives": ["chunk sai 1", "chunk sai 2", ...]}
```

## Chi phí
- Data gen: **$0** (Claude Code sinh, không gọi API ngoài).
- Train: **$0** (Kaggle GPU free 30h/tuần).
- Base model + tài liệu: **$0** (open-source / công khai).
