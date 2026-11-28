# Đọc, ghi và thống kê tập dữ liệu cử chỉ bàn tay định dạng CSV 43 cột

import csv
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.ml.features import FEATURE_VECTOR_SIZE, GESTURE_LABELS
from src.vision.hand_tracker import HAND_LANDMARK_COUNT


# Tạo tuple 43 tên cột chuẩn cho file CSV dữ liệu cử chỉ
def _build_csv_header() -> tuple[str, ...]:
    columns = ["label"]
    for index in range(HAND_LANDMARK_COUNT):
        columns.append(f"x{index}")
        columns.append(f"y{index}")
    return tuple(columns)


# Tiêu đề chuẩn 43 cột: label, x0, y0, ..., x20, y20
CSV_HEADER: tuple[str, ...] = _build_csv_header()

# Tập hợp nhãn hợp lệ để tra cứu nhanh
_VALID_LABELS = frozenset(GESTURE_LABELS)


# Đối tượng lưu toàn bộ ma trận đặc trưng (N, 42) và danh sách nhãn tương ứng
@dataclass
class GestureDataset:
    features: np.ndarray
    labels: list[str]


# Kiểm tra một dòng CSV có hoàn toàn rỗng hay không
def _is_blank_row(row: list[str]) -> bool:
    if not row:
        return True
    return all(cell.strip() == "" for cell in row)


# Kiểm tra dòng tiêu đề CSV có khớp chính xác schema 43 cột hay không
def _validate_header(row: list[str], line_number: int) -> None:
    if tuple(row) != CSV_HEADER:
        raise ValueError(
            f"Dòng {line_number}: header CSV không khớp schema chuẩn 43 cột "
            f"('label,x0,y0,...,x20,y20')."
        )


# Phân tích và kiểm tra hợp lệ một dòng mẫu dữ liệu trong file CSV
def _parse_sample_row(row: list[str], line_number: int) -> tuple[str, list[float]]:
    if len(row) != len(CSV_HEADER):
        raise ValueError(
            f"Dòng {line_number}: sai số cột (cần {len(CSV_HEADER)}, nhận được {len(row)})."
        )

    label = row[0]
    if label not in _VALID_LABELS:
        raise ValueError(
            f"Dòng {line_number}: nhãn '{label}' không nằm trong danh sách nhãn hợp lệ."
        )

    feature_values: list[float] = []
    for col_offset, raw_cell in enumerate(row[1:], start=2):
        try:
            numeric_value = float(raw_cell)
        except ValueError as exc:
            raise ValueError(
                f"Dòng {line_number}, cột {col_offset}: giá trị '{raw_cell}' không phải số hợp lệ."
            ) from exc

        if not math.isfinite(numeric_value):
            raise ValueError(
                f"Dòng {line_number}, cột {col_offset}: giá trị chứa NaN hoặc Inf."
            )
        feature_values.append(numeric_value)

    return label, feature_values


# Kiểm tra dòng header hợp lệ ở đầu file CSV đã tồn tại
def _validate_existing_file_header(path: Path) -> None:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.reader(csv_file)
        for line_number, row in enumerate(reader, start=1):
            if _is_blank_row(row):
                continue
            _validate_header(row, line_number)
            return

    raise ValueError(
        f"File '{path}' chỉ chứa dòng trống và thiếu header CSV hợp lệ."
    )


# Kiểm tra file đã tồn tại có kết thúc bằng ký tự xuống dòng '\n' hay chưa
def _file_ends_with_newline(path: Path) -> bool:
    with path.open("rb") as binary_file:
        binary_file.seek(-1, 2)
        last_byte = binary_file.read(1)
    return last_byte == b"\n"


# Đếm số mẫu hiện có cho từng nhãn trong file CSV (luôn trả đủ 7 nhãn)
def count_samples_by_label(csv_path: str | Path) -> dict[str, int]:
    counts: dict[str, int] = {label: 0 for label in GESTURE_LABELS}
    path = Path(csv_path)

    if not path.exists() or path.stat().st_size == 0:
        return counts

    header_validated = False
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.reader(csv_file)
        for line_number, row in enumerate(reader, start=1):
            if _is_blank_row(row):
                continue

            if not header_validated:
                _validate_header(row, line_number)
                header_validated = True
                continue

            label, _feature_values = _parse_sample_row(row, line_number)
            counts[label] += 1

    return counts


# Nạp toàn bộ tập dữ liệu cử chỉ từ file CSV thành GestureDataset chuẩn hóa
def load_dataset(csv_path: str | Path) -> GestureDataset:
    path = Path(csv_path)
    empty_features = np.empty((0, FEATURE_VECTOR_SIZE), dtype=np.float32)

    if not path.exists() or path.stat().st_size == 0:
        return GestureDataset(features=empty_features, labels=[])

    header_validated = False
    labels: list[str] = []
    feature_rows: list[list[float]] = []

    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.reader(csv_file)
        for line_number, row in enumerate(reader, start=1):
            if _is_blank_row(row):
                continue

            if not header_validated:
                _validate_header(row, line_number)
                header_validated = True
                continue

            label, feature_values = _parse_sample_row(row, line_number)
            labels.append(label)
            feature_rows.append(feature_values)

    if not feature_rows:
        return GestureDataset(features=empty_features, labels=[])

    features_matrix = np.asarray(feature_rows, dtype=np.float32)
    return GestureDataset(features=features_matrix, labels=labels)


# Ghi nối một mẫu đặc trưng 42 chiều hợp lệ vào file CSV và xả đệm ngay
def append_sample(
    csv_path: str | Path,
    label: str,
    features: Sequence[float] | np.ndarray,
) -> None:
    if label not in _VALID_LABELS:
        raise ValueError(
            f"Nhãn '{label}' không hợp lệ. Chỉ chấp nhận: {', '.join(GESTURE_LABELS)}."
        )

    feature_array = np.asarray(features, dtype=np.float64)
    if feature_array.ndim != 1 or feature_array.shape[0] != FEATURE_VECTOR_SIZE:
        raise ValueError(
            f"Vector đặc trưng phải là mảng 1 chiều gồm đúng {FEATURE_VECTOR_SIZE} phần tử."
        )

    if not bool(np.all(np.isfinite(feature_array))):
        raise ValueError("Vector đặc trưng không được chứa NaN hoặc Inf.")

    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Xác định file mới/rỗng hay đã có dữ liệu để xử lý header và xuống dòng an toàn
    is_new_or_empty = not path.exists() or path.stat().st_size == 0
    needs_leading_newline = False

    if not is_new_or_empty:
        _validate_existing_file_header(path)
        needs_leading_newline = not _file_ends_with_newline(path)

    # Định dạng số float32 ngắn gọn giữ nguyên độ chính xác khi nạp lại
    formatted_features = [str(float(np.float32(value))) for value in feature_array]
    row_values = [label, *formatted_features]

    with path.open("a", encoding="utf-8", newline="") as csv_file:
        if needs_leading_newline:
            csv_file.write("\n")

        writer = csv.writer(csv_file, lineterminator="\n")
        if is_new_or_empty:
            writer.writerow(CSV_HEADER)
        writer.writerow(row_values)
        csv_file.flush()
