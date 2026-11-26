# Lớp quản lý mở, đọc khung hình trên luồng nền và giải phóng camera bằng OpenCV

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import cv2

# Số lần đọc lỗi liên tiếp tối đa trước khi đánh dấu mất tín hiệu camera
DEFAULT_MAX_CONSECUTIVE_FAILURES = 15
# Thời gian nghỉ ngắn khi đọc lỗi để tránh luồng nền chiếm 100% CPU
FAILURE_RETRY_DELAY_SECONDS = 0.01
# Thời gian chờ tối đa cho khung hình đầu tiên khi gọi read_frame đồng bộ
DEFAULT_FIRST_FRAME_TIMEOUT_SECONDS = 1.0
# Thời gian chờ mặc định để luồng nền kết thúc khi giải phóng camera
DEFAULT_RELEASE_JOIN_TIMEOUT_SECONDS = 1.0


# Đóng gói trạng thái cô lập cho mỗi phiên mở kết nối VideoCapture
@dataclass
class _CaptureSession:
    capture: Any
    stop_event: threading.Event
    first_frame_event: threading.Event
    release_lock: threading.Lock
    released: bool = False
    thread: threading.Thread | None = None


# Giải phóng đối tượng VideoCapture của một phiên đúng một lần an toàn
def _release_session_capture(session: _CaptureSession) -> None:
    with session.release_lock:
        if session.released:
            return
        session.released = True

    try:
        session.capture.release()
    except Exception:
        pass


