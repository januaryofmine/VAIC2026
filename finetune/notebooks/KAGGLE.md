# Chạy fine-tune trên Kaggle (GPU free)

## 1. Chuẩn bị dataset
1. Nén thư mục `finetune/` (chỉ cần `data/` + `notebooks/`) hoặc push repo lên GitHub.
2. Kaggle → **Datasets** → **New Dataset** → upload → đặt tên **`vaic-finetune`**.
   - Bắt buộc có: `data/train_indomain.jsonl`, `data/eval_indomain.jsonl`, `data/chunks.jsonl`,
     `notebooks/train_reranker.py`, `notebooks/eval_reranker.py`.

## 2. Tạo Notebook
1. Kaggle → **Code** → **New Notebook** → import `notebooks/kaggle_reranker.ipynb`.
2. **Add Input** → chọn dataset `vaic-finetune`.
3. **Settings**:
   - Accelerator → **GPU T4 x1** (hoặc P100).
   - Internet → **On** (để tải model gốc + dataset Zalo).
4. **Run All**.

## 3. Kết quả
- Model fine-tune: `/kaggle/working/bge-reranker-dienbien/` (+ file `.zip` để tải về).
- Bảng số eval + `eval_results.json` (Recall@k / MRR / nDCG cho 3 tầng).

## Thời gian & chi phí
- ~15–30 phút trên T4. **$0** (Kaggle GPU free 30h/tuần).
- Chạy nhanh thử: thêm `--max-queries 300` vào cell train.

## Deps
Kaggle preinstall sẵn `torch`, `transformers`, `datasets`. Notebook chỉ cài thêm
`rank-bm25`, `sentence-transformers`.

## Sau khi train xong
Tải model về `finetune/models/bge-reranker-dienbien/` để:
- Chạy `eval_reranker.py` lại trên máy (CPU cũng được, chỉ chậm hơn).
- Serving: trỏ `RERANKER_MODEL` của retrieval-api vào thư mục model (xem `retrieval-api`).
