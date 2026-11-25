# T002 - Thiết lập GitHub Actions CI (lint và test)

Cập nhật: 2026-11-25
Epic: E01
Spec: không có
Nhánh: `chore/cau-hinh-ci`
Phụ thuộc: T001

## Mục tiêu
- Cấu hình quy chuẩn lint (`ruff`) và workflow GitHub Actions tự động kiểm tra chất lượng code và chạy unit test trên mỗi PR / push vào `main`.

## Phạm vi (lát cắt dọc)
- Cấu hình cục bộ: `pyproject.toml` khai báo quy tắc `ruff` và cấu hình `pytest`.
- CI: `.github/workflows/ci.yml` chạy cài đặt dependency cần thiết, `ruff check .` và `pytest` không cần webcam.

## Xong khi (kiểm tra được bằng chạy hoặc test)
- [ ] Chạy cục bộ `.venv\Scripts\ruff check .` không báo lỗi.
- [ ] Chạy cục bộ `.venv\Scripts\pytest` đạt 100%.
- [ ] File `.github/workflows/ci.yml` hợp lệ, tự động kích hoạt trên `push` (`main`) và `pull_request` (`main`).

## Ghi chú
- Trong CI không có webcam thật và không có màn hình GUI, nên unit test phải test tầng xử lý độc lập hoặc dùng ảnh tổng hợp/mock.

## Kết quả (điền ở commit cuối nhánh task trước khi push/merge)
- Ngày xong:
- Nhánh / PR chính:
- Việc phát sinh hoặc còn tồn:
