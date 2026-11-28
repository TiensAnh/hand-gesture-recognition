# Kiểm thử chọn bàn tay chính và bộ điều khiển trạng thái thu thập dữ liệu

import pytest

from src.ml.collector import CollectionController, select_primary_detection
from src.ml.features import FEATURE_VECTOR_SIZE, GESTURE_LABELS
from src.vision.hand_tracker import HandDetection


# Tạo một HandDetection giả lập với bounding box xác định theo vị trí và kích thước
def _make_detection(
    origin_x: float,
    origin_y: float,
    width: float,
    height: float,
    score: float = 0.9,
) -> HandDetection:
    landmarks: list[tuple[float, float, float]] = []
    for index in range(21):
        ratio_x = (index % 5) / 4.0
        ratio_y = (index // 5) / 4.0
        landmarks.append((origin_x + ratio_x * width, origin_y + ratio_y * height, 0.0))

    return HandDetection(
        handedness="Right",
        score=score,
        landmarks=landmarks,
        finger_count=5,
    )


# Đồng hồ giả lập cho phép kiểm thử điều kiện giãn cách thời gian không cần sleep
class _FakeClock:
    def __init__(self, initial: float = 10.0) -> None:
        self.now = initial

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


# Kiểm tra select_primary_detection trả về None khi danh sách rỗng
def test_select_primary_detection_returns_none_when_empty() -> None:
    assert select_primary_detection([]) is None


# Kiểm tra chọn bàn tay có diện tích bounding box lớn nhất
def test_select_primary_detection_prefers_largest_bounding_box() -> None:
    small_hand = _make_detection(0.1, 0.1, width=0.1, height=0.1, score=0.99)
    large_hand = _make_detection(0.2, 0.2, width=0.35, height=0.4, score=0.75)

    primary = select_primary_detection([small_hand, large_hand])
    assert primary is large_hand


# Kiểm tra phá hòa theo score cao nhất khi diện tích bounding box bằng nhau
def test_select_primary_detection_tiebreaks_by_score() -> None:
    lower_score = _make_detection(0.1, 0.1, width=0.2, height=0.2, score=0.81)
    higher_score = _make_detection(0.5, 0.5, width=0.2, height=0.2, score=0.94)

    primary = select_primary_detection([lower_score, higher_score])
    assert primary is higher_score


# Kiểm tra validate tham số khởi tạo của CollectionController
def test_collection_controller_validates_init_arguments() -> None:
    with pytest.raises(ValueError):
        CollectionController(labels=())

    with pytest.raises(ValueError):
        CollectionController(capture_interval_seconds=0.0)

    with pytest.raises(ValueError):
        CollectionController(capture_interval_seconds=-0.5)


# Kiểm tra chuyển nhãn theo chỉ số và bật/tắt chế độ ghi tự động
def test_collection_controller_label_selection_and_auto_toggle() -> None:
    controller = CollectionController(labels=GESTURE_LABELS)
    assert controller.current_label == "fist"
    assert controller.auto_capture is False

    assert controller.select_label_by_index(3) is True
    assert controller.current_label == "peace"
    assert controller.select_label_by_index(99) is False
    assert controller.select_label_by_index(-1) is False
    assert controller.current_label == "peace"

    assert controller.toggle_auto_capture() is True
    assert controller.auto_capture is True
    controller.set_auto_capture(False)
    assert controller.auto_capture is False


# Kiểm tra chụp thủ công không bị chặn bởi interval nhưng vẫn chặn trùng frame_id
def test_manual_capture_ignores_interval_but_deduplicates_frame_id() -> None:
    clock = _FakeClock(100.0)
    controller = CollectionController(capture_interval_seconds=0.5, clock=clock)
    detection = _make_detection(0.2, 0.2, width=0.3, height=0.3)

    # Ở chế độ thủ công, manual=False sẽ không chụp
    assert controller.try_capture(frame_id=1, detections=[detection], manual=False) is None

    # Chụp thủ công frame 1 thành công
    first_result = controller.try_capture(frame_id=1, detections=[detection], manual=True)
    assert first_result is not None
    label_1, vec_1 = first_result
    assert label_1 == "fist"
    assert vec_1.shape == (FEATURE_VECTOR_SIZE,)

    # Bấm Space lần nữa trên cùng frame_id=1 bị từ chối
    assert controller.try_capture(frame_id=1, detections=[detection], manual=True) is None

    # Chụp thủ công frame 2 ngay sau 0.01s (< interval 0.5s) vẫn thành công
    clock.advance(0.01)
    second_result = controller.try_capture(frame_id=2, detections=[detection], manual=True)
    assert second_result is not None
    assert controller.last_captured_frame_id == 2


# Kiểm tra chế độ tự động tuân thủ giãn cách thời gian và lọc frame_id không hợp lệ
def test_auto_capture_respects_interval_and_frame_id() -> None:
    clock = _FakeClock(50.0)
    controller = CollectionController(capture_interval_seconds=0.2, clock=clock)
    controller.set_auto_capture(True)
    detection = _make_detection(0.1, 0.1, width=0.25, height=0.25)

    # frame_id <= 0 bị bỏ qua
    assert controller.try_capture(frame_id=0, detections=[detection]) is None
    assert controller.try_capture(frame_id=-3, detections=[detection]) is None

    # Frame đầu tiên hợp lệ được chụp ngay
    assert controller.try_capture(frame_id=1, detections=[detection]) is not None

    # Chưa đủ 0.2s dù frame_id mới -> bỏ qua
    clock.advance(0.1)
    assert controller.try_capture(frame_id=2, detections=[detection]) is None

    # Đủ 0.2s nhưng vẫn là frame_id đã chụp -> bỏ qua
    clock.advance(0.15)
    assert controller.try_capture(frame_id=1, detections=[detection]) is None

    # Đủ 0.2s và có frame_id mới -> chụp thành công
    result = controller.try_capture(frame_id=3, detections=[detection])
    assert result is not None
    assert controller.last_captured_frame_id == 3


# Kiểm tra từ chối khi không có bàn tay hoặc mẫu suy biến toàn 0.0
def test_try_capture_rejects_empty_detections_and_degenerate_hand() -> None:
    clock = _FakeClock(0.0)
    controller = CollectionController(clock=clock)
    degenerate_hand = _make_detection(0.5, 0.5, width=0.0, height=0.0)

    assert controller.try_capture(frame_id=1, detections=[], manual=True) is None
    assert controller.try_capture(frame_id=2, detections=[degenerate_hand], manual=True) is None
    assert controller.last_captured_frame_id is None
