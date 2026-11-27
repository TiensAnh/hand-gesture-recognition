# Kiểm thử đơn vị cho module tiền xử lý khung hình OpenCV

import numpy as np
import pytest

from src.vision.preprocessing import PreprocessOptions, preprocess_frame


# Kiểm tra báo lỗi khi tham số bộ lọc không hợp lệ
@pytest.mark.parametrize("invalid_kernel", [0, -3, 2, 4])
def test_preprocess_options_invalid_blur_kernel(invalid_kernel: int) -> None:
    with pytest.raises(ValueError):
        PreprocessOptions(blur_kernel_size=invalid_kernel)


# Kiểm tra báo lỗi khi tham số CLAHE không hợp lệ
def test_preprocess_options_invalid_clahe_params() -> None:
    with pytest.raises(ValueError):
        PreprocessOptions(clahe_clip_limit=0.0)
    with pytest.raises(ValueError):
        PreprocessOptions(clahe_tile_grid_size=(0, 8))


# Kiểm tra tắt toàn bộ tùy chọn vẫn trả về bản sao độc lập với ảnh gốc
def test_preprocess_frame_returns_copy_when_all_disabled() -> None:
    original = np.arange(4 * 6 * 3, dtype=np.uint8).reshape((4, 6, 3))
    options = PreprocessOptions(
        flip_horizontal=False,
        enable_blur=False,
        enable_clahe=False,
    )

    result = preprocess_frame(original, options)

    assert result is not original
    assert np.array_equal(result, original)
    result[0, 0, 0] = 255
    assert original[0, 0, 0] == 0


# Kiểm tra lật gương theo trục ngang đảo chính xác thứ tự cột ảnh
def test_preprocess_frame_flip_horizontal() -> None:
    frame = np.zeros((10, 20, 3), dtype=np.uint8)
    frame[:, 0, :] = [10, 20, 30]
    frame[:, -1, :] = [200, 150, 100]

    result = preprocess_frame(frame, PreprocessOptions(flip_horizontal=True))

    assert np.array_equal(result[:, -1, :], frame[:, 0, :])
    assert np.array_equal(result[:, 0, :], frame[:, -1, :])


# Kiểm tra lọc nhiễu Gaussian làm dịu điểm nhiễu đơn lẻ và giữ nguyên kích thước ảnh
def test_preprocess_frame_gaussian_blur() -> None:
    frame = np.zeros((32, 32, 3), dtype=np.uint8)
    frame[16, 16, :] = 255

    result = preprocess_frame(
        frame,
        PreprocessOptions(flip_horizontal=False, enable_blur=True, blur_kernel_size=5),
    )

    assert result.shape == frame.shape
    assert result.dtype == np.uint8
    assert result[16, 16, 0] < 255
    assert result[16, 17, 0] > 0


# Kiểm tra cân bằng sáng CLAHE cải thiện tương phản ảnh tối và giữ nguyên shape/dtype
def test_preprocess_frame_clahe() -> None:
    gradient = np.linspace(10, 60, 64, dtype=np.uint8)
    channel = np.tile(gradient, (64, 1))
    frame = np.stack([channel, channel, channel], axis=-1)

    result = preprocess_frame(
        frame,
        PreprocessOptions(flip_horizontal=False, enable_clahe=True),
    )

    assert result.shape == frame.shape
    assert result.dtype == np.uint8
    assert float(result.std()) > float(frame.std())


# Kiểm tra kết hợp đồng thời cả 3 tùy chọn tiền xử lý không làm thay đổi ảnh đầu vào
def test_preprocess_frame_combined_options() -> None:
    rng = np.random.default_rng(42)
    frame = rng.integers(0, 256, size=(48, 64, 3), dtype=np.uint8)
    snapshot = frame.copy()

    result = preprocess_frame(
        frame,
        PreprocessOptions(flip_horizontal=True, enable_blur=True, enable_clahe=True),
    )

    assert result.shape == frame.shape
    assert result.dtype == np.uint8
    assert np.array_equal(frame, snapshot)
