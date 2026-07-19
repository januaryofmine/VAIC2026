# Kịch bản quay video demo — Paperless Meetings (VAIC2026)

Thời lượng đích: **4 phút**. Có bản rút gọn 2 phút ở cuối.

---

## PHẦN 0 — Checklist TRƯỚC KHI BẤM GHI (đừng bỏ qua)

Quay hỏng vì hạ tầng là mất cả buổi. Chạy hết list này trước:

- [ ] **Mở demo, upload thử 1 lần trọn vẹn** — upload → tóm tắt → thuật ngữ → câu hỏi → hỏi đáp.
      Nếu bước nào lỗi thì sửa trước, đừng quay rồi cắt.
- [ ] **LLM có key sống không?** Nếu tóm tắt trả rỗng hoặc treo → key chưa cấu hình trên Vercel.
- [ ] **Tài liệu demo đã ingest sẵn** trong hệ thống (đừng để camera phải chờ ingest 59 trang).
      Nhưng vẫn giữ 1 bản để **upload live** cho phần mở đầu — xem mẹo "upload thật, chờ giả" bên dưới.
- [ ] **Chuẩn bị sẵn câu hỏi Q&A** đã thử trước và biết chắc ra trích dẫn đẹp.
      Gợi ý (đã kiểm chứng trên QĐ 56/2026): *"Quyết định này công bố bao nhiêu văn bản hết hiệu lực?"*
- [ ] **Đóng hết tab/thông báo cá nhân**, bật chế độ Do Not Disturb, ẩn bookmark bar.
- [ ] **Zoom trình duyệt 110–125%** — chữ trên video nén sẽ dễ đọc hơn nhiều.
- [ ] **Đồng hồ bấm giây** mở sẵn ở góc màn hình (cho phần chứng minh < 60 giây).
- [ ] *(Nếu muốn demo reranker live)* nhờ đồng nghiệp set biến `RERANKER_MODEL` trên HF Space trước.
      **Chưa set thì đừng nói "model của chúng tôi đang chạy"** — nói theo phương án B ở Cảnh 5.

---

## KỊCH BẢN 4 PHÚT

### Cảnh 1 — Vấn đề (0:00 – 0:25)
**Hình:** một PDF 59 trang cuộn nhanh, dày đặc chữ. Hoặc quay màn hình lướt tài liệu thật.

**Lời:**
> "Đây là tài liệu một cuộc họp cấp tỉnh: **59 trang**, đầy thuật ngữ pháp lý.
> Cán bộ thường nhận nó **trước cuộc họp một ngày**.
> Không ai đọc kịp. Kết quả: vào họp không nắm nội dung, họp kéo dài vì phải giải thích lại,
> và không ai chuẩn bị được câu hỏi phản biện."

*Nhịp: nói nhanh, dứt khoát. Đây là 25 giây bán vấn đề, không phải bán sản phẩm.*

---

### Cảnh 2 — Tóm tắt < 60 giây (0:25 – 1:05)
**Hình:** kéo thả file PDF vào giao diện → **bấm đồng hồ ngay khi thả** → màn hình xử lý → tóm tắt hiện ra → **dừng đồng hồ, để số hiện rõ**.

**Lời:**
> "Cán bộ chỉ cần thả tài liệu vào."
> *(chờ, để đồng hồ chạy — đừng lấp bằng lời)*
> "…Và đây. **[đọc đúng số trên đồng hồ] giây** cho 59 trang.
> Bản tóm tắt có cấu trúc: **bối cảnh**, **nội dung chính**, **các điểm cần quyết định**, và **tác động**.
> Đây không phải tóm tắt chung chung — nó nêu đúng 50 văn bản hết hiệu lực, tách 22 nghị quyết HĐND và 28 quyết định UBND."

**Quan trọng:** để đồng hồ trong khung hình suốt lúc chờ. Con số tự chứng minh, không cần nói "rất nhanh".

---

### Cảnh 3 — Thuật ngữ được giải thích (1:05 – 1:35)
**Hình:** chuyển tab Thuật ngữ. Rê chuột chậm qua 3–4 thuật ngữ, dừng lại ở phần giải thích.

**Lời:**
> "Hệ thống tự phát hiện thuật ngữ chuyên ngành và giải thích ngay tại chỗ.
> **VBQPPL**, **phân cấp nguồn thu**, **định giá đất**…
> Với cán bộ mới hoặc trái ngành, đây là thứ giúp họ theo kịp cuộc họp."

*Đừng đọc hết danh sách. Chọn 3 cái nghe "khó" nhất rồi dừng lại ở một cái.*

---

### Cảnh 4 — Câu hỏi phản biện (1:35 – 2:05)
**Hình:** tab Câu hỏi gợi ý. **Zoom vào đúng 1 câu sắc nhất.**

