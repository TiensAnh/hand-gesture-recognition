# E02 - Dữ liệu, Huấn luyện & Nhận diện cử chỉ ML

Cập nhật: 2026-11-25
Spec: không có
Ưu tiên: P1

## Mục tiêu
- Xây dựng trọn vẹn quy trình Machine Learning trên tọa độ 21 landmark: trích xuất/chuẩn hóa đặc trưng, thu thập dataset CSV, huấn luyện và đánh giá mô hình phân loại 7 cử chỉ cơ bản, tích hợp nhận diện realtime vào ứng dụng.

## Phạm vi
- Làm: chuẩn hóa vector đặc trưng, công cụ thu thập dữ liệu, script huấn luyện/đánh giá `scikit-learn` (MLP, SVM, KNN), nhận diện 7 cử chỉ (`fist`, `open_palm`, `point`, `peace`, `ok`, `thumbs_up`, `rock`) qua webcam và ảnh/video.
- Không làm: điều khiển hệ điều hành/ứng dụng ngoài bằng cử chỉ (thuộc E03).

## Danh sách task (theo thứ tự làm)
Ký hiệu: `[ ]` chưa làm | `[~]` đang làm | `[x]` xong | `[!]` vướng | `[-]` bỏ

- [ ] T004 - Chuẩn hóa đặc trưng và công cụ thu thập dữ liệu — `feature/thu-thap-du-lieu`
- [ ] T005 - Huấn luyện và đánh giá mô hình phân loại cử chỉ — `feature/huan-luyen-mo-hinh`
- [ ] T006 - Tích hợp nhận diện cử chỉ realtime và ảnh/video — `feature/nhan-dien-cu-chi-realtime`

## Vướng mắc / chờ quyết định
- Chưa có.
