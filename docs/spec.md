# Đặc tả tổng dự án (Spec)

Cập nhật: 2026-11-25

## 1. Mục tiêu và đối tượng sử dụng
- Dự án giải quyết bài toán gì: Xây dựng hệ thống Desktop Python nhận diện bàn tay và cử chỉ theo thời gian thực qua webcam (hỗ trợ kiểm thử trên ảnh/video), kết hợp huấn luyện mô hình phân loại trên tọa độ landmark để phục vụ bài tập lớn môn Xử lý ảnh.
- Người dùng / vai trò chính: Người dùng cá nhân chạy ứng dụng local trên máy tính (sinh viên demo và giảng viên đánh giá).

## 2. Phạm vi tổng thể
- Các tính năng / nhóm chức năng cốt lõi (Làm):
  - Tiền xử lý ảnh cơ bản bằng OpenCV (lật ảnh, lọc nhiễu/cân bằng sáng CLAHE tùy chọn để so sánh trực quan).
  - Phát hiện bàn tay và trích xuất 21 điểm mốc (landmark) bằng MediaPipe Hands; phân biệt tay trái/tay phải và đếm số ngón tay.
  - Công cụ thu thập dữ liệu tọa độ landmark dạng CSV, huấn luyện và đánh giá mô hình phân loại cử chỉ bằng `scikit-learn` (MLP/SVM/KNN, xuất accuracy, classification report và confusion matrix).
  - Nhận diện 7 cử chỉ cơ bản theo thời gian thực qua webcam (`fist`, `open_palm`, `point`, `peace`, `ok`, `thumbs_up`, `rock`), có làm mượt kết quả theo chuỗi frame và hỗ trợ kiểm thử trên ảnh/video có sẵn.
  - Chế độ ứng dụng thực tế điều khiển bằng cử chỉ (điều chỉnh độ sáng/âm lượng, chuyển slide/media theo file cấu hình `.json`, có cooldown chống lặp và công tắc bật/tắt an toàn).
  - Giao diện Desktop bằng `CustomTkinter` hiển thị luồng video, khung xương bàn tay, nhãn cử chỉ, độ tin cậy, FPS và điều khiển chế độ.
  - Thiết lập CI bằng GitHub Actions tự động chạy lint (`ruff`) và unit test (`pytest`) khi tạo PR hoặc push lên `main`.
- Ngoài phạm vi (Không làm ở giai đoạn hiện tại):
  - Ứng dụng Web/Mobile, Backend/Frontend tách rời.
  - Cơ sở dữ liệu (Database).
  - Nhận diện ngôn ngữ ký hiệu động liên tục thành câu hoàn chỉnh.

## 3. Quy tắc nghiệp vụ và ràng buộc chung
- Quy tắc cốt lõi toàn hệ thống:
  - Dữ liệu huấn luyện landmark lưu dạng `.csv`, mô hình đã huấn luyện lưu dạng `.joblib`/`.pkl`, cấu hình ánh xạ cử chỉ lưu dạng `.json`.
  - Mọi dữ liệu và quá trình xử lý chạy hoàn toàn offline/local trên máy người dùng.
- Ràng buộc phi chức năng:
  - Nền tảng: Windows (Python 3.x), chạy mượt trên CPU không yêu cầu GPU rời.
  - Hiệu năng mục tiêu: xử lý webcam theo thời gian thực (mục tiêu >= 20 FPS trên CPU phổ thông).

## 4. Công nghệ và kiến trúc
- Ngôn ngữ / framework: Python 3.x, `opencv-python`, `mediapipe`, `numpy`, `scikit-learn`, `matplotlib`, `customtkinter`.
- Cơ sở dữ liệu: không có.
- Công cụ build / lint / test / CI: `venv` + `pip` (`requirements.txt`), `ruff` (lint), `pytest` (unit test), GitHub Actions (`.github/workflows/ci.yml`).
- Kiến trúc: Ứng dụng Desktop đơn khối theo module (tách riêng tiền xử lý OpenCV, trích xuất landmark MediaPipe, huấn luyện/dự đoán ML, điều khiển hành động và giao diện CustomTkinter).

## 5. Cấu trúc thư mục
*(Dự kiến — sẽ cập nhật khi khởi tạo mã nguồn)*
- `src/`: mã nguồn chính của ứng dụng (xử lý ảnh, nhận diện bàn tay, phân loại cử chỉ, điều khiển, GUI).
- `data/`: tập dữ liệu tọa độ landmark (`.csv`) và ảnh/video mẫu kiểm thử.
- `models/`: mô hình phân loại đã huấn luyện và cấu hình nhãn.
- `scripts/`: script thu thập dữ liệu, huấn luyện và đánh giá mô hình.
- `tests/`: kiểm thử tự động bằng `pytest`.
- `.github/workflows/`: cấu hình GitHub Actions CI.
- `docs/`: tài liệu đặc tả (`spec.md`, `specs/`) và tiến độ (`progress/`).

## 6. Lệnh chạy
*(Dự kiến — sẽ cập nhật sau khi tạo `requirements.txt` và `pyproject.toml`)*
- Cài đặt: `python -m venv .venv` rồi `.venv\Scripts\pip install -r requirements.txt`
- Chạy dev: `.venv\Scripts\python -m src.main`
- Lint: `.venv\Scripts\ruff check .`
- Test: `.venv\Scripts\pytest`

## 7. Quy ước chung của dự án
- Code Python theo chuẩn PEP 8 (kiểm tra bằng `ruff`), tách rõ phần xử lý thuật toán (không phụ thuộc GUI/webcam) khỏi lớp giao diện `CustomTkinter` để dễ viết unit test chạy trong CI.
- Không commit file môi trường ảo (`.venv/`), cache Python (`__pycache__/`) hay video dung lượng lớn vào Git.