**Lời:**
> "Và đây là phần tôi thích nhất. Hệ thống không chỉ tóm tắt — nó **đặt câu hỏi phản biện** thay cán bộ."
> *(đọc to 1 câu, chậm)*
> "*'Một số quyết định có hiệu lực trước ngày ban hành — điều này có vi phạm nguyên tắc hiệu lực hồi tố không?'*
> Đó là câu hỏi mà một chuyên viên pháp chế có kinh nghiệm mới nghĩ ra.
> Hệ thống đưa nó cho cán bộ **trước khi vào phòng họp**."

*Đây là khoảnh khắc gây ấn tượng mạnh nhất. Cho nó thở — dừng 1 giây sau khi đọc xong.*

---

### Cảnh 5 — Hỏi đáp có trích dẫn (2:05 – 2:45)
**Hình:** gõ câu hỏi tiếng Việt → câu trả lời hiện ra → **click vào trích dẫn → nhảy đúng trang/Điều trong PDF bên cạnh**.

**Lời:**
> "Trong cuộc họp, cán bộ hỏi thẳng bằng tiếng Việt."
> *(gõ câu hỏi đã chuẩn bị)*
> "Câu trả lời kèm **trích dẫn trang và số Điều**. Và click vào là nhảy thẳng tới đúng chỗ trong văn bản gốc.
> **Cán bộ kiểm chứng được** — đó mới là thứ khiến họ dám dùng nó trong phòng họp."

**Đây là cảnh quan trọng nhất về mặt tin cậy.** Phải quay được cú click → nhảy trang. Nếu UI chưa có tính năng nhảy trang, chỉ cần chỉ tay vào số trang/Điều và nói rõ.

---

### Cảnh 6 — Chiều sâu kỹ thuật: model PyTorch tự huấn luyện (2:45 – 3:30)
**Hình:** cắt khỏi giao diện. Hiện **sơ đồ 2 tầng** rồi **bảng số**.

**Lời:**
> "Phần này là khác biệt kỹ thuật. Hầu hết hệ thống dừng ở tìm kiếm vector — chúng tôi đo được
> **chỉ 72% câu hỏi có đoạn đúng ở vị trí số một**. Với văn bản pháp lý, trích dẫn sai là mất niềm tin.
>
> Nên chúng tôi **tự huấn luyện một model bằng PyTorch** — một cross-encoder đọc câu hỏi và
> đoạn văn cùng lúc, đặt làm tầng hai để chấm lại 30 ứng viên.
>
> Và tôi muốn kể cả **lần thất bại**: fine-tune toàn bộ trên một bộ dữ liệu luật lớn khiến model
> **tệ đi** — từ 0,83 xuống 0,52. Nhờ quy trình đánh giá tách sạch nên chúng tôi phát hiện,
> chẩn đoán là catastrophic forgetting, rồi sửa bằng **LoRA** và dữ liệu đúng lĩnh vực.
>
> Kết quả trên 18 câu hỏi chưa từng thấy: Recall@1 từ **0,72 lên 0,83 rồi 0,89**.
> Chi phí huấn luyện: **0 đồng**, trên GPU miễn phí."

**Hình kèm bảng:**

| | Recall@1 | MRR | nDCG@5 |
|---|---|---|---|
| Chỉ tìm kiếm vector | 0.72 | 0.82 | 0.86 |
| + reranker gốc | 0.83 | 0.90 | 0.92 |
| **+ model chúng tôi train** | **0.89** | **0.94** | **0.96** |

> ⚠️ **Nếu biến `RERANKER_MODEL` chưa set trên Space:** đừng nói "đang chạy trên bản demo này".
> Nói: *"Model này đã public trên Hugging Face và tích hợp sẵn trong API — đây là số đo trên tập kiểm tra tách riêng."* Vẫn đúng sự thật, vẫn ăn điểm.

---

### Cảnh 7 — Khả thi triển khai + chốt (3:30 – 4:00)
**Hình:** sơ đồ kiến trúc, hoặc màn hình terminal đang chạy hệ thống nội bộ.

**Lời:**
> "Toàn hệ thống chạy được **on-premise**: tài liệu pháp lý của tỉnh không cần rời khỏi máy chủ nội bộ.
> Huấn luyện lại mất 20 phút, chi phí bằng không, suy luận chạy được trên CPU.
>
> Với cán bộ dự họp, giá trị không nằm ở chỗ hệ thống trả lời trôi chảy — mà ở chỗ họ
> **lật đúng trang, đúng Điều để kiểm chứng**. Đó là thứ chúng tôi xây."

*Dừng 1 nhịp trước câu cuối. Nói chậm lại.*

---

## BẢN RÚT GỌN 2 PHÚT (nếu bị giới hạn)

