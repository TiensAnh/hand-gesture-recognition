# Kiểm thử đọc, ghi, thống kê và kiểm tra lỗi file CSV tập dữ liệu cử chỉ

import math
from pathlib import Path

import numpy as np
import pytest

from src.ml.dataset import (
    CSV_HEADER,
    GestureDataset,
    append_sample,
    count_samples_by_label,
    load_dataset,
)
from src.ml.features import FEATURE_VECTOR_SIZE, GESTURE_LABELS


# Tạo vector đặc trưng 42 chiều hợp lệ phục vụ kiểm thử
def _make_feature_vector(seed_offset: float = 0.0) -> np.ndarray:
    values = np.linspace(-1.0, 1.0, FEATURE_VECTOR_SIZE, dtype=np.float32)
    values = np.clip(values + seed_offset, -1.0, 1.0).astype(np.float32)
    values[0] = 0.0
    values[1] = 0.0
    return values


# Kiểm tra schema CSV gồm đúng 43 cột: label, x0, y0, ..., x20, y20
def test_csv_header_schema_has_43_columns() -> None:
    assert len(CSV_HEADER) == 43
    assert CSV_HEADER[0] == "label"
    assert CSV_HEADER[1:5] == ("x0", "y0", "x1", "y1")
    assert CSV_HEADER[-2:] == ("x20", "y20")


