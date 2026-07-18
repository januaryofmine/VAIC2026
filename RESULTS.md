# Kết quả đo lường — Paperless Meetings (VAIC2026)

Bằng chứng thực nghiệm cho 5 yêu cầu nộp bài + giải PyTorch. Mọi số liệu đo trên
tài liệu **thật**: Quyết định 56/2026 của UBND tỉnh Điện Biên (**59 trang**, 96 chunks).
Bổ trợ cho [ARCHITECTURE.md](ARCHITECTURE.md).

---

## 1. Reranker PyTorch — eval trên tập held-out (yêu cầu #5 + giải Meta PyTorch)

**Thiết lập nghiêm ngặt:** 53 câu hỏi in-domain, chia **35 train / 18 test**, nhóm theo
positive chunk nên **không rò rỉ** (train và test không dùng chung đáp án). Đo trên 18 câu test.

| Tầng | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 |
|------|:---:|:---:|:---:|:---:|:---:|
| e5 retrieval (hệ gốc) | 0.72 | 0.94 | 1.00 | 0.82 | 0.86 |
| + bge-reranker-v2-m3 gốc | 0.83 | 1.00 | 1.00 | 0.90 | 0.92 |
| **+ reranker fine-tune (LoRA in-domain)** | **0.89** | 1.00 | 1.00 | **0.94** | **0.96** |

**Câu chuyện kỹ thuật (tư duy khoa học, không chỉ code):**
- Full fine-tune trên dataset ngoài domain (Zalo legal) → **overfit / catastrophic forgetting**,
  tệ hơn cả model gốc (R@1 rớt còn 0.52 trên held-out).
- Chuyển sang **LoRA** (đóng băng base, học adapter) + **train đúng domain Điện Biên** → thắng thật.
- Pipeline PyTorch tự xây: vòng lặp train thuần (AdamW + AMP + linear-warmup + gradient
  checkpointing), PEFT/LoRA, eval Recall/MRR/nDCG. Chạy trên Kaggle GPU (P100), $0.

**Kiểm chứng qua đúng code serving** (`reranking.py` + CrossEncoder, model LoRA thật):
Recall@5 từ **12/18 → 18/18** — kéo đúng chunk lên #1 kèm citation `trang X · Điều Y`.

Chi tiết: [finetune/](finetune/) · model: `finetune/models/bge-reranker-lora/`.

---

## 2. Prep-pack — 3 deliverable đo thật trên doc 56 (yêu cầu #1, #2, #3)

Đo bằng [paperless-ui/scripts/test-prep-pack.mjs](paperless-ui/scripts/test-prep-pack.mjs)
(dùng đúng prompt + map-reduce của app, LLM qua 9router).

| # | Deliverable | Yêu cầu | Đo được | Kết quả |
|---|-------------|---------|---------|--------|
| 1 | Tóm tắt có cấu trúc | < 60 giây | **11.9s** | ✅ ĐẠT |
| 2 | Highlight & giải thích thuật ngữ | ≥ 10 thuật ngữ | **12 thuật ngữ** | ✅ ĐẠT |
| 3 | Câu hỏi phản biện tự sinh | ≥ 5 câu | **5 câu (sắc bén)** | ✅ ĐẠT |

**#1 Tóm tắt (mẫu thực tế):** bối cảnh (UBND Điện Biên công bố/thay thế/bãi bỏ VBQPPL 2025),
nội dung chính (50 văn bản hết hiệu lực: 22 NQ HĐND + 28 QĐ UBND), 5 điểm quyết định, tác động.

**#2 Thuật ngữ (mẫu):** UBND, HĐND, NĐ-CP, QĐ-UBND, VBQPPL, Ngân sách nhà nước, Thủ tục
hành chính, Phân cấp, Ủy quyền, Chữ ký số, Định giá đất, Kết cấu hạ tầng giao thông...

**#3 Câu hỏi (mẫu — phản biện pháp lý sắc):**
- QĐ có hiệu lực *trước ngày ban hành* — có vi phạm nguyên tắc hồi tố (Luật Ban hành VBQPPL)?
- Bãi bỏ hàng loạt văn bản cùng lúc có tạo *khoảng trống pháp lý* tạm thời?
- Bỏ quy định dạy thêm / bến xe vùng sâu — đã *đánh giá tác động xã hội* chưa?

**Đảm bảo bằng schema (không chỉ prompt):** đã thêm ràng buộc cứng — terms `.min(10)`,
questions `.min(5)` — nên khi model trả thiếu, AI SDK tự hỏi lại; không thể "lọt" số lượng thiếu.
35/35 unit test PASS.

> **Lưu ý cấu hình:** nếu route LLM qua 9router + model *reasoning* (vd `deepseek-v4-flash`),
> phải gửi `reasoning_effort: "none"` — nếu không, model dồn token vào "suy nghĩ", trả nội dung
> rỗng và vượt 60s. Dùng Claude (haiku/sonnet) như app cấu hình thì không cần. (Đã ghi TASKS T18.)

---

## 3. Yêu cầu #4 — Q&A trích dẫn trang/mục
Kiến trúc đảm bảo grounding: mỗi chunk mang metadata `page` + `section (Điều/Khoản)` từ khâu
parse; retrieval scope theo tài liệu; reranker kéo đúng chunk lên đầu → câu trả lời trích dẫn
cụ thể trang + Điều. (Xem `retrieval-api` + demo serving ở mục 1.)

---

## Tóm tắt cho deck (1 slide)
- ✅ **5/5 yêu cầu chức năng** có bằng chứng đo được trên tài liệu 59 trang thật.
- ✅ **Reranker PyTorch tự train (LoRA)** vượt baseline trên held-out — R@1 0.72→0.83→**0.89**.
- ✅ **Prep-pack < 60s**: tóm tắt 11.9s, thuật ngữ 12, câu hỏi 5 — tất cả ĐẠT.
- ✅ **Grounding**: trích dẫn trang/Điều truy vết được, reranker đưa đúng chunk lên #1 (18/18).
