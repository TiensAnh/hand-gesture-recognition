# T006 - Tích hợp nhận diện cử chỉ realtime và ảnh/video

Cập nhật: 2026-11-25
Epic: E02
Spec: không có
Nhánh: `feature/nhan-dien-cu-chi-realtime`
Phụ thuộc: T005

## Mục tiêu
- Tích hợp mô hình đã huấn luyện vào ứng dụng CustomTkinter để nhận diện 7 cử chỉ realtime kèm làm mượt chuỗi frame và hỗ trợ mở ảnh/video có sẵn để kiểm thử.

## Phạm vi (lát cắt dọc)
- Dự đoán & Làm mượt: nạp model từ `models/`, lọc theo ngưỡng độ tin cậy (confidence threshold) và làm mượt nhãn bằng cửa sổ trượt (majority voting).
- Giao diện: hiển thị tên cử chỉ, thanh/phần trăm độ tin cậy, nút chọn nguồn đầu vào (Webcam / Ảnh / Video).
- Kiểm thử: unit test cho bộ lọc ngưỡng tin cậy và thuật toán làm mượt theo cửa sổ frame.

## Xong khi (kiểm tra được bằng chạy hoặc test)
- [ ] Ứng dụng nhận diện realtime 7 cử chỉ qua webcam ổn định, ít nhấp nháy nhãn.
- [ ] Mở và nhận diện được trên file ảnh tĩnh hoặc video có sẵn từ giao diện.
- [ ] `ruff check .` và `pytest` đều đạt.

## Ghi chú
- Khi chưa có file model trong `models/`, ứng dụng vẫn chạy chế độ phát hiện bàn tay bình thường và hiển thị thông báo rõ thay vì văng lỗi.

## Kết quả (điền ở commit cuối nhánh task trước khi push/merge)
- Ngày xong:
- Nhánh / PR chính:
- Việc phát sinh hoặc còn tồn:
