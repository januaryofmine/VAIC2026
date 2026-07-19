# Thí nghiệm: thêm dữ liệu tỉnh khác vào TRAIN có giúp không?

## Câu hỏi
Reranker hiện train trên 35 câu hỏi Điện Biên. **Thêm dữ liệu các tỉnh khác
(cùng thể loại quyết định/nghị quyết UBND cấp tỉnh) vào tập train có nâng chất lượng
trên chính tập test Điện Biên không?**

Đây KHÔNG phải lặp lại sai lầm Zalo: Zalo là **luật trung ương** (lệch domain, đã làm
R@1 rớt 0.83 → 0.52). Sơn La / Đắk Lắk là **văn bản hành chính cấp tỉnh** — cùng văn phong,
cùng cấu trúc Điều/Khoản, cùng dạng câu hỏi.

## Thiết kế (kiểm soát biến)

| | Baseline (đã đo) | Đa tỉnh v1 | Đa tỉnh v2 (dự phòng) |
|---|---|---|---|
| Train | 35 câu Điện Biên | **67 câu** = 35 ĐB + 32 tỉnh khác | **88 câu** = 35 ĐB + 53 tỉnh khác |
| Test | **18 câu Điện Biên** | **18 câu — Y HỆT** | **18 câu — Y HỆT** |
| Model gốc | `BAAI/bge-reranker-v2-m3` | y hệt | y hệt |
| Siêu tham số | LoRA r=16 α=32, 6 epoch, lr 1e-4, batch 8, max_len 384 | **y hệt** | **y hệt** |

File: `data/train_multiprovince.jsonl` (v1) · `data/train_multiprovince_v2.jsonl` (v2).
v2 chỉ chạy nếu v1 cho tín hiệu tích cực — để không đốt vô ích quota GPU miễn phí.

**Chỉ đổi đúng một thứ: dữ liệu train.** Mọi thứ khác giữ nguyên nên chênh lệch kết quả
quy được về đúng biến đó.

Tập test được **đóng băng** ở `data/frozen/eval_dienbien_18_FROZEN.jsonl` trước khi bắt đầu,
để không có khả năng vô tình thay đổi rồi so sánh nhầm.

## Dữ liệu tỉnh khác thu thập được

| Nguồn | Tài liệu | Chunks |
|---|---|---|
| congbao.sonla.gov.vn | 42 quyết định UBND tỉnh | ~1.050 |
| congbao.daklak.gov.vn | 1 công báo (Nghị quyết HĐND + QĐ UBND) | ~50 |
| **Tổng** | **43** | **1.101** |

Không tải được: Vĩnh Phúc, Thanh Hóa (host timeout / 404).

Cách lấy: `scripts/harvest_sonla.py` — view `/congbao.nsf/VanBanQPPL2` render thẳng link
`<UNID>/$file/<tên>.pdf` trong HTML (khác Điện Biên vốn dựng link bằng JS nên phải dò tay).
Bẫy: tên file có dấu cách nên regex phải bắt tới phần mở rộng, không dừng ở khoảng trắng.

QA: 32 câu hỏi tiếng Việt tự nhiên do Claude Code soạn từ 85 chunk mẫu, mỗi câu gắn đúng
1 chunk chứa đáp án; hard negatives đào bằng BM25 trong cùng văn bản (6 negative/câu).

## Kết quả (đo xong 19/07/2026, Kaggle kernel v12)

Tất cả đo trên **cùng 18 câu Điện Biên đóng băng**:

| Cấu hình | Recall@1 | Recall@3 | MRR | nDCG@5 |
|---|---|---|---|---|
| e5 retrieval only | 0.7222 | 0.9444 | 0.8194 | 0.8645 |
| + bge-reranker gốc | 0.8333 | 1.0000 | 0.8981 | 0.9239 |
| + LoRA train **35 câu Điện Biên** (baseline) | **0.8889** | 1.0000 | **0.9444** | **0.9590** |
| + LoRA train **67 câu đa tỉnh** | **0.8889** | 1.0000 | **0.9444** | **0.9590** |

### Kết luận: KHÔNG THAY ĐỔI — không tốt lên, cũng không tệ đi

Hai dòng cuối **trùng khít đến từng chữ số**. Thêm 32 câu hỏi từ Sơn La/Đắk Lắk vào tập
train làm dịch chuyển kết quả đúng **0,0000**.

Đã kiểm chứng kernel thật sự dùng tập mới (không nhầm file):
```
in-domain triples: 67                    (baseline: 35)
training samples=469  batches/epoch=58   (baseline: 245)
TRAIN_MULTI = .../data/train_multiprovince.jsonl
eval queries: 18 | avg pool: 13.1
```

### Vì sao không đổi — trần đo lường (ceiling)

Đây mới là phát hiện đáng giá: **tập test đã chạm trần, không còn dư địa để đo.**

- `Recall@3` và `Recall@5` đã = **1.000** ở cả model gốc lẫn model fine-tune → mọi đoạn đúng
  đều đã nằm trong top-3. Không còn gì để cải thiện ở đó.
- Chỉ `Recall@1` còn dư địa: 0.8889 = **16/18 câu** đúng ở vị trí 1. Chỉ **2 câu** chưa đạt.
- Muốn nhích Recall@1 lên phải sửa đúng 2 câu đó — mà 32 ví dụ từ tỉnh khác rõ ràng không
  chạm tới được chúng.

