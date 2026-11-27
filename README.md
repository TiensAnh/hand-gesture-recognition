# Hệ thống nhận diện bàn tay và cử chỉ realtime (Xử lý ảnh)

Ứng dụng Desktop Python nhận diện bàn tay và cử chỉ theo thời gian thực qua webcam hoặc camera điện thoại (DroidCam / IP Webcam), sử dụng OpenCV, MediaPipe Hands, scikit-learn và CustomTkinter.

## Yêu cầu môi trường
- Windows 10/11
- Python 3.11+

## Cài đặt
Chạy các lệnh sau tại thư mục gốc của repo (`xu-ly-anh/`):

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

Nếu cần chạy lint và kiểm thử tự động:

```powershell
.\.venv\Scripts\pip install -r requirements-dev.txt
```

Tải mô hình nhận diện bàn tay MediaPipe (`models/hand_landmarker.task`, ~7.5 MB):

```powershell
.\.venv\Scripts\python scripts\download_hand_model.py
```

## Chạy ứng dụng
```powershell
.\.venv\Scripts\python -m src.main
```

### Chọn nguồn camera trong ứng dụng
- **Webcam laptop:** nhập `0` rồi bấm **Bật camera**.
- **Camera ảo bên thứ 3 (DroidCam Client / Iriun):** nhập `1` hoặc `2`.
- **DroidCam qua Wi-Fi (khuyên dùng nếu cam laptop hỏng hoặc xung đột driver Windows):**
  1. Mở app **DroidCam** trên điện thoại (chung Wi-Fi với máy tính). Nếu đang mở DroidCam Client trên Windows thì bấm **Stop** trước.
  2. Nhập URL `http://<WiFi-IP>:4747/video` (ví dụ `http://192.168.1.182:4747/video`) vào ô **Nguồn camera:** rồi bấm **Bật camera**.

## Kiểm tra chất lượng code
```powershell
.\.venv\Scripts\ruff check .
.\.venv\Scripts\pytest
```

## Cấu trúc thư mục
- `src/`: mã nguồn chính của ứng dụng
  - `src/capture/`: quản lý mở, đọc luồng nền và giải phóng camera (`CameraManager`)
  - `src/config/`: cấu hình mặc định và phân tích nguồn camera
  - `src/vision/`: tiền xử lý OpenCV (lật gương, Gaussian blur, CLAHE) và nhận diện bàn tay MediaPipe (`HandTracker`, đếm ngón tay, FPS)
  - `src/gui/`: giao diện Desktop CustomTkinter
  - `src/main.py`: điểm khởi chạy ứng dụng
- `data/`: tập dữ liệu landmark (`.csv`) và ảnh/video mẫu kiểm thử
- `models/`: mô hình phân loại cử chỉ đã huấn luyện
- `scripts/`: script thu thập dữ liệu, huấn luyện và đánh giá mô hình
- `tests/`: kiểm thử tự động bằng `pytest`
- `docs/`: tài liệu đặc tả (`spec.md`) và tiến độ (`progress/`)
