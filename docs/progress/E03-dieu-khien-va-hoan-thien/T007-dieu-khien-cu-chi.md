# T007 - Chế độ điều khiển thực tế bằng cử chỉ

Cập nhật: 2026-11-25
Epic: E03
Spec: không có
Nhánh: `feature/dieu-khien-cu-chi`
Phụ thuộc: T006

## Mục tiêu
- Cho phép bật chế độ điều khiển ứng dụng/máy tính bằng cử chỉ (độ sáng/âm lượng hoặc phím slide/media) theo file cấu hình `.json` với cơ chế cooldown chống kích hoạt lặp.

## Phạm vi (lát cắt dọc)
- Logic điều khiển: đọc ánh xạ cử chỉ → hành động từ file `.json`, kiểm tra thời gian giữ cử chỉ (hold) và cooldown trước khi thực thi.
- Giao diện: công tắc bật/tắt chế độ điều khiển (mặc định tắt để an toàn) và hiển thị log hành động gần nhất vừa kích hoạt.
- Kiểm thử: unit test kiểm tra logic hold/cooldown và ánh xạ cấu hình (mock phần gọi hệ điều hành để chạy được trên CI).

## Xong khi (kiểm tra được bằng chạy hoặc test)
- [ ] Khi bật chế độ điều khiển, cử chỉ kích hoạt đúng hành động đã cấu hình và không bị lặp liên tục nhờ cooldown.
- [ ] Khi tắt chế độ điều khiển, hệ thống chỉ nhận diện và không gửi lệnh điều khiển.
- [ ] `ruff check .` và `pytest` đều đạt.

## Ghi chú
- Tách lớp thực thi lệnh hệ điều hành riêng để dễ thay đổi hoặc mock khi test trên Linux CI.

## Kết quả (điền ở commit cuối nhánh task trước khi push/merge)
- Ngày xong:
- Nhánh / PR chính:
- Việc phát sinh hoặc còn tồn:
