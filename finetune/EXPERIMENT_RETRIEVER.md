# Thí nghiệm: fine-tune tầng truy xuất (e5) có phá được trần không?

## Vì sao làm

Vòng 2 của thí nghiệm reranker cho một phát hiện đổi hướng: **trần đã dịch khỏi reranker.**

Trên 33 câu held-out, reranker đã tận dụng hết những gì tầng 1 đưa lên, nhưng tầng 1 chỉ đạt
`Recall@1 = 0.6970` và `Recall@5 = 0.9697` — nghĩa là có **1/33 câu mà e5 không hề đưa đáp án
vào top-5**. Reranker chỉ sắp xếp lại danh sách ứng viên, nên câu đó **không thể cứu được ở
tầng sau**. Muốn nhích tiếp thì phải sửa chính e5.

## Cách làm

`notebooks/train_retriever.py` — vòng lặp PyTorch thuần, cùng cơ chế với `train_reranker.py`
để hai bên so sánh được (AdamW, linear warmup, AMP, gradient checkpointing, LoRA,
`merge_and_unload`).

**Loss: InfoNCE** trên `[positive]` + `[hard negative BM25 cùng văn bản]` + `[in-batch]`.

Hard negative là phần quan trọng: in-batch negative đơn thuần **quá dễ**. Hai đoạn thuộc hai
văn bản khác nhau thì phân biệt không cần học; những đoạn gây nhầm thật sự nằm trong **cùng
một văn bản** — đúng điều kiện lúc chấm, vì truy xuất trong sản phẩm được giới hạn theo tài liệu.

Chỉ số `target` của ma trận logits là chỗ dễ sai nhất nên được kiểm chứng bằng bài test có răng
trước khi chạy GPU: mapping đúng → loss 0,0007; mapping sai → loss 16,6.

## Lần 1 — lr 1e-4, 10 epoch, 4 hard negative

Huấn luyện chạy đúng: `trainable 2.359.296 / 562.249.728 tham số (0,42%)`,
loss giảm đều `2,1346 → 1,0393` qua 10 epoch.

| Chỉ số (33 câu) | e5 gốc | e5 fine-tune | Chênh lệch |
|---|---|---|---|
| Recall@1 | 0.6970 | **0.7273** | +0.0303 (+1 câu) |
| Recall@3 | 0.9394 | 0.9394 | 0 |
| **Recall@5** | **0.9697** | **0.9394** | **−0.0303 (−1 câu)** |
| **MRR** | **0.8210** | **0.8207** | **−0.0003** |
| nDCG@5 | 0.8577 | 0.8452 | −0.0125 |

### Kết luận lần 1: KẾT QUẢ ÂM

**MRR đứng yên là dấu hiệu quyết định.** MRR tổng hợp vị trí của đáp án trên *toàn bộ* xếp
hạng; nó không nhúc nhích (−0,0003) nghĩa là chất lượng xếp hạng **không cải thiện gì cả**.
Mô hình chỉ **xáo chỗ**: kéo một câu lên hạng 1, đồng thời đánh rơi một câu khác ra khỏi top-5.

Tệ hơn, `Recall@5` — **đúng chỉ số mà thí nghiệm này nhắm sửa** — lại đi ngược: từ 1 câu lọt
lưới thành 2 câu. nDCG@5 giảm theo, xác nhận đây không phải nhiễu một chiều.

Nếu chỉ nhìn `Recall@1` rồi báo "+0.0303, cải thiện", ta đã báo cáo sai một mô hình **kém hơn**
mô hình gốc. Đây là lý do không được chọn một chỉ số duy nhất để kết luận.

### Chẩn đoán

46 ví dụ với lr 1e-4 là **quá mạnh** cho một không gian embedding đã pretrain tốt.

Vì sao reranker chịu được mà bi-encoder thì không — khác biệt nằm ở cấu trúc bài toán:

| | Cross-encoder (reranker) | Bi-encoder (e5) |
|---|---|---|
| Cách chấm | đọc **cặp** (câu hỏi, đoạn) cùng lúc | mã hoá **độc lập** thành vector |
| Phạm vi ảnh hưởng khi học | cục bộ, theo từng cặp | **toàn cục** — dịch cả không gian vector |
| Hậu quả khi lệch | một cặp chấm sai | **mọi** truy vấn đều bị ảnh hưởng, recall hỏng |

Fine-tune bi-encoder trên dữ liệu nhỏ làm méo không gian vector đã học tốt từ hàng trăm triệu
cặp — cái mất (recall toàn cục) lớn hơn cái được (một câu lên hạng 1).

## Lần 2 — cấu hình thận trọng

Một lần thử nữa, có lý do nguyên tắc chứ không phải dò bừa: nếu chẩn đoán "học quá mạnh" đúng
thì hạ cường độ học phải cho kết quả khá hơn.

- `lr 2e-5` (thấp hơn 5 lần) · `4 epoch` (thay vì 10) · `8 hard negative` (thay vì 4)
- Mọi thứ khác **giữ nguyên**, vẫn đo trên **đúng 33 câu đóng băng**.

> Ghi rõ để minh bạch: đây là **cấu hình thứ hai và là cấu hình cuối** được thử ở nhánh này.
> Cả hai kết quả đều được báo cáo. Không chạy tiếp rồi chỉ chọn lần đẹp nhất.

**Nếu lần 2 vẫn không thắng e5 gốc ở `Recall@5`**, kết luận sẽ là: ở quy mô dữ liệu hiện tại
(46 ví dụ huấn luyện), **không nên fine-tune tầng truy xuất**. Đường đi đúng khi đó là sửa
**dữ liệu và cách cắt đoạn**, không phải sửa trọng số mô hình.

## Giá trị của nhánh này dù kết quả âm

Ba lần fine-tune trên cùng một tập test cho một quy luật nhất quán về **thứ nên train**:

| Đối tượng fine-tune | Dữ liệu | Kết quả |
|---|---|---|
| Cross-encoder (reranker) | Zalo — lệch domain | **0.52** ↓↓ hỏng nặng |
| Cross-encoder (reranker) | Điện Biên — đúng domain | **0.8485** ↑ thắng rõ |
| Bi-encoder (e5) | Điện Biên — đúng domain | **xấu đi ở R@5** |

→ Đúng domain là **điều kiện cần, không phải điều kiện đủ**. Còn phải chọn đúng **thành phần**
để huấn luyện: ở quy mô dữ liệu nhỏ, cross-encoder là chỗ đáng train, bi-encoder thì không.
