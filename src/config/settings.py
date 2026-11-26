# Quản lý cấu hình mặc định và phân tích nguồn camera cho ứng dụng

from dataclasses import dataclass

# Các tiền tố giao thức mạng hợp lệ cho camera bên thứ 3 (IP Webcam, DroidCam Wi-Fi)
SUPPORTED_STREAM_PREFIXES = ("http://", "https://", "rtsp://", "rtmp://")


# Cấu hình mặc định cho cửa sổ ứng dụng và luồng camera
@dataclass(frozen=True)
class AppConfig:
    window_title: str = "Nhận diện cử chỉ bàn tay"
    window_width: int = 960
    window_height: int = 680
    default_camera_source: str = "0"
    frame_width: int = 640
    frame_height: int = 480
    refresh_interval_ms: int = 15


# Chuyển chuỗi nguồn camera người dùng nhập sang chỉ số nguyên hoặc URL luồng mạng
def parse_camera_source(raw_source: str) -> int | str:
    cleaned_source = raw_source.strip()

    # Báo lỗi nếu người dùng để trống nguồn camera
    if not cleaned_source:
        raise ValueError("Nguồn camera không được để trống.")

    # Chấp nhận chỉ số số nguyên không âm cho webcam laptop (0) hoặc cam ảo bên thứ 3 (1, 2...)
    if cleaned_source.isdigit():
        return int(cleaned_source)

    # Chấp nhận URL luồng video cho ứng dụng camera điện thoại qua Wi-Fi
    lower_source = cleaned_source.lower()
    if lower_source.startswith(SUPPORTED_STREAM_PREFIXES):
        return cleaned_source

    raise ValueError(
        "Nguồn camera không hợp lệ. Hãy nhập chỉ số (0, 1, 2...) hoặc URL (http://..., rtsp://...)."
    )
