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
- **Đã bỏ (2026-11-25):** Không sử dụng CI/CD (GitHub Actions) trong dự án này. Phần cấu hình cục bộ `pyproject.toml` (`ruff` và `pytest`) được chuyển sang `T001`.

## Kết quả (điền ở commit cuối nhánh task trước khi push/merge)
- Ngày xong:
- Nhánh / PR chính:
- Việc phát sinh hoặc còn tồn:
