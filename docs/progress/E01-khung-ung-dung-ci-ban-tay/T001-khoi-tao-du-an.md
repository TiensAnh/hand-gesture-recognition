# T001 - Khởi tạo dự án và khung app webcam

Cập nhật: 2026-11-26
Epic: E01
Spec: không có
Nhánh: `chore/khoi-tao-du-an`
Phụ thuộc: không

## Mục tiêu
- Dựng cấu trúc thư mục chuẩn, quản lý thư viện Python, kiểm thử `pytest` đầu tiên và khung giao diện CustomTkinter mở/đóng webcam realtime ổn định.

## Phạm vi (lát cắt dọc)
- Cấu hình dự án: `.gitignore`, `requirements.txt`, `requirements-dev.txt`, `pyproject.toml` (cấu hình `ruff` và `pytest`), cấu trúc `src/`, `tests/`, `data/`, `models/`, `scripts/`.
- Giao diện & Webcam: cửa sổ CustomTkinter hiển thị luồng webcam từ OpenCV, có nút Bật/Tắt camera và xử lý gọn khi không có webcam.
- Kiểm thử: unit test kiểm tra cấu hình/hàm tiện ích cơ bản bằng `pytest`.

## Xong khi (kiểm tra được bằng chạy hoặc test)
- [x] Cài đặt được thư viện trong môi trường ảo `.venv` không lỗi.
- [x] Chạy `.venv\Scripts\python -m src.main` mở được cửa sổ CustomTkinter, bật/tắt webcam mượt và đóng cửa sổ không treo tiến trình.
- [x] Chạy `.venv\Scripts\ruff check .` và `.venv\Scripts\pytest` đạt 100%.

## Ghi chú
- Tách phần quản lý camera khỏi lớp giao diện để dễ mở rộng xử lý frame ở T003.

## Kết quả (điền ở commit cuối nhánh task trước khi push/merge)
- Ngày xong: 2026-11-26
- Nhánh / PR chính: `chore/khoi-tao-du-an`
- Việc phát sinh hoặc còn tồn: Đã tối ưu đọc nền, mở/tắt camera không chặn UI cho nguồn DroidCam Wi-Fi và sửa lỗi `TclError` khi gỡ ảnh khỏi `CTkLabel`; phần dropdown chọn camera (`CTkComboBox`) để lại cân nhắc sau nếu cần.