# Quản lý kết nối webcam laptop, camera ảo bên thứ 3 và luồng IP camera
class CameraManager:
    # Khởi tạo cấu hình nguồn camera, hàm tạo VideoCapture và trạng thái đồng bộ
    def __init__(
        self,
        source: int | str = 0,
        frame_width: int = 640,
        frame_height: int = 480,
        capture_factory: Callable[[int | str], Any] | None = None,
        max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES,
    ) -> None:
        self._source: int | str = source
        self._frame_width = frame_width
        self._frame_height = frame_height
        self._capture_factory = capture_factory if capture_factory is not None else cv2.VideoCapture
        self._max_consecutive_failures = max(1, max_consecutive_failures)

        self._lock = threading.Lock()
        self._session: _CaptureSession | None = None
        self._is_opened = False
        self._latest_frame: Any | None = None
        self._frame_id = 0
        self._stream_failed = False

    # Trả về nguồn camera hiện tại
    @property
    def source(self) -> int | str:
        with self._lock:
            return self._source

    # Kiểm tra camera có đang mở theo cờ trạng thái thread-safe
    @property
    def is_opened(self) -> bool:
        with self._lock:
            return self._is_opened

    # Kiểm tra luồng camera có đang gặp lỗi mất tín hiệu hay không
    @property
    def has_error(self) -> bool:
        with self._lock:
            return self._stream_failed

    # Mở kết nối tới nguồn camera chỉ định và khởi chạy luồng đọc nền
    def open(self, source: int | str | None = None) -> tuple[bool, str]:
        with self._lock:
            target_source = self._source if source is None else source

        # Đóng kết nối cũ trước khi mở nguồn mới
        self.release()

        try:
            capture = self._capture_factory(target_source)
        except Exception as exc:
            return False, f"Không thể khởi tạo camera ({target_source}): {exc}"

        # Kiểm tra thiết bị hoặc luồng mạng có mở thành công không
        if capture is None or not capture.isOpened():
            if capture is not None:
                capture.release()
            return (
                False,
                f"Không mở được camera '{target_source}'. "
                "Kiểm tra lại kết nối webcam hoặc ứng dụng camera điện thoại.",
            )

        # Giảm bộ đệm nội bộ xuống tối thiểu và thiết lập độ phân giải mong muốn
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._frame_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._frame_height)

        # Tạo phiên cô lập riêng cho lần mở này
        session = _CaptureSession(
            capture=capture,
            stop_event=threading.Event(),
            first_frame_event=threading.Event(),
            release_lock=threading.Lock(),
        )
        worker_thread = threading.Thread(
            target=self._reader_loop,
            args=(session,),
            daemon=True,
        )
        session.thread = worker_thread

        with self._lock:
            self._source = target_source
            self._session = session
            self._is_opened = True
            self._latest_frame = None
            self._frame_id = 0
            self._stream_failed = False

        worker_thread.start()
        return True, f"Đang mở camera: {target_source}"

    # Vòng lặp nền liên tục rút khung hình mới nhất để tránh trễ bộ đệm
    def _reader_loop(self, session: _CaptureSession) -> None:
        consecutive_failures = 0

        try:
            while not session.stop_event.is_set():
                try:
                    success, frame = session.capture.read()
                except Exception:
                    success, frame = False, None

                if session.stop_event.is_set():
                    break

                # Cập nhật khung hình mới nhất dưới khóa khi đọc thành công
                if success and frame is not None:
                    consecutive_failures = 0
                    with self._lock:
                        if not session.stop_event.is_set() and self._session is session:
                            self._latest_frame = frame
                            self._frame_id += 1
                            self._stream_failed = False
                    session.first_frame_event.set()
                    continue

                # Đếm lỗi liên tiếp và báo mất tín hiệu khi vượt ngưỡng cho phép
                consecutive_failures += 1
                if consecutive_failures >= self._max_consecutive_failures:
                    with self._lock:
                        if not session.stop_event.is_set() and self._session is session:
                            self._stream_failed = True
                    break

                time.sleep(FAILURE_RETRY_DELAY_SECONDS)
        finally:
            session.first_frame_event.set()
            _release_session_capture(session)

    # Trả về mã khung hình và ảnh mới nhất không chặn dành cho luồng giao diện
    def get_latest_frame(self) -> tuple[int, Any | None]:
        with self._lock:
            if not self._is_opened:
                return 0, None
            return self._frame_id, self._latest_frame

    # Đọc khung hình hiện tại (tương thích ngược, chờ ngắn nếu khung hình đầu chưa về)
    def read_frame(self) -> tuple[bool, Any | None]:
        with self._lock:
            if not self._is_opened or self._stream_failed or self._session is None:
                return False, None
            if self._latest_frame is not None:
                return True, self._latest_frame
            first_frame_event = self._session.first_frame_event

        # Chờ bên ngoài khóa để luồng nền cập nhật khung hình đầu tiên hoặc báo lỗi
        first_frame_event.wait(timeout=DEFAULT_FIRST_FRAME_TIMEOUT_SECONDS)

        with self._lock:
            if not self._is_opened or self._stream_failed or self._latest_frame is None:
                return False, None
            return True, self._latest_frame

    # Dừng luồng đọc nền và giải phóng tài nguyên camera an toàn
    def release(self, wait_timeout: float = DEFAULT_RELEASE_JOIN_TIMEOUT_SECONDS) -> None:
        with self._lock:
            session = self._session
            self._session = None
            self._is_opened = False
            self._latest_frame = None
            self._frame_id = 0
            self._stream_failed = False

        if session is None:
            return

        session.stop_event.set()
        worker_thread = session.thread

        # Chế độ không chặn (dùng từ UI): đẩy việc chờ và dọn dẹp sang luồng daemon
        if wait_timeout <= 0:
            def cleanup_in_background() -> None:
                if worker_thread is not None:
                    worker_thread.join(timeout=DEFAULT_RELEASE_JOIN_TIMEOUT_SECONDS)
                if worker_thread is None or not worker_thread.is_alive():
                    _release_session_capture(session)

            threading.Thread(target=cleanup_in_background, daemon=True).start()
            return

        # Chế độ có chờ: đợi luồng nền dừng trong giới hạn rồi giải phóng ngay nếu đã dừng
        if worker_thread is not None:
            worker_thread.join(timeout=wait_timeout)

        if worker_thread is None or not worker_thread.is_alive():
            _release_session_capture(session)
