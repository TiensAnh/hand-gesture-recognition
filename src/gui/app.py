# Cửa sổ giao diện Desktop CustomTkinter hiển thị luồng webcam và nhận diện bàn tay realtime

import threading
import tkinter as tk
from typing import Any

import customtkinter as ctk
import cv2
from PIL import Image

from src.capture.camera import CameraManager
from src.config.settings import AppConfig, parse_camera_source
from src.vision.hand_tracker import (
    FpsCounter,
    HandDetection,
    HandTracker,
    draw_hand_landmarks,
)
from src.vision.preprocessing import PreprocessOptions, preprocess_frame


# Ứng dụng Desktop hiển thị luồng camera, tùy chọn tiền xử lý và kết quả nhận diện bàn tay
class HandGestureApp(ctk.CTk):
    # Khởi tạo cửa sổ chính, đối tượng quản lý camera, bộ nhận diện bàn tay và giao diện
    def __init__(
        self,
        config: AppConfig | None = None,
        camera_manager: CameraManager | None = None,
        hand_tracker: HandTracker | None = None,
        tracker_error: str | None = None,
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
        self._hand_tracker = hand_tracker
        self._tracker_error = tracker_error
        self._fps_counter = FpsCounter()

        self._after_job_id: str | None = None
        self._current_image: ctk.CTkImage | None = None
        self._last_frame_id = 0
        self._is_connecting = False
        self._is_closing = False
        self._connect_request_id = 0

        # Các biến trạng thái điều khiển tùy chọn tiền xử lý OpenCV realtime
        self._flip_var = tk.BooleanVar(value=True)
        self._blur_var = tk.BooleanVar(value=False)
        self._clahe_var = tk.BooleanVar(value=False)

        self._configure_window()
        self._build_layout()

    # Thiết lập tiêu đề, kích thước và sự kiện đóng cửa sổ
    def _configure_window(self) -> None:
        self.title(self._config.window_title)
        self.geometry(f"{self._config.window_width}x{self._config.window_height}")
        self.minsize(720, 560)
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

    # Dựng bố cục thanh nguồn camera, thanh tiền xử lý, khung video và thanh thông tin bàn tay
    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Thanh điều khiển nguồn camera phía trên
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=0, column=0, padx=16, pady=(16, 6), sticky="ew")
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

        # Thanh bật/tắt tùy chọn tiền xử lý OpenCV realtime
        preprocess_frame_box = ctk.CTkFrame(self)
        preprocess_frame_box.grid(row=1, column=0, padx=16, pady=6, sticky="ew")

        preprocess_title = ctk.CTkLabel(preprocess_frame_box, text="Tiền xử lý OpenCV:")
        preprocess_title.grid(row=0, column=0, padx=(12, 12), pady=10)

        self._flip_checkbox = ctk.CTkCheckBox(
            preprocess_frame_box,
            text="Lật gương",
            variable=self._flip_var,
        )
        self._flip_checkbox.grid(row=0, column=1, padx=10, pady=10)

        self._blur_checkbox = ctk.CTkCheckBox(
            preprocess_frame_box,
            text="Lọc nhiễu Gaussian",
            variable=self._blur_var,
        )
        self._blur_checkbox.grid(row=0, column=2, padx=10, pady=10)

        self._clahe_checkbox = ctk.CTkCheckBox(
            preprocess_frame_box,
            text="Cân bằng sáng CLAHE",
            variable=self._clahe_var,
        )
        self._clahe_checkbox.grid(row=0, column=3, padx=10, pady=10)

        # Khung hiển thị video ở trung tâm
        video_frame = ctk.CTkFrame(self)
        video_frame.grid(row=2, column=0, padx=16, pady=6, sticky="nsew")
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

        # Thanh thông tin nhận diện bàn tay và FPS cố định (không bị thanh trạng thái ghi đè)
        info_frame = ctk.CTkFrame(self)
        info_frame.grid(row=3, column=0, padx=16, pady=6, sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)

        initial_hand_text = self._get_idle_hand_info_text()
        self._hand_info_label = ctk.CTkLabel(
            info_frame,
            text=initial_hand_text,
            anchor="w",
        )
        self._hand_info_label.grid(row=0, column=0, padx=(12, 8), pady=8, sticky="ew")

        self._fps_label = ctk.CTkLabel(
            info_frame,
            text="FPS: --",
            width=100,
            anchor="e",
        )
        self._fps_label.grid(row=0, column=1, padx=(8, 12), pady=8, sticky="e")

        # Thanh trạng thái kết nối camera phía dưới
        self._status_label = ctk.CTkLabel(
            self,
            text="Trạng thái: Sẵn sàng",
            anchor="w",
        )
        self._status_label.grid(row=4, column=0, padx=20, pady=(2, 14), sticky="ew")

    # Tạo nội dung mặc định cho vùng thông tin bàn tay khi chờ hoặc khi thiếu model
    def _get_idle_hand_info_text(self) -> str:
        if self._tracker_error:
            return f"Cảnh báo nhận diện bàn tay: {self._tracker_error}"
        if self._hand_tracker is None:
            return "Nhận diện bàn tay: Chưa kích hoạt"
        return "Nhận diện bàn tay: Chưa phát hiện bàn tay"

    # Tạo chuỗi mô tả ngắn gọn các bàn tay đang phát hiện (tay trái/phải và số ngón)
    def _format_hand_summary(self, detections: list[HandDetection]) -> str:
        if self._tracker_error:
            return f"Cảnh báo nhận diện bàn tay: {self._tracker_error}"
        if self._hand_tracker is None:
            return "Nhận diện bàn tay: Chưa kích hoạt"
        if not detections:
            return "Nhận diện bàn tay: Chưa phát hiện bàn tay"

        parts: list[str] = []
        for detection in detections:
            if detection.handedness == "Left":
                hand_name = "Tay trái"
            elif detection.handedness == "Right":
                hand_name = "Tay phải"
            else:
                hand_name = "Không rõ"
            parts.append(f"{hand_name}: {detection.finger_count} ngón")

        return "Nhận diện bàn tay: " + " | ".join(parts)

    # Đọc tùy chọn tiền xử lý hiện tại từ các checkbox trên giao diện
    def _get_preprocess_options(self) -> PreprocessOptions:
        return PreprocessOptions(
            flip_horizontal=bool(self._flip_var.get()),
            enable_blur=bool(self._blur_var.get()),
            enable_clahe=bool(self._clahe_var.get()),
        )

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
        self._fps_counter.reset()
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
        self._fps_counter.reset()
        self._fps_label.configure(text="FPS: --")
        self._hand_info_label.configure(text=self._get_idle_hand_info_text())
        self._toggle_button.configure(text="Bật camera", state="normal")
        self._source_entry.configure(state="normal")
        self._set_status("Đã tắt camera")

    # Lấy khung hình mới nhất, tiền xử lý, nhận diện bàn tay và hiển thị lên giao diện
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
        current_fps = self._fps_counter.tick()

        # Tiền xử lý khung hình theo các tùy chọn đang bật trên giao diện
        preprocess_options = self._get_preprocess_options()
        processed_bgr = preprocess_frame(resized_bgr, preprocess_options)

        # Nhận diện bàn tay nếu đã nạp model và bắt lỗi an toàn để không làm đứt vòng lặp khung hình
        detections: list[HandDetection] = []
        runtime_error: str | None = None
        if self._hand_tracker is not None:
            try:
                detections = self._hand_tracker.process(
                    processed_bgr,
                    is_mirrored=preprocess_options.flip_horizontal,
                )
            except Exception as exc:
                runtime_error = f"Lỗi xử lý nhận diện bàn tay: {exc}"

        annotated_bgr = draw_hand_landmarks(processed_bgr, detections, fps=current_fps)

        frame_rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        new_image = ctk.CTkImage(
            light_image=pil_image,
            dark_image=pil_image,
            size=(resized_width, resized_height),
        )
        self._video_label.configure(image=new_image, text="")
        self._current_image = new_image

        # Cập nhật nhãn FPS và thông tin tay trái/phải cùng số ngón tay
        self._fps_label.configure(text=f"FPS: {current_fps:.1f}")
        if runtime_error is not None:
            self._hand_info_label.configure(text=runtime_error)
        else:
            self._hand_info_label.configure(text=self._format_hand_summary(detections))

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
            if self._hand_tracker is not None:
                self._hand_tracker.close()
            self._current_image = None
        finally:
            self.destroy()
