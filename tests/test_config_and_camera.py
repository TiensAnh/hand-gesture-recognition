# Kiểm thử đơn vị cho cấu hình nguồn camera và lớp CameraManager

import threading
import time

import cv2
import numpy as np
import pytest

from src.capture.camera import CameraManager
from src.config.settings import AppConfig, parse_camera_source


# Lớp giả lập cv2.VideoCapture để kiểm thử không phụ thuộc phần cứng webcam
class FakeVideoCapture:
    # Khởi tạo trạng thái mở và dữ liệu khung hình giả lập
    def __init__(self, should_open: bool = True, should_read: bool = True) -> None:
        self._opened = should_open
        self._should_read = should_read
        self.released = False
        self.properties: dict[int, float] = {}

    # Trả về trạng thái kết nối giả lập
    def isOpened(self) -> bool:
        return self._opened

    # Lưu thuộc tính độ phân giải được thiết lập
    def set(self, prop_id: int, value: float) -> bool:
        self.properties[prop_id] = value
        return True

    # Trả về khung hình đen giả lập hoặc thất bại theo cấu hình
    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self._opened or not self._should_read:
            return False, None
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        return True, dummy_frame

    # Đánh dấu đã giải phóng tài nguyên
    def release(self) -> None:
        self._opened = False
        self.released = True


# Kiểm tra cấu hình mặc định có các giá trị hợp lệ
def test_app_config_defaults() -> None:
    config = AppConfig()

    assert config.default_camera_source == "0"
    assert config.frame_width > 0
    assert config.frame_height > 0
    assert config.refresh_interval_ms > 0


# Kiểm tra phân tích chỉ số webcam laptop và camera ảo bên thứ 3
def test_parse_camera_source_indices() -> None:
    assert parse_camera_source("0") == 0
    assert parse_camera_source(" 1 ") == 1
    assert parse_camera_source("2") == 2


# Kiểm tra phân tích URL luồng mạng của ứng dụng camera điện thoại
def test_parse_camera_source_stream_urls() -> None:
    http_url = "http://192.168.1.10:4747/video"
    rtsp_url = "rtsp://192.168.1.10:8554/live"

    assert parse_camera_source(http_url) == http_url
    assert parse_camera_source(f"  {rtsp_url}  ") == rtsp_url


# Kiểm tra báo lỗi khi nguồn camera rỗng hoặc sai định dạng
@pytest.mark.parametrize("invalid_source", ["", "   ", "-1", "abc", "ftp://192.168.1.1/video"])
def test_parse_camera_source_invalid(invalid_source: str) -> None:
    with pytest.raises(ValueError):
        parse_camera_source(invalid_source)


# Kiểm tra mở, đọc khung hình và giải phóng camera thành công
def test_camera_manager_open_read_release() -> None:
    fake_capture = FakeVideoCapture(should_open=True, should_read=True)
    received_sources: list[int | str] = []

    def factory(source: int | str) -> FakeVideoCapture:
        received_sources.append(source)
        return fake_capture

    manager = CameraManager(frame_width=640, frame_height=480, capture_factory=factory)

    try:
        opened, message = manager.open(1)
        assert opened is True
        assert "1" in message
        assert received_sources == [1]
        assert manager.is_opened is True

        success, frame = manager.read_frame()
        assert success is True
        assert frame is not None
        assert frame.shape == (480, 640, 3)
    finally:
        manager.release()

    assert manager.is_opened is False
    assert fake_capture.released is True


# Kiểm tra xử lý gọn khi không mở được webcam hoặc cam bên thứ 3
def test_camera_manager_open_failure() -> None:
    fake_capture = FakeVideoCapture(should_open=False)
    manager = CameraManager(capture_factory=lambda _src: fake_capture)

    try:
        opened, message = manager.open("http://192.168.1.99:4747/video")

        assert opened is False
        assert "Không mở được camera" in message
        assert manager.is_opened is False
        assert fake_capture.released is True
    finally:
        manager.release()


# Kiểm tra đọc khung hình khi chưa mở camera trả về False an toàn
def test_camera_manager_read_when_closed() -> None:
    manager = CameraManager(capture_factory=lambda _src: FakeVideoCapture())

    success, frame = manager.read_frame()

    assert success is False
    assert frame is None


# Kiểm tra open() thiết lập kích thước bộ đệm CAP_PROP_BUFFERSIZE bằng 1
def test_camera_manager_sets_minimal_buffer_size() -> None:
    fake_capture = FakeVideoCapture(should_open=True, should_read=True)
    manager = CameraManager(capture_factory=lambda _src: fake_capture)

    try:
        opened, _ = manager.open("http://192.168.1.182:4747/video")
        assert opened is True
        assert fake_capture.properties.get(cv2.CAP_PROP_BUFFERSIZE) == 1
    finally:
        manager.release()


