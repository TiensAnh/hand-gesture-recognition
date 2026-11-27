# Điểm khởi chạy chính của ứng dụng Desktop nhận diện cử chỉ bàn tay

import customtkinter as ctk

from src.capture.camera import CameraManager
from src.config.settings import AppConfig
from src.gui.app import HandGestureApp
from src.vision.hand_tracker import HandTracker


# Khởi tạo bộ nhận diện bàn tay an toàn, trả về thông báo lỗi nếu thiếu file model
def _create_hand_tracker(config: AppConfig) -> tuple[HandTracker | None, str | None]:
    try:
        tracker = HandTracker(
            model_path=config.hand_model_path,
            max_num_hands=config.max_num_hands,
            min_hand_detection_confidence=config.min_hand_detection_confidence,
            min_hand_presence_confidence=config.min_hand_presence_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
        )
        return tracker, None
    except FileNotFoundError as exc:
        return None, str(exc)
    except Exception as exc:
        return None, f"Không khởi tạo được MediaPipe HandLandmarker: {exc}"


# Khởi tạo cấu hình, camera, bộ nhận diện bàn tay, giao diện và chạy vòng lặp sự kiện chính
def main() -> None:
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    config = AppConfig()
    camera_manager = CameraManager(
        frame_width=config.frame_width,
        frame_height=config.frame_height,
    )
    hand_tracker, tracker_error = _create_hand_tracker(config)
    app = HandGestureApp(
        config=config,
        camera_manager=camera_manager,
        hand_tracker=hand_tracker,
        tracker_error=tracker_error,
    )
    app.mainloop()


if __name__ == "__main__":
    main()
