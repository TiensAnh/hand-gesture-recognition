# T003 - Tiền xử lý OpenCV và nhận diện bàn tay MediaPipe

Cập nhật: 2026-11-25
Epic: E01
Spec: không có
Nhánh: `feature/tien-xu-ly-va-ban-tay`
Phụ thuộc: T001

## Mục tiêu
- Tích hợp bước tiền xử lý OpenCV tùy chọn và phát hiện bàn tay MediaPipe Hands vẽ 21 landmark, phân biệt tay trái/phải, đếm ngón tay và hiển thị FPS realtime trên GUI.

## Phạm vi (lát cắt dọc)
- Xử lý ảnh: module tiền xử lý OpenCV (lật gương, Gaussian blur giảm nhiễu, cân bằng sáng CLAHE tùy chọn).
- Nhận diện bàn tay: module bọc MediaPipe Hands trích xuất 21 landmark, nhãn `Left`/`Right`, thuật toán đếm số ngón tay đang giơ.
- Giao diện: bật/tắt tiền xử lý, hiển thị khung xương bàn tay, tay trái/phải, số ngón tay và FPS trên CustomTkinter.
- Kiểm thử: unit test cho tiền xử lý OpenCV và hàm đếm ngón tay từ tọa độ landmark mẫu.

## Xong khi (kiểm tra được bằng chạy hoặc test)
- [ ] Webcam hiển thị rõ 21 landmark, phân biệt đúng tay trái/phải, đếm đúng 0–5 ngón tay và hiển thị FPS.
- [ ] Bật/tắt tùy chọn tiền xử lý (lật gương, lọc nhiễu, CLAHE) hoạt động ngay trên giao diện.
- [ ] `ruff check .` và `pytest` đều đạt.

## Ghi chú
- Giữ interface trả về tọa độ landmark chuẩn hóa để dùng trực tiếp cho T004 ở E02.

## Kết quả (điền ở commit cuối nhánh task trước khi push/merge)
- Ngày xong:
- Nhánh / PR chính:
- Việc phát sinh hoặc còn tồn:
