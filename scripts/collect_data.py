# Script thu thập dữ liệu cử chỉ bàn tay từ camera và lưu vào file CSV 43 cột

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

# Thêm thư mục gốc dự án vào sys.path khi chạy trực tiếp dưới dạng script
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.capture.camera import CameraManager  # noqa: E402
from src.config.settings import (  # noqa: E402
    DEFAULT_DATASET_PATH,
    AppConfig,
    parse_camera_source,
)
from src.ml import (  # noqa: E402
    GESTURE_LABELS,
    CollectionController,
    append_sample,
    count_samples_by_label,
)
from src.vision.hand_tracker import (  # noqa: E402
    FpsCounter,
    HandDetection,
    HandTracker,
    draw_hand_landmarks,
)
from src.vision.preprocessing import PreprocessOptions, preprocess_frame  # noqa: E402

# Tên cửa sổ OpenCV dùng hoàn toàn ASCII không dấu
WINDOW_NAME = "Gesture Data Collector"

# Mã phím ASCII cho Escape và dấu cách
KEY_ESCAPE = 27
KEY_SPACE = ord(" ")


# Thu nhỏ khung hình giữ đúng tỉ lệ khung ảnh về tối đa max_width x max_height
def resize_frame_to_fit(
    frame_bgr: np.ndarray,
    max_width: int,
    max_height: int,
) -> np.ndarray:
    height, width = frame_bgr.shape[:2]
    if width <= 0 or height <= 0:
        return frame_bgr

    if width <= max_width and height <= max_height:
        return frame_bgr

    scale = min(max_width / width, max_height / height)
    target_width = max(1, int(round(width * scale)))
    target_height = max(1, int(round(height * scale)))
    return cv2.resize(frame_bgr, (target_width, target_height), interpolation=cv2.INTER_AREA)


# Vẽ giao diện HUD thông tin thu thập bằng ký tự ASCII không dấu lên khung hình
def draw_collection_hud(
    frame_bgr: np.ndarray,
    controller: CollectionController,
    sample_counts: dict[str, int],
    flip_horizontal: bool,
    status_message: str,
) -> np.ndarray:
    annotated = frame_bgr.copy()
    height, width = annotated.shape[:2]
    if width <= 0 or height <= 0:
        return annotated

    # Vẽ dải nền tối phía dưới để chữ HUD luôn dễ đọc trên mọi phông nền camera
    panel_height = 108
    panel_top = max(0, height - panel_height)
    overlay = annotated.copy()
    cv2.rectangle(overlay, (0, panel_top), (width, height), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.72, annotated, 0.28, 0.0, annotated)

    current_label = controller.current_label
    current_count = sample_counts.get(current_label, 0)
    total_count = sum(sample_counts.values())
    mode_text = "AUTO" if controller.auto_capture else "MANUAL"
    flip_text = "ON" if flip_horizontal else "OFF"
    mode_color = (0, 200, 255) if controller.auto_capture else (220, 220, 220)

    # Dòng 1: nhãn đang chọn, chế độ chụp và trạng thái lật gương
    header_line = (
        f"Label: [{controller.current_index + 1}] {current_label} ({current_count}) | "
        f"Total: {total_count} | Mode: {mode_text} | Flip: {flip_text}"
    )
    cv2.putText(
        annotated,
        header_line,
        (10, panel_top + 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        mode_color,
        1,
        cv2.LINE_AA,
    )

    # Dòng 2 và 3: thống kê nhanh số mẫu của 7 cử chỉ theo phím tắt 1-7
    first_row_items = [
        f"{idx}:{name}({sample_counts.get(name, 0)})"
        for idx, name in enumerate(controller.labels[:4], start=1)
    ]
    second_row_items = [
        f"{idx}:{name}({sample_counts.get(name, 0)})"
        for idx, name in enumerate(controller.labels[4:], start=5)
    ]
    cv2.putText(
        annotated,
        "  ".join(first_row_items),
        (10, panel_top + 46),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.46,
        (235, 235, 235),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        annotated,
        "  ".join(second_row_items),
        (10, panel_top + 68),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.46,
        (235, 235, 235),
        1,
        cv2.LINE_AA,
    )

    # Dòng 4: hướng dẫn phím tắt điều khiển nhanh
    keys_line = "Keys: [1-7] Label | [Space] Snap | [C] Auto | [F] Flip | [Q/Esc] Quit"
    cv2.putText(
        annotated,
        keys_line,
        (10, panel_top + 94),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (160, 220, 255),
        1,
        cv2.LINE_AA,
    )

    # Hiển thị thông báo trạng thái gần nhất ở góc trên phải
    if status_message:
        status_color = (0, 120, 255) if status_message.startswith("WARN") else (80, 255, 140)
        cv2.putText(
            annotated,
            status_message,
            (12, 54),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.56,
            status_color,
            2,
            cv2.LINE_AA,
        )

    return annotated


# Phân tích các tham số dòng lệnh cho công cụ thu thập dữ liệu
def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Thu thập dữ liệu đặc trưng bàn tay (42 chiều) ra file CSV."
    )
    parser.add_argument(
        "--source",
        type=str,
        default="0",
        help="Nguồn camera: chỉ số webcam (0, 1...) hoặc URL luồng mạng (mặc định: 0).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Đường dẫn file CSV đầu ra (mặc định: data/gestures.csv).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.2,
        help="Giãn cách tối thiểu (giây) khi bật chế độ ghi liên tục (mặc định: 0.2).",
    )
    parser.add_argument(
        "--no-flip",
        action="store_true",
        help="Tắt lật gương khung hình theo trục ngang khi khởi chạy.",
    )
    return parser