Nói cách khác: **nút thắt không phải thiếu dữ liệu train, mà là tập test 18 câu quá nhỏ để
phân giải thêm.** Mỗi câu = 5,6 điểm phần trăm; không thể đo được cải thiện nhỏ hơn thế.

### Điều này vẫn có giá trị

So sánh 3 lần fine-tune trên cùng một tập test cho ra một quy luật rõ:

| Dữ liệu train thêm | Recall@1 | Nhận xét |
|---|---|---|
| Zalo (luật trung ương — **lệch domain**) | **0.52** ↓↓ | catastrophic forgetting |
| Không thêm gì (35 câu Điện Biên) | 0.889 | baseline |
| Sơn La/Đắk Lắk (**cùng domain**) | 0.889 → | an toàn, nhưng không thêm gì |

→ Khẳng định được: **dữ liệu cùng-domain KHÔNG gây hại** (khác hẳn Zalo). Đây là bằng chứng
cho tính khả thi nhân rộng: đưa thêm tỉnh vào không làm hỏng model đã có.

### Không chạy tiếp v2 (88 câu) — và vì sao

Đã dựng sẵn `train_multiprovince_v2.jsonl` (35 + 53 câu) nhưng **không chạy**: v1 dịch chuyển
đúng 0,0000, và trần đo lường vẫn y nguyên, nên v2 gần như chắc chắn cho cùng kết quả.
Chạy thêm chỉ tốn quota GPU mà không tạo thông tin mới.

### Việc nên làm thay thế (nếu muốn đo tiếp)

1. **Mở rộng tập TEST**, không phải tập train — thêm 40-60 câu hỏi Điện Biên nữa để mỗi câu
   chỉ còn ~1-2 điểm phần trăm, đủ phân giải cải thiện nhỏ.
2. **Soi 2 câu đang sai** ở vị trí 1: chúng hỏng vì mơ hồ, vì chunk bị cắt, hay vì model?
   Sửa đúng nguyên nhân sẽ hiệu quả hơn đổ thêm dữ liệu.

---

## Vòng 2 — đã thực thi đề xuất (1): mở rộng tập TEST

Kết luận trên nói nút thắt là **độ phân giải tập test**, nên bước tiếp theo là mở rộng nó.

### Cách lấy thêm câu hỏi
`scripts/dump_unused.py` liệt kê các chunk **chưa từng được dùng làm đáp án** trong `qa.jsonl`
— đó chính là vật liệu còn trống để soạn câu hỏi mới mà không trùng lặp.

Kiểm kê cho thấy dư địa lớn: **198 chunks, chỉ 41 chunk đã dùng làm đáp án / 53 câu hỏi.**
Nhiều tài liệu gần như chưa khai thác (báo cáo CĐSQG: 9 chunk trống, 142/QĐ-VPCP: 2, 565/QĐ-TTg: 15).

Đã soạn thêm **26 câu hỏi Điện Biên** từ các chunk trống này → **79 QA**, chia lại
grouped-by-positive-chunk (vẫn không rò rỉ): **46 train / 33 test**.

| | Vòng 1 | Vòng 2 |
|---|---|---|
| Tổng QA Điện Biên | 53 | **79** |
| Train / Test | 35 / 18 | **46 / 33** |
| Mỗi câu test đáng | 5,6 điểm % | **3,0 điểm %** |

Tập test mới đóng băng tại `data/frozen/eval_dienbien_33_FROZEN.jsonl`.

### Thiết kế vòng 2
Vì tập test đổi, **số cũ không so sánh trực tiếp được nữa** — nên phải chạy lại **cả hai
cấu hình** trên tập test mới trong cùng một kernel, giữ nguyên siêu tham số:

| | A (baseline mới) | B (đa tỉnh) |
|---|---|---|
| Train | 46 câu Điện Biên | **78 câu** = 46 ĐB + 32 Sơn La/Đắk Lắk |
| Test | 33 câu Điện Biên đóng băng | **y hệt** |
| Siêu tham số | LoRA r=16 α=32, 6 epoch, lr 1e-4, batch 8, max_len 384 | **y hệt** |

File: `data/train_dienbien_v2.jsonl` (A) · `data/train_multiprovince_v3.jsonl` (B).
Notebook: `kaggle_kernel/kaggle_reranker.ipynb` (kernel v13) — in ra số dòng thực tế của
từng file trước khi train, để **tin số đếm chứ không tin tên file** (bài học vòng 1).

### Trạng thái
⏳ Kernel v13 đang chạy. Kết quả sẽ ghi bổ sung vào đây và vào `RESULTS.md`.

Điều cần lưu ý khi đọc kết quả: nếu A trên test-33 **thấp hơn** 0.889 của test-18, đó
**không phải model tệ đi** — mà là tập test cũ dễ hơn (đã chạm trần). Con số duy nhất có
nghĩa là **chênh lệch B − A trên cùng test-33**.

## Ghi chú vận hành

- Không tải được model 2,2GB về máy: `IncompleteRead(369MB đọc, còn 1,9GB)` — mạng đứt giữa
  chừng, lặp lại 2 lần. Lấy số liệu bằng cách gọi thẳng API
  `GET /api/v1/kernels/output` (trả về trường `log`, 513KB) thay vì `kaggle kernels output`
  vốn cố tải cả model. Mẹo này nên dùng lại cho các lần đo sau.

