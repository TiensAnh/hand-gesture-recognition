# Kiểm thử trích xuất và chuẩn hóa vector đặc trưng 42 chiều cho bàn tay

import math

import numpy as np
import pytest

from src.ml.features import FEATURE_VECTOR_SIZE, GESTURE_LABELS, extract_landmark_features


# Tạo tập 21 điểm mốc mẫu có hình dạng bàn tay đơn giản để kiểm thử
def _make_sample_landmarks() -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    for index in range(21):
        x_coord = 0.2 + index * 0.02
        y_coord = 0.7 - (index % 5) * 0.05 - (index // 5) * 0.03
        z_coord = -0.01 * index
        points.append((x_coord, y_coord, z_coord))
    return points


# Kiểm tra danh sách nhãn mặc định có đủ 7 cử chỉ không trùng lặp
def test_gesture_labels_has_seven_unique_entries() -> None:
    assert len(GESTURE_LABELS) == 7
    assert len(set(GESTURE_LABELS)) == 7


# Kiểm tra hình dạng, kiểu dữ liệu và giá trị chuẩn hóa của vector 42 chiều
def test_extract_landmark_features_shape_dtype_and_normalization() -> None:
    landmarks = _make_sample_landmarks()
    vector = extract_landmark_features(landmarks)

    assert vector.shape == (FEATURE_VECTOR_SIZE,)
    assert vector.dtype == np.float32
    assert vector[0] == 0.0
    assert vector[1] == 0.0
    assert np.isclose(np.max(np.abs(vector)), 1.0, atol=1e-6)


# Kiểm tra hỗ trợ đầu vào chỉ gồm 2 tọa độ (x, y) cho mỗi điểm mốc
def test_extract_landmark_features_accepts_2d_points() -> None:
    landmarks_3d = _make_sample_landmarks()
    landmarks_2d = [(x, y) for x, y, _z in landmarks_3d]

    vec_3d = extract_landmark_features(landmarks_3d)
    vec_2d = extract_landmark_features(landmarks_2d)

    assert np.allclose(vec_3d, vec_2d, atol=1e-6)


# Kiểm tra tính bất biến tịnh tiến khi dịch chuyển toàn bộ bàn tay
def test_extract_landmark_features_translation_invariant() -> None:
    base_landmarks = _make_sample_landmarks()
    shifted_landmarks = [(x + 0.35, y - 0.42, z + 0.1) for x, y, z in base_landmarks]

    base_vec = extract_landmark_features(base_landmarks)
    shifted_vec = extract_landmark_features(shifted_landmarks)

    assert np.allclose(base_vec, shifted_vec, atol=1e-6)


# Kiểm tra tính bất biến tỉ lệ khi phóng to hoặc thu nhỏ bàn tay
def test_extract_landmark_features_scale_invariant() -> None:
    base_landmarks = _make_sample_landmarks()
    scaled_landmarks = [(x * 2.75, y * 2.75, z * 2.75) for x, y, z in base_landmarks]

    base_vec = extract_landmark_features(base_landmarks)
    scaled_vec = extract_landmark_features(scaled_landmarks)

    assert np.allclose(base_vec, scaled_vec, atol=1e-6)


# Kiểm tra bất biến khi kết hợp đồng thời tịnh tiến và thay đổi tỉ lệ
def test_extract_landmark_features_combined_translation_and_scale_invariant() -> None:
    base_landmarks = _make_sample_landmarks()
    transformed = [(x * 0.45 + 0.28, y * 0.45 - 0.17, z) for x, y, z in base_landmarks]

    base_vec = extract_landmark_features(base_landmarks)
    transformed_vec = extract_landmark_features(transformed)

    assert np.allclose(base_vec, transformed_vec, atol=1e-6)


# Kiểm tra trả về vector toàn 0.0 khi toàn bộ 21 điểm trùng nhau (max_norm == 0)
def test_extract_landmark_features_degenerate_returns_zeros() -> None:
    collapsed_landmarks = [(0.5, 0.5, 0.0)] * 21
    vector = extract_landmark_features(collapsed_landmarks)

    assert vector.shape == (FEATURE_VECTOR_SIZE,)
    assert vector.dtype == np.float32
    assert np.array_equal(vector, np.zeros(FEATURE_VECTOR_SIZE, dtype=np.float32))


# Kiểm tra báo lỗi khi số lượng điểm mốc khác 21
def test_extract_landmark_features_rejects_wrong_landmark_count() -> None:
    with pytest.raises(ValueError, match="21"):
        extract_landmark_features([(0.0, 0.0, 0.0)] * 20)


# Kiểm tra báo lỗi khi điểm mốc thiếu tọa độ (x, y)
def test_extract_landmark_features_rejects_short_point() -> None:
    invalid_landmarks: list[tuple[float, ...]] = [(0.1, 0.2)] * 20 + [(0.3,)]
    with pytest.raises(ValueError, match="2 tọa độ"):
        extract_landmark_features(invalid_landmarks)


# Kiểm tra báo lỗi khi tọa độ chứa NaN hoặc Inf
@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
def test_extract_landmark_features_rejects_non_finite_values(bad_value: float) -> None:
    landmarks = _make_sample_landmarks()
    landmarks[5] = (bad_value, 0.4, 0.0)

    with pytest.raises(ValueError, match="không hữu hạn"):
        extract_landmark_features(landmarks)
