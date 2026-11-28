# Trích xuất và chuẩn hóa vector đặc trưng 42 chiều từ 21 điểm mốc bàn tay MediaPipe

from collections.abc import Sequence

import numpy as np

from src.vision.hand_tracker import HAND_LANDMARK_COUNT

# Danh sách 7 nhãn cử chỉ chuẩn của dự án (khớp thứ tự phím tắt 1-7)
GESTURE_LABELS: tuple[str, ...] = (
    "fist",
    "open_palm",
    "point",
    "peace",
    "ok",
    "thumbs_up",
    "rock",
)

# Kích thước cố định của vector đặc trưng (21 điểm x 2 tọa độ x, y)
FEATURE_VECTOR_SIZE = HAND_LANDMARK_COUNT * 2

# Ngưỡng chuẩn hóa tối thiểu để tránh chia cho 0 khi các điểm trùng nhau
ZERO_NORM_EPSILON = 1e-12


# Trích xuất vector 42 chiều bất biến tịnh tiến và tỉ lệ từ 21 điểm mốc bàn tay
def extract_landmark_features(
    landmarks: Sequence[Sequence[float]],
) -> np.ndarray:
    if len(landmarks) != HAND_LANDMARK_COUNT:
        raise ValueError(
            f"Cần đúng {HAND_LANDMARK_COUNT} điểm landmark, nhận được {len(landmarks)}."
        )

    # Kiểm tra từng điểm có đủ tọa độ (x, y) và mọi giá trị đều hữu hạn
    xy_points: list[tuple[float, float]] = []
    for index, point in enumerate(landmarks):
        if len(point) < 2:
            raise ValueError(
                f"Điểm landmark tại vị trí {index} phải có ít nhất 2 tọa độ (x, y)."
            )
        coord_x = float(point[0])
        coord_y = float(point[1])
        if not (np.isfinite(coord_x) and np.isfinite(coord_y)):
            raise ValueError(
                f"Điểm landmark tại vị trí {index} chứa giá trị không hữu hạn (NaN/Inf)."
            )
        xy_points.append((coord_x, coord_y))

    # Dịch hệ trục tọa độ về gốc cổ tay (điểm mốc 0) và trải phẳng xen kẽ x0, y0, ..., x20, y20
    origin_x, origin_y = xy_points[0]
    relative_values: list[float] = []
    for coord_x, coord_y in xy_points:
        relative_values.append(coord_x - origin_x)
        relative_values.append(coord_y - origin_y)

    relative_array = np.asarray(relative_values, dtype=np.float64)

    # Chuẩn hóa theo giá trị tuyệt đối lớn nhất trong 42 thành phần
    max_abs = float(np.max(np.abs(relative_array)))
    if max_abs <= ZERO_NORM_EPSILON:
        return np.zeros(FEATURE_VECTOR_SIZE, dtype=np.float32)

    normalized_array = (relative_array / max_abs).astype(np.float32)
    return normalized_array