# Kiểm tra đọc và đếm khi file CSV chưa tồn tại, rỗng hoặc chỉ có header
def test_empty_or_missing_csv_returns_zero_counts_and_empty_dataset(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.csv"
    counts_missing = count_samples_by_label(missing_path)
    dataset_missing = load_dataset(missing_path)

    assert counts_missing == {label: 0 for label in GESTURE_LABELS}
    assert isinstance(dataset_missing, GestureDataset)
    assert dataset_missing.features.shape == (0, FEATURE_VECTOR_SIZE)
    assert dataset_missing.features.dtype == np.float32
    assert dataset_missing.labels == []
    assert isinstance(dataset_missing.labels, list)

    empty_path = tmp_path / "empty.csv"
    empty_path.write_text("", encoding="utf-8")
    assert count_samples_by_label(empty_path) == {label: 0 for label in GESTURE_LABELS}
    assert load_dataset(empty_path).labels == []

    header_only_path = tmp_path / "header_only.csv"
    header_only_path.write_text(",".join(CSV_HEADER) + "\n", encoding="utf-8")
    assert count_samples_by_label(header_only_path) == {label: 0 for label in GESTURE_LABELS}
    loaded_header_only = load_dataset(header_only_path)
    assert loaded_header_only.features.shape == (0, FEATURE_VECTOR_SIZE)
    assert loaded_header_only.labels == []


# Kiểm tra ghi nối nhiều mẫu, tự tạo thư mục cha và nạp lại khớp dữ liệu
def test_append_sample_creates_parent_and_roundtrips_cleanly(tmp_path: Path) -> None:
    csv_path = tmp_path / "nested" / "dir" / "gestures.csv"
    vec_1 = _make_feature_vector(0.0)
    vec_2 = _make_feature_vector(0.15)
    vec_3 = _make_feature_vector(-0.2)

    append_sample(csv_path, "fist", vec_1)
    append_sample(csv_path, "peace", vec_2)
    append_sample(csv_path, "fist", vec_3)

    counts = count_samples_by_label(csv_path)
    assert counts["fist"] == 2
    assert counts["peace"] == 1
    assert counts["ok"] == 0
    assert sum(counts.values()) == 3

    dataset = load_dataset(csv_path)
    assert dataset.labels == ["fist", "peace", "fist"]
    assert dataset.features.shape == (3, FEATURE_VECTOR_SIZE)
    assert dataset.features.dtype == np.float32
    assert np.allclose(dataset.features[0], vec_1, atol=1e-6)
    assert np.allclose(dataset.features[1], vec_2, atol=1e-6)
    assert np.allclose(dataset.features[2], vec_3, atol=1e-6)


# Kiểm tra append an toàn khi file cũ thiếu ký tự xuống dòng ở cuối
def test_append_sample_handles_missing_trailing_newline(tmp_path: Path) -> None:
    csv_path = tmp_path / "no_newline.csv"
    first_row = ["open_palm"] + ["0.0"] * FEATURE_VECTOR_SIZE
    csv_path.write_text(
        ",".join(CSV_HEADER) + "\n" + ",".join(first_row),
        encoding="utf-8",
    )

    append_sample(csv_path, "rock", _make_feature_vector(0.05))
    dataset = load_dataset(csv_path)

    assert dataset.labels == ["open_palm", "rock"]
    assert dataset.features.shape == (2, FEATURE_VECTOR_SIZE)


# Kiểm tra bỏ qua dòng trống xen giữa trong file CSV hợp lệ
def test_dataset_ignores_blank_lines(tmp_path: Path) -> None:
    csv_path = tmp_path / "with_blanks.csv"
    sample_row = ",".join(["ok"] + ["0.25"] * FEATURE_VECTOR_SIZE)
    csv_path.write_text(
        "\n" + ",".join(CSV_HEADER) + "\n\n" + sample_row + "\n\n",
        encoding="utf-8",
    )

    assert count_samples_by_label(csv_path)["ok"] == 1
    dataset = load_dataset(csv_path)
    assert dataset.labels == ["ok"]
    assert dataset.features.shape == (1, FEATURE_VECTOR_SIZE)


# Kiểm tra fail-fast kèm số dòng khi header CSV sai
def test_invalid_header_raises_value_error_with_line_number(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad_header.csv"
    csv_path.write_text("wrong_col,x0,y0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Dòng 1"):
        load_dataset(csv_path)
    with pytest.raises(ValueError, match="Dòng 1"):
        count_samples_by_label(csv_path)
    with pytest.raises(ValueError, match="Dòng 1"):
        append_sample(csv_path, "fist", _make_feature_vector())


# Kiểm tra fail-fast kèm số dòng khi sai số cột, nhãn lạ, giá trị hỏng hoặc NaN/Inf
@pytest.mark.parametrize(
    "bad_row",
    [
        "fist,0.1,0.2",
        ",".join(["unknown_label"] + ["0.0"] * FEATURE_VECTOR_SIZE),
        ",".join(["fist", "not_a_number"] + ["0.0"] * (FEATURE_VECTOR_SIZE - 1)),
        ",".join(["fist", "nan"] + ["0.0"] * (FEATURE_VECTOR_SIZE - 1)),
        ",".join(["fist", "inf"] + ["0.0"] * (FEATURE_VECTOR_SIZE - 1)),
    ],
)
def test_corrupted_row_raises_value_error_with_line_number(
    tmp_path: Path,
    bad_row: str,
) -> None:
    csv_path = tmp_path / "corrupted.csv"
    valid_row = ",".join(["fist"] + ["0.0"] * FEATURE_VECTOR_SIZE)
    csv_path.write_text(
        ",".join(CSV_HEADER) + "\n" + valid_row + "\n" + bad_row + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Dòng 3"):
        load_dataset(csv_path)
    with pytest.raises(ValueError, match="Dòng 3"):
        count_samples_by_label(csv_path)


# Kiểm tra append_sample từ chối nhãn lạ, sai kích thước vector hoặc chứa NaN/Inf
def test_append_sample_validates_label_and_features(tmp_path: Path) -> None:
    csv_path = tmp_path / "validate.csv"

    with pytest.raises(ValueError, match="Nhãn"):
        append_sample(csv_path, "invalid_gesture", _make_feature_vector())

    with pytest.raises(ValueError, match="42"):
        append_sample(csv_path, "fist", np.zeros(10, dtype=np.float32))

    with pytest.raises(ValueError, match="42"):
        append_sample(csv_path, "fist", np.zeros((1, FEATURE_VECTOR_SIZE), dtype=np.float32))

    bad_vec = _make_feature_vector()
    bad_vec[3] = math.nan
    with pytest.raises(ValueError, match="NaN"):
        append_sample(csv_path, "fist", bad_vec)
