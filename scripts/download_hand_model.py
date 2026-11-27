# Script tải file model hand_landmarker.task của MediaPipe vào thư mục models/

import argparse
import sys
import urllib.request
from pathlib import Path

# Thêm thư mục gốc dự án vào sys.path khi chạy trực tiếp dưới dạng script
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import DEFAULT_HAND_MODEL_PATH  # noqa: E402

# Đường dẫn tải chính thức của Google Storage cho MediaPipe HandLandmarker (float16)
HAND_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
DOWNLOAD_CHUNK_SIZE = 65536


# Tải file model về đường dẫn đích bằng file tạm ngay trong thư mục models/ trên ổ dự án
def download_hand_model(
    destination: Path = DEFAULT_HAND_MODEL_PATH,
    force: bool = False,
    url: str = HAND_LANDMARKER_MODEL_URL,
) -> Path:
    target_path = Path(destination)
    if target_path.is_file() and not force:
        print(f"File model đã tồn tại tại: {target_path}")
        return target_path

    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(f"{target_path.suffix}.tmp")

    print(f"Đang tải hand_landmarker.task từ: {url}")
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            with temp_path.open("wb") as output_file:
                while True:
                    chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    output_file.write(chunk)

        temp_path.replace(target_path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise

    size_mb = target_path.stat().st_size / (1024 * 1024)
    print(f"Tải xong model ({size_mb:.2f} MB) tại: {target_path}")
    return target_path


# Phân tích tham số dòng lệnh và thực thi tải model
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tải file model hand_landmarker.task cho MediaPipe HandLandmarker."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_HAND_MODEL_PATH,
        help="Đường dẫn lưu file model (mặc định: models/hand_landmarker.task).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Tải lại và ghi đè nếu file model đã tồn tại.",
    )
    args = parser.parse_args()
    download_hand_model(destination=args.output, force=args.force)


if __name__ == "__main__":
    main()