# Kiểm tra luồng nền liên tục cập nhật frame_id và trả về khung hình mới nhất
def test_camera_manager_background_thread_updates_latest_frame() -> None:
    fake_capture = FakeVideoCapture(should_open=True, should_read=True)
    manager = CameraManager(capture_factory=lambda _src: fake_capture)

    try:
        opened, _ = manager.open(0)
        assert opened is True

        # Đợi khung hình đầu tiên xuất hiện từ luồng nền
        deadline = time.monotonic() + 1.0
        first_frame_id = 0
        first_frame = None
        while time.monotonic() < deadline:
            first_frame_id, first_frame = manager.get_latest_frame()
            if first_frame_id > 0 and first_frame is not None:
                break
            time.sleep(0.005)

        assert first_frame_id > 0
        assert first_frame is not None
        assert first_frame.shape == (480, 640, 3)

        # Kiểm tra frame_id tiếp tục tăng khi luồng nền đọc thêm khung hình
        deadline = time.monotonic() + 1.0
        next_frame_id = first_frame_id
        while time.monotonic() < deadline:
            next_frame_id, _ = manager.get_latest_frame()
            if next_frame_id > first_frame_id:
                break
            time.sleep(0.005)

        assert next_frame_id > first_frame_id
    finally:
        manager.release()


# Kiểm tra phát hiện mất tín hiệu nhanh khi camera đọc lỗi liên tiếp
def test_camera_manager_handles_stream_failure_quickly() -> None:
    fake_capture = FakeVideoCapture(should_open=True, should_read=False)
    manager = CameraManager(capture_factory=lambda _src: fake_capture)

    try:
        opened, _ = manager.open("http://192.168.1.182:4747/video")
        assert opened is True

        started_at = time.monotonic()
        success, frame = manager.read_frame()
        elapsed = time.monotonic() - started_at

        assert success is False
        assert frame is None
        assert elapsed < 0.8
        assert manager.has_error is True
        assert manager.is_opened is True
    finally:
        manager.release()

    assert manager.is_opened is False
    assert manager.has_error is False


# Lớp giả lập VideoCapture bị chặn trong read() để kiểm thử release không chặn
class BlockingVideoCapture(FakeVideoCapture):
    # Khởi tạo sự kiện điều khiển việc nhả hàm read() đang bị chặn
    def __init__(self, unblock_event: threading.Event) -> None:
        super().__init__(should_open=True, should_read=True)
        self._unblock_event = unblock_event
        self.read_started_event = threading.Event()

    # Chặn cho tới khi sự kiện mở khóa được bật rồi trả về thất bại
    def read(self) -> tuple[bool, np.ndarray | None]:
        self.read_started_event.set()
        self._unblock_event.wait(timeout=2.0)
        return False, None


# Kiểm tra release(wait_timeout=0) không chặn và không ảnh hưởng phiên open() mới
def test_camera_manager_non_blocking_release_and_reopen() -> None:
    unblock_old_capture = threading.Event()
    old_capture = BlockingVideoCapture(unblock_old_capture)
    new_capture = FakeVideoCapture(should_open=True, should_read=True)
    captures = [old_capture, new_capture]

    def factory(_source: int | str) -> FakeVideoCapture:
        return captures.pop(0)

    manager = CameraManager(capture_factory=factory)

    try:
        opened_old, _ = manager.open("http://192.168.1.182:4747/video")
        assert opened_old is True
        assert old_capture.read_started_event.wait(timeout=1.0) is True

        # Giải phóng không chặn phải trả về gần như tức thời dù phiên cũ đang kẹt read()
        started_at = time.monotonic()
        manager.release(wait_timeout=0)
        elapsed = time.monotonic() - started_at
        assert elapsed < 0.2
        assert manager.is_opened is False

        # Mở lại ngay phiên mới phải hoạt động độc lập với phiên cũ
        opened_new, _ = manager.open(0)
        assert opened_new is True
        success, frame = manager.read_frame()
        assert success is True
        assert frame is not None
        assert manager.has_error is False
    finally:
        unblock_old_capture.set()
        manager.release()

    # Kiểm tra phiên cũ tự giải phóng an toàn sau khi thoát khỏi read()
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline and not old_capture.released:
        time.sleep(0.01)

    assert old_capture.released is True
    assert new_capture.released is True
