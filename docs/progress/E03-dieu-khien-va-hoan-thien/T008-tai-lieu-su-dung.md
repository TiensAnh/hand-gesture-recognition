# T008 - Tài liệu hướng dẫn sử dụng và kiểm thử tổng thể

Cập nhật: 2026-11-25
Epic: E03
Spec: không có
Nhánh: `docs/tai-lieu-su-dung`
Phụ thuộc: T007

## Mục tiêu
- Hoàn thiện `README.md` đầy đủ hướng dẫn cài đặt, chạy ứng dụng, thu thập dữ liệu, huấn luyện mô hình, chạy lint/test và rà soát kiểm thử toàn bộ luồng.

## Phạm vi (lát cắt dọc)
- Tài liệu: `README.md` mô tả bài toán, kiến trúc module, cấu trúc thư mục, lệnh cài đặt/chạy/huấn luyện/test và danh sách 7 cử chỉ hỗ trợ.
- Rà soát: kiểm tra `docs/spec.md` khớp thực tế code, chạy lại toàn bộ `ruff check .` và `pytest`.

## Xong khi (kiểm tra được bằng chạy hoặc test)
- [ ] `README.md` có đầy đủ hướng dẫn để người khác clone repo về cài đặt và chạy được.
- [ ] `docs/spec.md` khớp với cấu trúc thư mục và lệnh chạy thực tế.
- [ ] `ruff check .` và `pytest` đều đạt.

## Ghi chú
- Cập nhật trạng thái hoàn tất sau khi kiểm thử thủ công toàn bộ luồng từ đầu đến cuối.

## Kết quả (điền ở commit cuối nhánh task trước khi push/merge)
- Ngày xong:
- Nhánh / PR chính:
- Việc phát sinh hoặc còn tồn:
