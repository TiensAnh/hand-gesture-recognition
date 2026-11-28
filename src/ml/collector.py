# Logic điều phối chọn bàn tay chính, nhãn đang thu và điều kiện chụp mẫu dữ liệu

import time
from collections.abc import Callable, Sequence

import numpy as np

from src.ml.features import GESTURE_LABELS, extract_landmark_features
from src.vision.hand_tracker import HandDetection


# Tính diện tích hộp bao chuẩn hóa (bounding box) từ danh sách điểm mốc bàn tay
def _compute_bounding_box_area(detection: HandDetection) -> float:
    if not detection.landmarks:
        return 0.0

    xs = [point[0] for point in detection.landmarks]
    ys = [point[1] for point in detection.landmarks]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    return max(0.0, width) * max(0.0, height)


# Ngưỡng sai số dấu phẩy động khi so sánh diện tích bằng nhau để phá hòa theo score
AREA_TIE_EPSILON = 1e-9


# Chọn bàn tay chính có diện tích bounding box lớn nhất (phá hòa theo độ tin cậy score)
def select_primary_detection(
    detections: Sequence[HandDetection],
) -> HandDetection | None:
    if not detections:
        return None

    best_detection = detections[0]
    best_area = _compute_bounding_box_area(best_detection)

    # Ưu tiên bàn tay có diện tích lớn hơn rõ rệt; nếu xấp xỉ bằng nhau thì phá hòa theo score
    for candidate in detections[1:]:
        candidate_area = _compute_bounding_box_area(candidate)
        if candidate_area > best_area + AREA_TIE_EPSILON:
            best_detection = candidate
            best_area = candidate_area
        elif abs(candidate_area - best_area) <= AREA_TIE_EPSILON:
            if candidate.score > best_detection.score:
                best_detection = candidate
                best_area = candidate_area

    return best_detection


# Bộ điều khiển trạng thái thu thập dữ liệu cử chỉ (nhãn hiện tại, chụp đơn và tự động)
class CollectionController:
    # Khởi tạo danh sách nhãn, khoảng thời gian chụp liên tục và hàm đồng hồ
    def __init__(
        self,
        labels: Sequence[str] = GESTURE_LABELS,
        capture_interval_seconds: float = 0.2,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if not labels:
            raise ValueError("Danh sách nhãn thu thập không được rỗng.")
        if capture_interval_seconds <= 0:
            raise ValueError("capture_interval_seconds phải lớn hơn 0.")

        self._labels: tuple[str, ...] = tuple(labels)
        self._current_index: int = 0
        self._auto_capture: bool = False
        self._capture_interval_seconds: float = float(capture_interval_seconds)
        self._clock: Callable[[], float] = clock if clock is not None else time.monotonic
        self._last_captured_frame_id: int | None = None
        self._last_capture_time: float | None = None

    # Trả về danh sách các nhãn đang cấu hình
    @property
    def labels(self) -> tuple[str, ...]:
        return self._labels

    # Trả về chỉ số nhãn hiện tại (0-based)
    @property
    def current_index(self) -> int:
        return self._current_index

    # Trả về tên nhãn cử chỉ đang chọn
    @property
    def current_label(self) -> str:
        return self._labels[self._current_index]

    # Trả về trạng thái chế độ ghi mẫu liên tục
    @property
    def auto_capture(self) -> bool:
        return self._auto_capture

    # Trả về khoảng thời gian tối thiểu giữa 2 lần ghi tự động
    @property
    def capture_interval_seconds(self) -> float:
        return self._capture_interval_seconds

    # Trả về frame_id của khung hình gần nhất đã chụp thành công
    @property
    def last_captured_frame_id(self) -> int | None:
        return self._last_captured_frame_id

    # Đổi nhãn cử chỉ hiện tại theo chỉ số (0-based)
    def select_label_by_index(self, index: int) -> bool:
        if 0 <= index < len(self._labels):
            self._current_index = index
            return True
        return False

    # Bật hoặc tắt chế độ ghi mẫu liên tục
    def toggle_auto_capture(self) -> bool:
        self._auto_capture = not self._auto_capture
        return self._auto_capture

    # Đặt trực tiếp trạng thái chế độ ghi mẫu liên tục
    def set_auto_capture(self, enabled: bool) -> None:
        self._auto_capture = bool(enabled)

    # Kiểm tra điều kiện và trích xuất mẫu (nhãn, vector 42 chiều) cho khung hình hiện tại
    def try_capture(
        self,
        frame_id: int,
        detections: Sequence[HandDetection],
        manual: bool = False,
    ) -> tuple[str, np.ndarray] | None:
        # Không chụp nếu đang ở chế độ thủ công mà không có yêu cầu chụp tay
        if not manual and not self._auto_capture:
            return None

        # Lọc bỏ frame chưa hợp lệ hoặc frame đã chụp trước đó
        if frame_id <= 0 or frame_id == self._last_captured_frame_id:
            return None

        now = float(self._clock())

        # Chế độ tự động phải tuân thủ giãn cách thời gian tối thiểu
        if not manual and self._last_capture_time is not None:
            elapsed = now - self._last_capture_time
            if elapsed < self._capture_interval_seconds:
                return None

        primary_detection = select_primary_detection(detections)
        if primary_detection is None:
            return None

        feature_vector = extract_landmark_features(primary_detection.landmarks)

        # Từ chối mẫu suy biến khi toàn bộ 42 thành phần đều bằng 0.0
        if not bool(np.any(feature_vector)):
            return None

        self._last_captured_frame_id = frame_id
        self._last_capture_time = now
        return self.current_label, feature_vector