Bỏ Cảnh 3 và 7. Rút Cảnh 6 còn 20 giây (chỉ bảng số + một câu "chúng tôi tự train bằng PyTorch, 0,72 → 0,89").

Thứ tự giữ: **Vấn đề (15s) → Tóm tắt có bấm giờ (35s) → Câu hỏi phản biện (25s) → Q&A có trích dẫn (35s) → Bảng số PyTorch (20s) → Chốt (10s)**.

---

## TIPS & TRICKS KHI QUAY

### Kỹ thuật quay
1. **Quay 1920×1080, 30fps.** Đừng quay màn hình 4K rồi để nền tảng nén — chữ sẽ nhòe.
2. **Zoom trình duyệt 110–125%** trước khi quay. Chữ mặc định trên web quá nhỏ khi xem trên điện thoại.
3. **Ẩn hết thứ gây nhiễu:** bookmark bar, extension, thông báo, tab cá nhân, tên máy tính.
   Dùng cửa sổ trình duyệt sạch (profile mới) nếu được.
4. **Con trỏ chuột di chậm và có chủ đích.** Rê chuột loạn là dấu hiệu rõ nhất của video nghiệp dư.
   Trước khi click, dừng con trỏ ở nút 0,5 giây.
5. **Công cụ:** OBS Studio (miễn phí, tốt nhất) hoặc ShareX. Windows Game Bar (Win+G) cũng đủ dùng.

### Về thời gian chờ
6. **Chờ thật thì để nguyên, chờ lâu thì cắt — nhưng phải nói rõ.**
   Với mốc "< 60 giây", **tuyệt đối không cắt** — để đồng hồ chạy thật. Đó là bằng chứng.
   Với bước ingest/upload dài, cắt và hiện chữ *"đã tua nhanh phần tải lên"*. Giám khảo trừ điểm
   nếu phát hiện cắt giấu, nhưng không trừ nếu bạn ghi rõ.
7. **Mẹo "upload thật, chờ giả":** ingest tài liệu **trước** khi quay. Lúc quay, vẫn kéo thả file thật
   (cảnh này chân thực), nhưng hệ thống đã có sẵn dữ liệu nên trả kết quả nhanh. Không gian dối —
   bạn đang demo bước tóm tắt, không phải bước upload.

### Về giọng nói
8. **Thu tiếng riêng, đừng thu trực tiếp khi đang thao tác.** Quay hình trước, lồng tiếng sau —
   bạn sẽ nói mượt hơn nhiều và không bị tiếng gõ phím/chuột.
9. **Dùng tai nghe có mic, thu trong phòng có rèm/chăn.** Tiếng vang phòng trống làm video rẻ tiền ngay.
10. **Nói chậm hơn bạn nghĩ là cần.** Người xem đang vừa đọc màn hình vừa nghe.
11. **Đừng đọc kịch bản như đọc văn bản.** Đọc trước 2–3 lần cho thuộc ý, rồi nói bằng lời của mình.

### Về nội dung
12. **Con số cụ thể luôn thắng tính từ.** "59 trang", "0,72 lên 0,89", "0 đồng" — chứ không phải
    "rất nhanh", "rất chính xác", "chi phí thấp".
13. **Chỉ nhấn 3 con số trong cả video.** Nhiều số quá thì không ai nhớ số nào.
    Chọn: **thời gian tóm tắt** · **0,72 → 0,89** · **0 đồng**.
14. **Kể lần thất bại.** Slide/cảnh nói về việc fine-tune làm model tệ đi rồi sửa được là đoạn
    ăn điểm nhất với giám khảo kỹ thuật — nó chứng minh có quy trình đo lường trung thực.
15. **Đừng khoe tính năng chưa chắc chạy.** Thà 4 tính năng chạy mượt còn hơn 6 tính năng có 1 cái lỗi.
16. **Thêm phụ đề.** Nhiều giám khảo xem không bật tiếng. CapCut tự tạo phụ đề tiếng Việt khá tốt.

### Bẫy hay gặp
17. **Đừng để lộ thông tin nhạy cảm:** API key trong terminal, email cá nhân, tên tài khoản cloud,
    đường dẫn chứa tên thật. Kiểm tra lại từng khung hình có terminal.
18. **Quay 2–3 lần rồi chọn.** Lần đầu luôn tệ hơn bạn tưởng. Lần thứ ba thường là bản dùng được.
19. **Xem lại trên điện thoại trước khi nộp.** Chữ nhỏ, màu nhạt, hoặc tương phản kém sẽ lộ ngay.
20. **Kiểm tra file xuất:** đúng định dạng ban tổ chức yêu cầu, dưới giới hạn dung lượng,
    và **mở được trên máy khác** (đừng nộp file chỉ chạy được trên máy bạn).
