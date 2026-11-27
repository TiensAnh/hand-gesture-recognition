# Kiểm thử đơn vị cho module nhận diện bàn tay, đếm ngón tay, vẽ khung xương và FPS

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from src.vision.hand_tracker import (
    HAND_LANDMARK_COUNT,
    FpsCounter,
    HandDetection,
    HandTracker,
    LandmarkPoint,
    count_extended_fingers,
    draw_hand_landmarks,
    normalize_handedness,
)


# Tạo bộ 21 landmark mẫu cho tay trái hoặc tay phải theo trạng thái từng ngón và tỉ lệ kích thước
def _build_hand_landmarks(
    handedness: str = "Right",
    thumb: bool = False,
    index: bool = False,
    middle: bool = False,
    ring: bool = False,
    pinky: bool = False,
    scale: float = 1.0,
) -> list[LandmarkPoint]:
    center_x = 0.5
    center_y = 0.6

    # Chuyển tọa độ cục bộ sang tọa độ chuẩn hóa trong khung hình
    def pt(dx: float, dy: float) -> LandmarkPoint:
        return (center_x + dx * scale, center_y + dy * scale, 0.0)

    # Trong ảnh selfie: tay phải có khớp ngón trỏ (5) nằm bên trái khớp ngón út (17)
    side = -1.0 if handedness == "Right" else 1.0

    landmarks: list[LandmarkPoint] = [pt(0.0, 0.25) for _ in range(HAND_LANDMARK_COUNT)]

    # Cổ tay (0) và các khớp ngón cái (1..4)
    landmarks[0] = pt(0.0, 0.25)
    landmarks[1] = pt(side * 0.08, 0.16)
    landmarks[2] = pt(side * 0.13, 0.08)
    landmarks[3] = pt(side * 0.17, 0.02)
    landmarks[4] = pt(side * (0.24 if thumb else 0.12), -0.02 if thumb else 0.04)

    # Khớp và đầu 4 ngón còn lại (trỏ, giữa, áp út, út)
    finger_specs = (
        (5, 6, 7, 8, side * 0.10, index),
        (9, 10, 11, 12, side * 0.03, middle),
        (13, 14, 15, 16, -side * 0.04, ring),
        (17, 18, 19, 20, -side * 0.11, pinky),
    )
    for mcp_idx, pip_idx, dip_idx, tip_idx, x_offset, is_extended in finger_specs:
        landmarks[mcp_idx] = pt(x_offset, 0.0)
        landmarks[pip_idx] = pt(x_offset, -0.10)
        if is_extended:
            landmarks[dip_idx] = pt(x_offset, -0.18)
            landmarks[tip_idx] = pt(x_offset, -0.26)
        else:
            landmarks[dip_idx] = pt(x_offset, -0.04)
            landmarks[tip_idx] = pt(x_offset, 0.04)

    return landmarks


# Kiểm tra đếm chính xác 0 đến 5 ngón tay cho cả tay phải và tay trái
@pytest.mark.parametrize("handedness", ["Right", "Left"])
@pytest.mark.parametrize(
    ("finger_flags", "expected_count"),
    [
        ((False, False, False, False, False), 0),
        ((True, False, False, False, False), 1),
        ((False, True, False, False, False), 1),
        ((False, True, True, False, False), 2),
        ((True, True, True, False, False), 3),
        ((False, True, True, True, True), 4),
        ((True, True, True, True, True), 5),
    ],
)
def test_count_extended_fingers_all_counts(
    handedness: str,
    finger_flags: tuple[bool, bool, bool, bool, bool],
    expected_count: int,
) -> None:
    thumb, index, middle, ring, pinky = finger_flags
    landmarks = _build_hand_landmarks(
        handedness=handedness,
        thumb=thumb,
        index=index,
        middle=middle,
        ring=ring,
        pinky=pinky,
    )

    assert count_extended_fingers(landmarks, handedness=handedness) == expected_count


# Kiểm tra công thức chuẩn hóa ngón cái vẫn đếm đúng khi bàn tay nhỏ ở xa camera
def test_count_extended_fingers_scale_invariance() -> None:
    small_open_hand = _build_hand_landmarks(
        handedness="Right",
        thumb=True,
        index=True,
        middle=True,
        ring=True,
        pinky=True,
        scale=0.15,
    )
    small_fist = _build_hand_landmarks(handedness="Left", scale=0.15)

    assert count_extended_fingers(small_open_hand, handedness="Right") == 5
    assert count_extended_fingers(small_fist, handedness="Left") == 0


# Kiểm tra guard khi độ rộng lòng bàn tay bằng 0 không gây lỗi toán học
def test_count_extended_fingers_degenerate_palm_guard() -> None:
    collapsed = [(0.5, 0.5, 0.0) for _ in range(HAND_LANDMARK_COUNT)]

    assert count_extended_fingers(collapsed, handedness="Right") == 0


# Kiểm tra báo lỗi rõ khi số lượng điểm landmark khác 21
def test_count_extended_fingers_invalid_length() -> None:
    with pytest.raises(ValueError):
        count_extended_fingers([(0.0, 0.0, 0.0)] * 10)


