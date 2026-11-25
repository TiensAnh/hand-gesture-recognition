# T005 - Huấn luyện và đánh giá mô hình phân loại cử chỉ

Cập nhật: 2026-11-25
Epic: E02
Spec: không có
Nhánh: `feature/huan-luyen-mo-hinh`
Phụ thuộc: T004

## Mục tiêu
- Viết script huấn luyện và so sánh các mô hình `scikit-learn` (MLP, SVM, KNN) trên tập đặc trưng landmark, lưu mô hình tốt nhất và xuất báo cáo đánh giá phục vụ báo cáo môn học.

## Phạm vi (lát cắt dọc)
- Huấn luyện: chia tập train/test (stratified), huấn luyện MLP, SVM (RBF) và KNN, chọn mô hình có F1/Accuracy tốt nhất.
- Lưu trữ & Đánh giá: lưu mô hình + danh sách nhãn vào `models/` (`.joblib` + `.json`), xuất bảng chỉ số (accuracy, precision, recall, F1) và ảnh confusion matrix (`matplotlib`).
- Kiểm thử: unit test chạy pipeline huấn luyện/dự đoán trên dữ liệu giả lập nhỏ để đảm bảo CI luôn kiểm tra được.

## Xong khi (kiểm tra được bằng chạy hoặc test)
- [ ] Chạy script huấn luyện tạo ra file model trong `models/` và ảnh confusion matrix không lỗi.
- [ ] Có bảng so sánh kết quả giữa MLP, SVM và KNN trên tập kiểm thử.
- [ ] `ruff check .` và `pytest` đều đạt.

## Ghi chú
- Không commit file model dung lượng quá lớn nếu vượt nhu cầu; giữ kích thước nhẹ (mô hình scikit-learn trên 42 đặc trưng rất nhỏ, vài trăm KB).

## Kết quả (điền ở commit cuối nhánh task trước khi push/merge)
- Ngày xong:
- Nhánh / PR chính:
- Việc phát sinh hoặc còn tồn:
