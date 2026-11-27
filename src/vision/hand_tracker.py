# Module nhận diện bàn tay MediaPipe HandLandmarker, đếm ngón tay, vẽ khung xương và tính FPS

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

from src.config.settings import DEFAULT_HAND_MODEL_PATH

# Số lượng điểm mốc chuẩn của một bàn tay trong MediaPipe
HAND_LANDMARK_COUNT = 21

# Các cặp chỉ số (đầu ngón, khớp giữa) của 4 ngón trỏ, giữa, áp út và út
NON_THUMB_FINGER_INDICES = (
    (8, 6),
    (12, 10),
    (16, 14),
    (20, 18),
)

# Ngưỡng tích vô hướng chuẩn hóa để xác định ngón cái đang giơ
THUMB_EXTENDED_DOT_RATIO = 0.08

# Danh sách 21 đoạn nối khung xương bàn tay lấy từ MediaPipe Tasks
HAND_CONNECTIONS: tuple[tuple[int, int], ...] = tuple(
    (connection.start, connection.end)
    for connection in vision.HandLandmarksConnections.HAND_CONNECTIONS
)

# Kiểu tọa độ 3D chuẩn hóa (x, y, z) cho từng điểm mốc bàn tay
LandmarkPoint = tuple[float, float, float]


# Dữ liệu kết quả nhận diện một bàn tay để tái sử dụng cho GUI và bước thu thập T004
@dataclass(frozen=True)
class HandDetection:
    handedness: str
    score: float
    landmarks: list[LandmarkPoint]
    finger_count: int


# Bộ đếm FPS làm mượt bằng trung bình trượt hàm mũ (EMA)
class FpsCounter:
    # Khởi tạo hệ số làm mượt và hàm đo thời gian
    def __init__(
        self,
        smoothing: float = 0.2,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if not 0.0 < smoothing <= 1.0:
            raise ValueError("smoothing phải nằm trong khoảng (0, 1].")
        self._smoothing = smoothing
        self._clock = clock if clock is not None else time.monotonic
        self._last_timestamp: float | None = None
        self._fps: float = 0.0

    # Trả về giá trị FPS đã làm mượt hiện tại
    @property
    def fps(self) -> float:
        return self._fps

    # Đặt lại trạng thái đo FPS khi bật hoặc tắt camera
    def reset(self) -> None:
        self._last_timestamp = None
        self._fps = 0.0

    # Ghi nhận một khung hình mới và cập nhật giá trị FPS
    def tick(self) -> float:
        now = self._clock()
        if self._last_timestamp is None:
            self._last_timestamp = now
            return self._fps

        delta = now - self._last_timestamp
        self._last_timestamp = now

        # Bỏ qua mẫu thời gian không dương để tránh chia cho 0
        if delta <= 0.0:
            return self._fps

        instant_fps = 1.0 / delta
        if self._fps == 0.0:
            self._fps = instant_fps
        else:
            self._fps = (
                self._smoothing * instant_fps + (1.0 - self._smoothing) * self._fps
            )
        return self._fps


# Đếm số ngón tay đang giơ (0-5) từ 21 tọa độ landmark chuẩn hóa
def count_extended_fingers(
    landmarks: Sequence[LandmarkPoint],
    handedness: str = "Right",
) -> int:
    if len(landmarks) != HAND_LANDMARK_COUNT:
        raise ValueError(
            f"Cần đúng {HAND_LANDMARK_COUNT} điểm landmark, nhận được {len(landmarks)}."
        )

    _ = handedness
    extended_count = 0

    # Đếm 4 ngón (trỏ, giữa, áp út, út) bằng cách so sánh tọa độ y của đầu ngón với khớp PIP
    for tip_index, pip_index in NON_THUMB_FINGER_INDICES:
        tip_y = landmarks[tip_index][1]
        pip_y = landmarks[pip_index][1]
        if tip_y < pip_y:
            extended_count += 1

    # Xác định ngón cái đang giơ bằng tích vô hướng 2D chuẩn hóa theo độ rộng lòng bàn tay
    thumb_tip = landmarks[4]
    thumb_ip = landmarks[3]
    index_mcp = landmarks[5]
    pinky_mcp = landmarks[17]

    palm_dx = index_mcp[0] - pinky_mcp[0]
    palm_dy = index_mcp[1] - pinky_mcp[1]
    palm_norm_sq = palm_dx * palm_dx + palm_dy * palm_dy

    if palm_norm_sq > 1e-8:
        thumb_dx = thumb_tip[0] - thumb_ip[0]
        thumb_dy = thumb_tip[1] - thumb_ip[1]
        dot_product = thumb_dx * palm_dx + thumb_dy * palm_dy
        if dot_product > THUMB_EXTENDED_DOT_RATIO * palm_norm_sq:
            extended_count += 1

    return extended_count


# Chuẩn hóa nhãn tay trái/phải theo trạng thái lật gương của ảnh đầu vào
def normalize_handedness(raw_label: str, is_mirrored: bool) -> str:
    cleaned = raw_label.strip()
    if cleaned not in ("Left", "Right"):
        return "Unknown"

    # MediaPipe giả định ảnh selfie đã lật gương; đảo nhãn nếu ảnh không lật gương
    if is_mirrored:
        return cleaned
    return "Right" if cleaned == "Left" else "Left"


# Vẽ 21 landmark, khung xương, nhãn tay/số ngón và FPS lên bản sao khung hình BGR
def draw_hand_landmarks(
    frame_bgr: np.ndarray,
    detections: Sequence[HandDetection],
    fps: float | None = None,
) -> np.ndarray:
    annotated = frame_bgr.copy()
    height, width = annotated.shape[:2]

    if width <= 0 or height <= 0:
        return annotated

    # Vẽ từng bàn tay gồm các đoạn nối xương, điểm mốc và nhãn ASCII
    for detection in detections:
        pixel_points: list[tuple[int, int]] = []
        for x_norm, y_norm, _z_norm in detection.landmarks:
            px = int(round(x_norm * width))
            py = int(round(y_norm * height))
            clamped_x = min(max(px, 0), width - 1)
            clamped_y = min(max(py, 0), height - 1)
            pixel_points.append((clamped_x, clamped_y))

        if len(pixel_points) == HAND_LANDMARK_COUNT:
            for start_idx, end_idx in HAND_CONNECTIONS:
                cv2.line(
                    annotated,
                    pixel_points[start_idx],
                    pixel_points[end_idx],
                    (0, 220, 120),
                    2,
                    cv2.LINE_AA,
                )

            for point in pixel_points:
                cv2.circle(annotated, point, 4, (255, 255, 255), -1, cv2.LINE_AA)
                cv2.circle(annotated, point, 4, (0, 120, 255), 1, cv2.LINE_AA)

            min_x = min(point[0] for point in pixel_points)
            min_y = min(point[1] for point in pixel_points)
            label_text = f"{detection.handedness}: {detection.finger_count}"
            text_y = max(24, min_y - 10)
            cv2.putText(
                annotated,
                label_text,
                (min_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )

    # Hiển thị FPS ở góc trên trái nếu được cung cấp
    if fps is not None:
        fps_text = f"FPS: {fps:.1f}"
        cv2.putText(
            annotated,
            fps_text,
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (50, 255, 50),
            2,
            cv2.LINE_AA,
        )

    return annotated


# Lớp bọc MediaPipe HandLandmarker ở chế độ VIDEO để trích xuất bàn tay theo thời gian thực
class HandTracker:
    # Nạp file model từ bộ nhớ đệm và khởi tạo HandLandmarker
    def __init__(
        self,
        model_path: str | Path = DEFAULT_HAND_MODEL_PATH,
        max_num_hands: int = 2,
        min_hand_detection_confidence: float = 0.5,
        min_hand_presence_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        landmarker: vision.HandLandmarker | None = None,
        clock_ms: Callable[[], int] | None = None,
    ) -> None:
        self._model_path = Path(model_path)
        self._clock_ms = (
            clock_ms
            if clock_ms is not None
            else lambda: time.monotonic_ns() // 1_000_000
        )
        self._last_timestamp_ms = 0

        # Cho phép truyền landmarker giả lập khi viết unit test
        if landmarker is not None:
            self._landmarker: vision.HandLandmarker | None = landmarker
            return

        if not self._model_path.is_file():
            raise FileNotFoundError(
                f"Không tìm thấy file model MediaPipe tại '{self._model_path}'. "
                "Hãy chạy lệnh: .venv\\Scripts\\python scripts\\download_hand_model.py"
            )

        # Đọc bytes trực tiếp để tránh lỗi đường dẫn Unicode trên Windows
        model_bytes = self._model_path.read_bytes()
        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_buffer=model_bytes),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_hand_detection_confidence,
            min_hand_presence_confidence=min_hand_presence_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

    # Phát hiện bàn tay trên khung hình BGR và trả về danh sách HandDetection chuẩn hóa
    def process(
        self,
        frame_bgr: np.ndarray,
        is_mirrored: bool = True,
    ) -> list[HandDetection]:
        if self._landmarker is None:
            return []

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        contiguous_rgb = np.ascontiguousarray(frame_rgb)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=contiguous_rgb)

        # Đảm bảo timestamp_ms luôn tăng nghiêm ngặt cho detect_for_video
        candidate_ms = int(self._clock_ms())
        timestamp_ms = max(candidate_ms, self._last_timestamp_ms + 1)
        self._last_timestamp_ms = timestamp_ms

        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        return self._parse_result(result, is_mirrored=is_mirrored)

    # Chuyển kết quả thô của MediaPipe sang danh sách HandDetection sạch
    def _parse_result(
        self,
        result: vision.HandLandmarkerResult,
        is_mirrored: bool,
    ) -> list[HandDetection]:
        detections: list[HandDetection] = []
        hand_landmarks_list = result.hand_landmarks or []
        handedness_list = result.handedness or []

        for index, raw_landmarks in enumerate(hand_landmarks_list):
            if len(raw_landmarks) != HAND_LANDMARK_COUNT:
                continue

            normalized_landmarks: list[LandmarkPoint] = [
                (float(point.x), float(point.y), float(point.z))
                for point in raw_landmarks
            ]

            raw_label = "Unknown"
            score = 0.0
            if index < len(handedness_list) and handedness_list[index]:
                top_category = handedness_list[index][0]
                raw_label = str(top_category.category_name or "Unknown")
                score = float(top_category.score or 0.0)

            handedness = normalize_handedness(raw_label, is_mirrored=is_mirrored)
            finger_count = count_extended_fingers(normalized_landmarks, handedness)

            detections.append(
                HandDetection(
                    handedness=handedness,
                    score=score,
                    landmarks=normalized_landmarks,
                    finger_count=finger_count,
                )
            )

        return detections

    # Giải phóng tài nguyên HandLandmarker an toàn
    def close(self) -> None:
        if self._landmarker is not None:
            self._landmarker.close()
            self._landmarker = None
