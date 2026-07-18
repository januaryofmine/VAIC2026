# VAIC2026 — Paperless Meetings

## ⚠️ QUY TẮC PHỐI HỢP (BẮT BUỘC — nhiều Claude chạy song song)

Nhiều phiên Claude có thể làm việc cùng lúc trên repo này. Để tránh xung đột, **mọi Claude phải tuân thủ**:

1. **Trước khi làm bất cứ việc gì:** đọc [TASKS.csv](TASKS.csv). Đây là nguồn sự thật về ai đang làm gì.
2. **Nhận việc (claim):** chỉ chọn task có cột `owner` **trống**. Điền `owner` (tên phiên của bạn, ví dụ `claude-B`) và đặt `status=in-progress` **trước khi** bắt đầu code. Ghi lại file bạn sẽ sửa vào cột `files`.
3. **Không đụng file của người khác:** nếu một task đang `in-progress` bởi owner khác, **không** sửa các file liệt kê ở cột `files` của task đó. Chọn việc khác hoặc chờ.
4. **Phạm vi (area) tách biệt:** ưu tiên làm trọn 1 `area` (finetune / retrieval-api / paperless-ui / rag-pipeline / docs). Tránh sửa chéo area đang có người giữ.
5. **Xong việc:** cập nhật `status=done` + ghi chú kết quả vào cột `notes`. Nếu bị chặn, đặt `status=blocked` + lý do.
6. **Cập nhật thường xuyên:** đọc lại TASKS.csv trước mỗi lần claim mới (file có thể đã đổi). Ghi thay đổi nhỏ, cập nhật CSV ngay, không gom lại cuối buổi.
7. **Thêm việc mới:** nếu phát sinh task chưa có, thêm 1 dòng vào TASKS.csv (id tăng dần: T16, T17...) rồi mới claim.
8. **File dùng chung** (`CLAUDE.md`, `TASKS.csv`, `docker-compose.yaml`): sửa tối thiểu, nhanh gọn, tránh giữ lâu.

Phases: `plan` (thiết kế) → `execute` (code) → `test` (chạy/verify). Một task nên đi qua đủ 3 phase.

---


## Định hướng kỹ thuật
Hệ thống theo kiến trúc **RAG** cho tài liệu pháp lý tiếng Việt, có thành phần học máy tự
huấn luyện bằng **PyTorch** (cross-encoder reranker fine-tune trên văn bản pháp quy) nhằm
nâng độ chính xác truy xuất và trích dẫn trang/điều khoản — thay vì chỉ gọi API bên thứ ba.
Chi tiết pipeline huấn luyện ở [finetune/](finetune/) và kiến trúc ở [ARCHITECTURE.md](ARCHITECTURE.md).

## Vòng đánh giá & Tiêu chí chấm điểm

Mọi bài nộp trải qua **3 vòng**:
- **Vòng 1 — AI sơ loại:** Tất cả các đội. Sàng lọc tự động vòng đầu cho mọi bài nộp.
- **Vòng 2 — Giám khảo đánh giá:** Top 30–40 đội. Giám khảo chuyên môn đánh giá các dự án lọt vòng trong.
- **Vòng 3 — Demo Day (LIVE):** Top 10 đội. Pitch trực tiếp **4 phút + 2 phút Q&A** trước giám khảo.

Chấm theo **6 tiêu chí, tổng 100 điểm**:

| # | Tiêu chí | Điểm |
|---|----------|------|
| 1 | Chất lượng triển khai kỹ thuật | 20 |
| 2 | Kiến trúc AI-Native & Đổi mới sáng tạo | 20 |
| 3 | Tính khả thi kinh doanh & Lộ trình Pilot | 20 |
| 4 | UX AI-Native & Tư duy thiết kế | 15 |
| 5 | An toàn AI, Grounding & Độ tin cậy | 15 |
| 6 | Trình bày & Bảo vệ giải pháp | 10 |

## Đề bài cuộc thi

**Paperless Meetings: AI for document processing & Meeting preparation**

- **Đơn vị đề xuất:** Department of Science and Technology, Dien Bien province (Sở Khoa học và Công nghệ tỉnh Điện Biên)
- **Chủ đề:** Chính phủ Thông minh (Smart Government)

### Bối cảnh (Context)
Các cuộc họp cấp tỉnh thường xử lý tài liệu 40–60 trang đầy thuật ngữ pháp lý, hành chính và kỹ thuật chuyên ngành. Tài liệu thường chỉ được gửi cho cán bộ **một ngày trước cuộc họp** — không đủ thời gian đọc kỹ. Hậu quả:
- Cán bộ vào họp mà chưa nắm được nội dung cốt lõi.
- Cuộc họp kéo dài vì mọi thứ phải giải thích lại từ đầu.
- Câu hỏi và phản biện không được chuẩn bị trước.

### Bài toán cần giải (Problem to solve)
Xây dựng hệ thống AI giúp cán bộ đọc, hiểu và chuẩn bị cho cuộc họp trong thời gian ngắn:

1. **Smart summarization (Tóm tắt thông minh):** Upload tài liệu (PDF/Word) → AI trả về bản tóm tắt có cấu trúc: bối cảnh, nội dung chính, các điểm quyết định, và tác động.
2. **Highlight and explain terminology (Đánh dấu & giải thích thuật ngữ):** Tự động đánh dấu các điều khoản quan trọng và thuật ngữ chuyên ngành, kèm giải thích ngắn gọn ngay trong tài liệu (inline).
3. **Suggested questions and related files (Gợi ý câu hỏi & tài liệu liên quan):** Dựa trên nội dung, AI đề xuất danh sách câu hỏi cán bộ nên chuẩn bị để thảo luận hiệu quả, và gợi ý các tài liệu/quy định liên quan để tham khảo.
4. **Meeting interface (Giao diện họp):** Trong cuộc họp, cán bộ có thể nhanh chóng hỏi về nội dung tài liệu bằng tiếng Việt tự nhiên và nhận câu trả lời trích dẫn cụ thể trang/điều khoản.

### Dữ liệu / Tài nguyên (Data / Resources)
- Văn bản quy phạm pháp luật, nghị quyết, và tài liệu hội nghị công khai từ UBND tỉnh và Chính phủ.
- Các đội có thể dùng tài liệu mẫu công khai 40–60 trang để phát triển và kiểm thử.

### Yêu cầu nộp bài tối thiểu (Minimum submission requirements)
1. **Summarization demo:** Upload một tài liệu thực tế 40+ trang và nhận bản tóm tắt có cấu trúc trong **< 60 giây**.
2. **Highlight & explain terminology:** Phát hiện và giải thích chính xác **ít nhất 10 thuật ngữ chuyên ngành**.
3. **Suggested questions:** Hệ thống tự sinh **ít nhất 5 câu hỏi phản biện chất lượng** (critical-thinking) từ nội dung.
4. **Document-grounded Q&A:** Hỏi bằng tiếng Việt tự nhiên → AI trả lời kèm **trích dẫn trang/mục cụ thể**.
5. **Architecture document + 1-page deck:** Mô hình xử lý, nguồn dữ liệu, lộ trình triển khai thực tế tại UBND.
