# Cửa sổ giao diện Desktop CustomTkinter hiển thị luồng webcam realtime

import threading
import tkinter as tk
from typing import Any

import customtkinter as ctk
import cv2
from PIL import Image

from src.capture.camera import CameraManager
from src.config.settings import AppConfig, parse_camera_source


# Ứng dụng Desktop hiển thị luồng camera và điều khiển bật/tắt nguồn vào
class HandGestureApp(ctk.CTk):
    # Khởi tạo cửa sổ chính, đối tượng quản lý camera và các thành phần giao diện
    def __init__(
        self,
        config: AppConfig | None = None,
        camera_manager: CameraManager | None = None,
    ) -> None:
        super().__init__()

        self._config = config if config is not None else AppConfig()
        self._camera = (
            camera_manager
            if camera_manager is not None
            else CameraManager(
                frame_width=self._config.frame_width,
                frame_height=self._config.frame_height,
            )
        )
        self._after_job_id: str | None = None
        self._current_image: ctk.CTkImage | None = None
        self._last_frame_id = 0
        self._is_connecting = False
        self._is_closing = False
        self._connect_request_id = 0

        self._configure_window()
        self._build_layout()

    # Thiết lập tiêu đề, kích thước và sự kiện đóng cửa sổ
    def _configure_window(self) -> None:
        self.title(self._config.window_title)
        self.geometry(f"{self._config.window_width}x{self._config.window_height}")
        self.minsize(720, 520)
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

    # Dựng bố cục thanh điều khiển nguồn camera và khung hiển thị video
    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Thanh điều khiển phía trên
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        control_frame.grid_columnconfigure(1, weight=1)

        source_label = ctk.CTkLabel(control_frame, text="Nguồn camera:")
        source_label.grid(row=0, column=0, padx=(12, 8), pady=12)

        self._source_entry = ctk.CTkEntry(
            control_frame,
            placeholder_text="0 (cam laptop), 1/2 (cam ảo) hoặc http://...",
        )
        self._source_entry.insert(0, self._config.default_camera_source)
        self._source_entry.grid(row=0, column=1, padx=8, pady=12, sticky="ew")

        self._toggle_button = ctk.CTkButton(
            control_frame,
            text="Bật camera",
            width=140,
            command=self._handle_toggle_camera,
        )
        self._toggle_button.grid(row=0, column=2, padx=(8, 12), pady=12)

        # Khung hiển thị video ở trung tâm
        video_frame = ctk.CTkFrame(self)
        video_frame.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        video_frame.grid_columnconfigure(0, weight=1)
        video_frame.grid_rowconfigure(0, weight=1)

        self._video_label = ctk.CTkLabel(
            video_frame,
            text=(
                "Chưa bật camera.\n"
                "Nhập 0 (cam laptop), 1/2 (DroidCam/Iriun) hoặc URL IP Webcam rồi bấm Bật camera."
            ),
            justify="center",
        )
        self._video_label.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")

        # Thanh trạng thái phía dưới
        self._status_label = ctk.CTkLabel(
            self,
            text="Trạng thái: Sẵn sàng",
            anchor="w",
        )
        self._status_label.grid(row=2, column=0, padx=20, pady=(4, 14), sticky="ew")

    # Cập nhật nội dung hiển thị trên thanh trạng thái
    def _set_status(self, message: str) -> None:
        self._status_label.configure(text=f"Trạng thái: {message}")

    # Xóa ảnh hiện tại trên nhãn video trước khi bỏ tham chiếu để tránh TclError
    def _clear_video_image(self, placeholder_text: str) -> None:
        self._video_label.configure(image=None, text=placeholder_text)
        internal_label = getattr(self._video_label, "_label", None)
        if internal_label is not None:
            internal_label.configure(image="")
        self._current_image = None

    # Thay đổi kích thước khung hình BGR giữ nguyên tỉ lệ vừa khít vùng hiển thị
    def _resize_frame_for_display(self, frame_bgr: Any) -> tuple[Any, int, int] | None:
        src_height, src_width = frame_bgr.shape[:2]
        if src_width <= 0 or src_height <= 0:
            return None

        max_width = self._config.frame_width
        max_height = self._config.frame_height
        scale = min(max_width / src_width, max_height / src_height)
        resized_width = max(1, int(round(src_width * scale)))
        resized_height = max(1, int(round(src_height * scale)))

        # Bỏ qua bước resize nếu kích thước khung hình đã khớp kích thước hiển thị
        if resized_width == src_width and resized_height == src_height:
            return frame_bgr, src_width, src_height

        resized_bgr = cv2.resize(
            frame_bgr,
            (resized_width, resized_height),
            interpolation=cv2.INTER_LINEAR,
        )
        return resized_bgr, resized_width, resized_height

    # Xử lý sự kiện nhấn nút Bật/Tắt camera
    def _handle_toggle_camera(self) -> None:
        if self._is_connecting:
            return

        if self._camera.is_opened:
            self._stop_camera()
            return

        self._start_camera()

    # Phân tích nguồn camera và mở kết nối bất đồng bộ để không chặn giao diện
    def _start_camera(self) -> None:
        raw_source = self._source_entry.get()

        try:
            parsed_source = parse_camera_source(raw_source)
        except ValueError as exc:
            self._set_status(str(exc))
            return

        # Khóa nút điều khiển trong lúc đang kết nối để tránh bấm đúp
        self._is_connecting = True
        self._connect_request_id += 1
        request_id = self._connect_request_id

        self._toggle_button.configure(text="Đang kết nối...", state="disabled")
        self._source_entry.configure(state="disabled")
        self._set_status("Đang kết nối camera...")
        self.update_idletasks()

        # Thực hiện mở camera trên luồng nền rồi trả kết quả về luồng giao diện
        def open_in_background() -> None:
            opened, message = self._camera.open(parsed_source)
            try:
                self.after(0, self._handle_open_result, request_id, opened, message)
            except tk.TclError:
                if opened:
                    self._camera.release(wait_timeout=0)

        threading.Thread(target=open_in_background, daemon=True).start()

    # Xử lý kết quả mở camera trả về từ luồng nền trên main thread
    def _handle_open_result(self, request_id: int, opened: bool, message: str) -> None:
        # Hủy kết nối thừa nếu cửa sổ đang đóng hoặc yêu cầu đã cũ
        if self._is_closing or request_id != self._connect_request_id:
            if opened:
                self._camera.release(wait_timeout=0)
            return

        self._is_connecting = False
        self._set_status(message)

        if not opened:
            self._toggle_button.configure(text="Bật camera", state="normal")
            self._source_entry.configure(state="normal")
            return

        self._last_frame_id = 0
        self._toggle_button.configure(text="Tắt camera", state="normal")
        self._schedule_next_frame()

    # Dừng vòng lặp cập nhật, giải phóng camera không chặn và đưa UI về trạng thái chờ
    def _stop_camera(self) -> None:
        if self._after_job_id is not None:
            self.after_cancel(self._after_job_id)
            self._after_job_id = None

        self._camera.release(wait_timeout=0)
        self._clear_video_image(
            "Camera đã tắt.\n"
            "Nhập 0 (cam laptop), 1/2 (DroidCam/Iriun) hoặc URL IP Webcam rồi bấm Bật camera."
        )
        self._last_frame_id = 0
        self._toggle_button.configure(text="Bật camera", state="normal")
        self._source_entry.configure(state="normal")
        self._set_status("Đã tắt camera")

    # Lấy khung hình mới nhất không chặn, resize giữ tỉ lệ và hiển thị lên giao diện
    def _update_frame(self) -> None:
        self._after_job_id = None

        if self._is_closing or not self._camera.is_opened:
            return

        # Dừng camera và thông báo khi luồng nền báo mất tín hiệu
        if self._camera.has_error:
            self._stop_camera()
            self._set_status("Mất tín hiệu từ camera. Vui lòng kiểm tra kết nối và bật lại.")
            return

        frame_id, frame_bgr = self._camera.get_latest_frame()

        # Bỏ qua render khi chưa có khung hình mới nhưng vẫn tiếp tục lên lịch đọc
        if frame_bgr is None or frame_id == self._last_frame_id:
            self._schedule_next_frame()
            return

        resized_result = self._resize_frame_for_display(frame_bgr)
        if resized_result is None:
            self._schedule_next_frame()
            return

        resized_bgr, resized_width, resized_height = resized_result
        self._last_frame_id = frame_id

        frame_rgb = cv2.cvtColor(resized_bgr, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        new_image = ctk.CTkImage(
            light_image=pil_image,
            dark_image=pil_image,
            size=(resized_width, resized_height),
        )
        self._video_label.configure(image=new_image, text="")
        self._current_image = new_image
        self._schedule_next_frame()

    # Đặt lịch đọc khung hình kế tiếp mà không chặn luồng giao diện
    def _schedule_next_frame(self) -> None:
        if self._is_closing:
            return

        self._after_job_id = self.after(
            self._config.refresh_interval_ms,
            self._update_frame,
        )

    # Giải phóng tài nguyên sạch sẽ và luôn đóng cửa sổ ứng dụng an toàn
    def _handle_close(self) -> None:
        self._is_closing = True
        self._connect_request_id += 1

        try:
            if self._after_job_id is not None:
                self.after_cancel(self._after_job_id)
                self._after_job_id = None
            self._camera.release(wait_timeout=0)
            self._current_image = None
        finally:
            self.destroy()
