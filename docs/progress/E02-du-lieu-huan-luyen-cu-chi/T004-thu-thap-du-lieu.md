# T004 - Chuẩn hóa đặc trưng và công cụ thu thập dữ liệu

Cập nhật: 2026-11-25
Epic: E02
Spec: không có
Nhánh: `feature/thu-thap-du-lieu`
Phụ thuộc: T003

## Mục tiêu
- Xây dựng hàm chuẩn hóa 21 landmark thành vector đặc trưng bất biến theo vị trí và tỉ lệ, cùng công cụ thu thập mẫu 7 cử chỉ từ webcam lưu ra `data/gestures.csv`.

## Phạm vi (lát cắt dọc)
- Đặc trưng: chuyển 21 điểm (x, y) về hệ tọa độ tương đối theo cổ tay (landmark 0) và chuẩn hóa theo độ lớn lớn nhất thành vector 42 chiều.
- Thu thập dữ liệu: script/chế độ thu thập cho phép chọn nhãn trong 7 cử chỉ cơ bản, ghi mẫu liên tục hoặc theo phím bấm và thống kê số mẫu từng lớp trong `data/gestures.csv`.
- Kiểm thử: unit test kiểm tra tính bất biến tịnh tiến/tỉ lệ của vector đặc trưng và đọc/ghi CSV.

## Xong khi (kiểm tra được bằng chạy hoặc test)
- [ ] Thu thập và lưu được mẫu vào `data/gestures.csv` cho các nhãn cử chỉ, hiển thị rõ số mẫu hiện có từng lớp.
- [ ] Unit test chứng minh vector đặc trưng không đổi khi dịch chuyển hoặc phóng to/thu nhỏ bàn tay.
- [ ] `ruff check .` và `pytest` đều đạt.

## Ghi chú
- Đảm bảo không làm mất dữ liệu cũ khi chạy thu thập bổ sung (hỗ trợ ghi nối tiếp).

## Kết quả (điền ở commit cuối nhánh task trước khi push/merge)
- Ngày xong:
- Nhánh / PR chính:
- Việc phát sinh hoặc còn tồn:
