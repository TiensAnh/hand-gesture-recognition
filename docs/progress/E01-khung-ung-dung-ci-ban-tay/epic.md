# E01 - Khung ứng dụng & Nhận diện bàn tay realtime

Cập nhật: 2026-11-26
Spec: không có
Ưu tiên: P1

## Mục tiêu
- Xây dựng nền tảng dự án Python Desktop chạy được webcam realtime và hiển thị nhận diện bàn tay (21 landmark, tay trái/phải, đếm ngón tay) trên giao diện.

## Phạm vi
- Làm: khởi tạo cấu trúc dự án, giao diện CustomTkinter cơ bản, cấu hình lint/test cục bộ (`ruff` + `pytest`), tiền xử lý OpenCV và phát hiện bàn tay bằng MediaPipe Hands.
- Không làm: thu thập dataset CSV, huấn luyện mô hình ML phân loại 7 cử chỉ (thuộc E02), điều khiển máy tính (thuộc E03).

## Danh sách task (theo thứ tự làm)
Ký hiệu: `[ ]` chưa làm | `[~]` đang làm | `[x]` xong | `[!]` vướng | `[-]` bỏ

- [x] T001 - Khởi tạo dự án và khung app webcam — `chore/khoi-tao-du-an`
- [-] T002 - Thiết lập GitHub Actions CI (lint và test) — `chore/cau-hinh-ci`
- [ ] T003 - Tiền xử lý OpenCV và nhận diện bàn tay MediaPipe — `feature/tien-xu-ly-va-ban-tay`

## Vướng mắc / chờ quyết định
- Chưa có.