# Chạy vòng lặp camera, nhận diện bàn tay và thu thập mẫu theo phím tắt
def run_collector(args: argparse.Namespace) -> int:
    if args.interval <= 0:
        print("Lỗi: --interval phải lớn hơn 0.")
        return 1

    try:
        parsed_source = parse_camera_source(args.source)
    except ValueError as exc:
        print(f"Lỗi nguồn camera: {exc}")
        return 1

    # Nạp bộ đếm số mẫu hiện có một lần vào RAM khi khởi động
    try:
        sample_counts = count_samples_by_label(args.output)
    except (ValueError, OSError) as exc:
        print(f"Lỗi khi đọc file dataset '{args.output}': {exc}")
        return 1

    config = AppConfig()
    controller = CollectionController(
        labels=GESTURE_LABELS,
        capture_interval_seconds=args.interval,
    )

    # Khởi tạo MediaPipe HandTracker và hướng dẫn tải model nếu còn thiếu
    try:
        hand_tracker = HandTracker(
            model_path=config.hand_model_path,
            max_num_hands=config.max_num_hands,
            min_hand_detection_confidence=config.min_hand_detection_confidence,
            min_hand_presence_confidence=config.min_hand_presence_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
        )
    except FileNotFoundError as exc:
        print(f"Lỗi khởi tạo HandTracker: {exc}")
        print("Hãy tải model trước bằng lệnh:")
        print("  .venv\\Scripts\\python scripts\\download_hand_model.py")
        return 1

    camera = CameraManager(
        source=parsed_source,
        frame_width=config.frame_width,
        frame_height=config.frame_height,
    )
    opened, open_message = camera.open()
    if not opened:
        hand_tracker.close()
        print(f"Không thể mở camera: {open_message}")
        return 1

    print(f"{open_message}")
    print(f"File dữ liệu đầu ra: {args.output}")
    print(
        "Phím tắt: [1-7] Chọn nhãn | [Space] Chụp đơn | "
        "[C] Bật/tắt Auto | [F] Lật gương | [Q/Esc] Thoát"
    )

    flip_horizontal = not args.no_flip
    fps_counter = FpsCounter()
    last_processed_frame_id = 0
    latest_detections: list[HandDetection] = []
    latest_base_frame: np.ndarray | None = None
    status_message = "Ready"
    window_shown = False

    try:
        while True:
            # Thoát gọn nếu luồng đọc camera báo mất tín hiệu
            if camera.has_error:
                print("Cảnh báo: mất tín hiệu từ nguồn camera. Đang dừng thu thập.")
                break

            # Kiểm tra người dùng có đóng cửa sổ bằng nút X hay không sau khi đã hiển thị
            if window_shown:
                window_visible = cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE)
                if window_visible < 1:
                    break

            frame_id, raw_frame = camera.get_latest_frame()
            manual_requested = False
            hud_dirty = False

            # Đọc phím tắt không chặn dài để giữ khung hình mượt và phản hồi nhanh
            key = cv2.waitKey(config.refresh_interval_ms) & 0xFF
            if key in (ord("q"), ord("Q"), KEY_ESCAPE):
                break
            if ord("1") <= key <= ord("7"):
                selected_index = key - ord("1")
                if controller.select_label_by_index(selected_index):
                    status_message = f"Selected: {controller.current_label}"
                    hud_dirty = True
            elif key == KEY_SPACE:
                manual_requested = True
            elif key in (ord("c"), ord("C")):
                auto_enabled = controller.toggle_auto_capture()
                status_message = "Auto capture: ON" if auto_enabled else "Auto capture: OFF"
                hud_dirty = True
            elif key in (ord("f"), ord("F")):
                flip_horizontal = not flip_horizontal
                status_message = "Flip: ON" if flip_horizontal else "Flip: OFF"
                hud_dirty = True

            # Xử lý khung hình mới khi camera đã trả về frame_id khác lần trước
            if raw_frame is not None and frame_id != last_processed_frame_id:
                last_processed_frame_id = frame_id
                resized_frame = resize_frame_to_fit(
                    raw_frame,
                    config.frame_width,
                    config.frame_height,
                )
                preprocess_options = PreprocessOptions(flip_horizontal=flip_horizontal)
                processed_frame = preprocess_frame(resized_frame, preprocess_options)
                latest_detections = hand_tracker.process(
                    processed_frame,
                    is_mirrored=flip_horizontal,
                )
                current_fps = fps_counter.tick()
                latest_base_frame = draw_hand_landmarks(
                    processed_frame,
                    latest_detections,
                    fps=current_fps,
                )
                hud_dirty = True

            # Thử chụp mẫu cho khung hình mới nhất khi ở chế độ auto hoặc bấm Space
            if latest_base_frame is not None and (manual_requested or controller.auto_capture):
                captured = controller.try_capture(
                    frame_id=last_processed_frame_id,
                    detections=latest_detections,
                    manual=manual_requested,
                )
                if captured is not None:
                    captured_label, feature_vector = captured
                    try:
                        append_sample(args.output, captured_label, feature_vector)
                        sample_counts[captured_label] = sample_counts.get(captured_label, 0) + 1
                        status_message = (
                            f"Saved: {captured_label} (#{sample_counts[captured_label]})"
                        )
                    except (OSError, PermissionError) as exc:
                        print(f"Cảnh báo: không thể ghi mẫu vào '{args.output}': {exc}")
                        status_message = "WARN: failed to write CSV"
                    hud_dirty = True

            # Hiển thị lại khung hình mỗi khi có frame mới hoặc trạng thái HUD thay đổi
            if latest_base_frame is not None and hud_dirty:
                display_frame = draw_collection_hud(
                    latest_base_frame,
                    controller=controller,
                    sample_counts=sample_counts,
                    flip_horizontal=flip_horizontal,
                    status_message=status_message,
                )
                cv2.imshow(WINDOW_NAME, display_frame)
                window_shown = True
    finally:
        camera.release()
        hand_tracker.close()
        cv2.destroyAllWindows()

    print(f"Đã dừng thu thập. Tổng số mẫu hiện có: {sum(sample_counts.values())}")
    return 0


# Điểm vào chính khi chạy script từ dòng lệnh
def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    exit_code = run_collector(args)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
