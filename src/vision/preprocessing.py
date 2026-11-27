# Module tiền xử lý khung hình OpenCV (lật gương, lọc nhiễu Gaussian, cân bằng sáng CLAHE)

from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np


# Cấu hình các tùy chọn tiền xử lý ảnh đầu vào
@dataclass(frozen=True)
class PreprocessOptions:
    flip_horizontal: bool = True
    enable_blur: bool = False
    enable_clahe: bool = False
    blur_kernel_size: int = 5
    clahe_clip_limit: float = 2.0
    clahe_tile_grid_size: tuple[int, int] = (8, 8)

    # Kiểm tra tính hợp lệ của các tham số bộ lọc ngay khi khởi tạo
    def __post_init__(self) -> None:
        if self.blur_kernel_size < 1 or self.blur_kernel_size % 2 == 0:
            raise ValueError("blur_kernel_size phải là số nguyên lẻ dương (ví dụ 3, 5, 7).")
        if self.clahe_clip_limit <= 0:
            raise ValueError("clahe_clip_limit phải lớn hơn 0.")
        tile_w, tile_h = self.clahe_tile_grid_size
        if tile_w < 1 or tile_h < 1:
            raise ValueError("clahe_tile_grid_size phải gồm 2 số nguyên dương.")


# Tạo và lưu đệm đối tượng CLAHE để tái sử dụng qua nhiều khung hình
@lru_cache(maxsize=16)
def _get_clahe(clip_limit: float, tile_grid_size: tuple[int, int]) -> cv2.CLAHE:
    return cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)


# Áp dụng chuỗi tiền xử lý OpenCV lên khung hình BGR và luôn trả về bản sao mới
def preprocess_frame(
    frame_bgr: np.ndarray,
    options: PreprocessOptions | None = None,
) -> np.ndarray:
    active_options = options if options is not None else PreprocessOptions()
    processed = frame_bgr.copy()

    # Lật gương theo trục ngang trước khi đưa vào MediaPipe
    if active_options.flip_horizontal:
        processed = cv2.flip(processed, 1)

    # Lọc nhiễu Gaussian để làm mịn ảnh đầu vào
    if active_options.enable_blur:
        kernel_size = active_options.blur_kernel_size
        processed = cv2.GaussianBlur(processed, (kernel_size, kernel_size), 0)

    # Cân bằng sáng cục bộ CLAHE trên kênh độ sáng L của không gian màu LAB
    if active_options.enable_clahe:
        lab_image = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab_image)
        clahe = _get_clahe(
            active_options.clahe_clip_limit,
            active_options.clahe_tile_grid_size,
        )
        equalized_l = clahe.apply(l_channel)
        merged_lab = cv2.merge((equalized_l, a_channel, b_channel))
        processed = cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)

    return processed