# Kiểm tra chuẩn hóa nhãn Left/Right theo trạng thái lật gương
def test_normalize_handedness() -> None:
    assert normalize_handedness("Left", is_mirrored=True) == "Left"
    assert normalize_handedness("Right", is_mirrored=True) == "Right"
    assert normalize_handedness("Left", is_mirrored=False) == "Right"
    assert normalize_handedness("Right", is_mirrored=False) == "Left"
    assert normalize_handedness("Other", is_mirrored=True) == "Unknown"


# Kiểm tra bộ đếm FPS làm mượt EMA và hàm reset()
def test_fps_counter_ema_and_reset() -> None:
    timestamps = iter([10.0, 10.05, 10.10, 20.0, 20.025])
    counter = FpsCounter(smoothing=0.5, clock=lambda: next(timestamps))

    assert counter.tick() == 0.0
    assert counter.tick() == pytest.approx(20.0)
    assert counter.tick() == pytest.approx(20.0)

    counter.reset()
    assert counter.fps == 0.0
    assert counter.tick() == 0.0
    assert counter.tick() == pytest.approx(40.0)


# Kiểm tra vẽ landmark trả về bản sao mới, vẽ đúng lên ảnh và clamp tọa độ ngoài biên
def test_draw_hand_landmarks_clamps_and_does_not_mutate() -> None:
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    landmarks = _build_hand_landmarks(handedness="Right", thumb=True, index=True)
    # Cố tình đặt một điểm vượt biên [0, 1] để kiểm tra cơ chế clamp
    landmarks[0] = (-0.2, 1.3, 0.0)
    detection = HandDetection(
        handedness="Right",
        score=0.95,
        landmarks=landmarks,
        finger_count=2,
    )

    annotated = draw_hand_landmarks(frame, [detection], fps=24.5)

    assert annotated is not frame
    assert np.all(frame == 0)
    assert int(annotated.sum()) > 0


# Kiểm tra HandTracker ném FileNotFoundError kèm hướng dẫn khi thiếu file model
def test_hand_tracker_missing_model_raises(tmp_path: Path) -> None:
    missing_model = tmp_path / "missing_hand_landmarker.task"

    with pytest.raises(FileNotFoundError, match="download_hand_model.py"):
        HandTracker(model_path=missing_model)


# Lớp giả lập HandLandmarker để kiểm thử luồng process() và close() không cần file .task thật
class _FakeLandmarker:
    # Khởi tạo kết quả giả lập và danh sách ghi nhận timestamp_ms
    def __init__(self, landmarks: list[LandmarkPoint], raw_label: str) -> None:
        self._landmarks = landmarks
        self._raw_label = raw_label
        self.timestamps: list[int] = []
        self.closed = False

    # Trả về kết quả nhận diện giả lập với cấu trúc tương tự HandLandmarkerResult
    def detect_for_video(self, _mp_image: object, timestamp_ms: int) -> SimpleNamespace:
        self.timestamps.append(timestamp_ms)
        mp_landmarks = [
            SimpleNamespace(x=point[0], y=point[1], z=point[2])
            for point in self._landmarks
        ]
        category = SimpleNamespace(category_name=self._raw_label, score=0.92)
        return SimpleNamespace(
            hand_landmarks=[mp_landmarks],
            handedness=[[category]],
        )

    # Đánh dấu đã giải phóng tài nguyên
    def close(self) -> None:
        self.closed = True


# Kiểm tra HandTracker ép timestamp_ms tăng nghiêm ngặt, đảo nhãn tay và close()
def test_hand_tracker_process_timestamp_and_handedness() -> None:
    sample_landmarks = _build_hand_landmarks(
        handedness="Right",
        thumb=True,
        index=True,
        middle=True,
    )
    fake_landmarker = _FakeLandmarker(sample_landmarks, raw_label="Right")
    # Cố tình trả đồng hồ đứng yên rồi giảm để kiểm tra cơ chế ép tăng nghiêm ngặt
    clock_values = iter([1000, 1000, 995])
    tracker = HandTracker(
        landmarker=fake_landmarker,  # type: ignore[arg-type]
        clock_ms=lambda: next(clock_values),
    )
    dummy_frame = np.zeros((64, 64, 3), dtype=np.uint8)

    detections_mirrored = tracker.process(dummy_frame, is_mirrored=True)
    detections_unmirrored = tracker.process(dummy_frame, is_mirrored=False)
    tracker.process(dummy_frame, is_mirrored=True)

    assert len(detections_mirrored) == 1
    assert detections_mirrored[0].handedness == "Right"
    assert detections_mirrored[0].finger_count == 3
    assert len(detections_mirrored[0].landmarks) == HAND_LANDMARK_COUNT
    assert detections_unmirrored[0].handedness == "Left"
    assert fake_landmarker.timestamps == [1000, 1001, 1002]

    tracker.close()
    assert fake_landmarker.closed is True
    assert tracker.process(dummy_frame) == []
