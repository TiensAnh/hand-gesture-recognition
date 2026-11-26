# Điểm khởi chạy chính của ứng dụng Desktop nhận diện cử chỉ bàn tay

import customtkinter as ctk

from src.capture.camera import CameraManager
from src.config.settings import AppConfig
from src.gui.app import HandGestureApp


# Khởi tạo cấu hình, giao diện và chạy vòng lặp sự kiện chính
def main() -> None:
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    config = AppConfig()
    camera_manager = CameraManager(
        frame_width=config.frame_width,
        frame_height=config.frame_height,
    )
    app = HandGestureApp(config=config, camera_manager=camera_manager)
    app.mainloop()


if __name__ == "__main__":
    main()
