# Thay đổi backend đợt gia cố (nhánh tmgs/backend-hardening)

Nền: phiên bản 0.1.96. Tài liệu này dành cho trưởng nhóm SOC: nói rõ đã đổi gì, route nào mới, cần làm gì khi triển khai và còn gì chưa làm.

## 1. Tóm tắt

- Backend không còn trả mật khẩu, khoá API của kết nối trong response. Quản trị viên vẫn thấy cờ "đã đặt" nhưng không đọc lại được giá trị.
- Ba route trước đây trả lỗi 500 nay chạy đúng hoặc trả lỗi 502/503 có thông báo rõ ràng.
- Job tạo alert tự động nay đóng kết nối tới kho dữ liệu sau mỗi lượt, chấm dứt rò kết nối (nguyên nhân của dòng log "SSL shutdown timed out").
- Thêm ba tính năng cho Console: Knowledge của khách hàng, Hỏi SOC (khách hỏi về alert hoặc case), Self Service bộ cài EDR (Mức 1).
- Thêm ba migration nối tiếp nhau, chạy tự động khi backend khởi động. Cần rebuild image backend.

Kết quả kiểm tra cuối: toàn bộ suite 2081 đạt, 5 lỗi đều đã biết và không do đợt này (mục 7).

## 2. Thay đổi theo nhóm

### 2.1 Bảo mật

- Connector: response không còn mật khẩu và khoá API.
- Tích hợp và kết nối mạng của khách hàng: giá trị `auth_value` không còn trong response, thay bằng cờ `auth_value_set`. Áp dụng cho các route GET danh sách.
- Meta khách hàng: mật khẩu đăng ký không còn trong response, thay bằng cờ `customer_meta_wazuh_auth_password_set`. Áp dụng cho mọi route trả dữ liệu meta.
- Khi cập nhật tích hợp hoặc kết nối mạng, gửi giá trị rỗng nghĩa là giữ nguyên giá trị cũ. Muốn đổi thì gửi giá trị mới. Hiện không có cách xoá secret qua API.
- Sửa kèm: cập nhật kết nối mạng trước đây luôn lỗi do sai tên thuộc tính.
- Thông báo lỗi mới trả cho người dùng không chứa tên nền tảng, địa chỉ hay thân phản hồi nội bộ; chi tiết chỉ nằm trong log.

### 2.2 Lỗi 500 đã sửa

| Route | Trước | Sau |
|---|---|---|
| `GET /api/incidents/alerts/alerts/not-created` | 500 do route không tách kết quả trả về từ service | 200 với danh sách alert |
| `GET /api/graylog/metrics` | 500 khi phản hồi thiếu số liệu | 502 "Không lấy được số liệu từ dịch vụ thu thập log" |
| Nhóm route đánh giá web `/api/nuclei/...` (danh sách báo cáo, báo cáo theo máy, quét, xoá) | 500 khi dịch vụ không phản hồi hoặc trả dữ liệu sai | 503 "Dịch vụ đánh giá web chưa sẵn sàng" khi lỗi mạng hoặc 5xx; 502 khi dữ liệu không hợp lệ; 404 giữ nguyên |

### 2.3 Rò kết nối

Job tạo alert tự động mở kết nối tới kho dữ liệu mỗi lượt nhưng không đóng, nên kết nối TLS tồn đọng và log đầy dòng "SSL shutdown timed out". Nay client được đóng sau mỗi lượt, kể cả khi lỗi giữa chừng.

### 2.4 Tính năng mới

- **Knowledge của khách hàng**: ghi chú tri thức theo từng khách (thêm, sửa, xoá, xem). Dành cho `admin`, `analyst`.
- **Hỏi SOC**: khách hàng gửi câu hỏi về một alert hoặc case; SOC xem danh sách, bật tắt tính năng theo khách và đặt hạn mức hỏi mỗi ngày. Khi SOC bình luận vào alert hoặc case có câu hỏi đang mở, câu hỏi tự chuyển sang "đã trả lời". Lỗi ở bước đánh dấu này không chặn việc tạo bình luận.
- **Self Service bộ cài EDR (Mức 1)**: người dùng khách tạo gói cài EDR có hạn 1, 7 hoặc 30 ngày, xem danh sách và thu hồi. Mức 1 nghĩa là chỉ ghi nhận gói, chưa cưỡng chế gì trên máy.

## 3. Route mới

Tất cả nằm dưới tiền tố `/api`. Scope hiện có: `admin`, `analyst`, `scheduler`, `customer_user`.

| Method | Path | Scope | Ghi chú |
|---|---|---|---|
| GET | `/customers/{customer_code}/knowledge` | admin, analyst | Danh sách ghi chú của khách |
| POST | `/customers/{customer_code}/knowledge` | admin, analyst | Thêm ghi chú |
| PUT | `/customers/{customer_code}/knowledge/{item_id}` | admin, analyst | Sửa ghi chú |
| DELETE | `/customers/{customer_code}/knowledge/{item_id}` | admin, analyst | Xoá ghi chú |
| GET | `/customer_portal/soc_requests/settings/{customer_code}` | admin, analyst | Xem bật/tắt và hạn mức hỏi mỗi ngày |
| PUT | `/customer_portal/soc_requests/settings/{customer_code}` | admin | Bật/tắt, đặt hạn mức (null là không giới hạn); có ghi audit |
| GET | `/customer_portal/soc_requests/availability` | admin, analyst, customer_user | Giao diện có hiện nút Hỏi SOC hay không |
| GET | `/customer_portal/soc_requests/alert/{alert_id}` | customer_user | Câu hỏi của chính khách về một alert |
| POST | `/customer_portal/soc_requests/alert/{alert_id}` | customer_user | Gửi câu hỏi về alert |
| GET | `/customer_portal/soc_requests/case/{case_id}` | customer_user | Câu hỏi của khách về một case |
| POST | `/customer_portal/soc_requests/case/{case_id}` | customer_user | Gửi câu hỏi về case |
| GET | `/customer_portal/soc_requests` | admin, analyst | Danh sách mọi câu hỏi trong phạm vi khách của người xem; có `total` và `open` |
| POST | `/customer_portal/soc_requests/{request_id}/answered` | admin, analyst | Đánh dấu đã trả lời (lặp lại không lỗi) |
| GET | `/self_service/edr_packages` | admin, analyst, customer_user | Danh sách gói cài EDR |
| POST | `/self_service/edr_packages` | admin, analyst, customer_user | Tạo gói (`valid_days` là 1, 7 hoặc 30). 429 nếu một người tạo quá 10 gói trong một khoảng ngắn, 409 nếu vượt quota |
| DELETE | `/self_service/edr_packages/{package_id}` | admin, analyst, customer_user | Thu hồi gói; thu hồi lại gói đã thu hồi không ghi audit lần nữa |

Khách ngoài phạm vi của người gọi luôn nhận 404 thay vì 403. Hai route ghi của `customer_user` (POST và DELETE edr_packages) và hai route POST hỏi SOC đã được thêm vào danh sách cho phép trong test kiểm soát quyền ghi.

## 4. Migration

Ba migration của TMGS, dùng id riêng, nối vào bản gốc `d1195a7b3c4e`:

```
d1195a7b3c4e -> 7a6d5b0e1c01 (bảng customer_knowledge_item)
             -> 7a6d5b0e1c02 (bảng Hỏi SOC và công tắc theo khách)
             -> 7a6d5b0e1c03 (bảng self_service_edr_packages)  (head)
```

`alembic heads` chỉ có một head: `7a6d5b0e1c03`.

## 5. Việc cần làm khi triển khai

1. Rebuild image backend rồi khởi động lại. Migration tự chạy lúc backend khởi động, không cần chạy tay.
2. Biến môi trường mới `SELF_SERVICE_EDR_INSTALL_QUOTA`: số gói đang hiệu lực tối đa mỗi khách, mặc định 1000. Giá trị sai hoặc âm tự quay về 1000 và ghi cảnh báo. Đã có trong `.env.example`; đặt vào `.env` thật nếu muốn đổi.
3. Kiểm tra sau triển khai:
   - Dòng log "SSL shutdown timed out" giảm rõ rệt sau vài lượt của job tạo alert tự động.
   - Các route trước đây 500 (mục 2.2) không còn 500: gọi thử từng route, kết quả phải là 200, 502 hoặc 503 có thông báo tiếng Việt.
   - Các route GET tích hợp, kết nối mạng, meta khách không còn trường mật khẩu hay `auth_value`.
   - `alembic current` trên cơ sở dữ liệu ra `7a6d5b0e1c03`.

## 6. Giới hạn đã biết

- Self Service Mức 1 chỉ ghi nhận gói, chưa cưỡng chế. Quota không khoá hàng và bộ giới hạn tốc độ nằm trong tiến trình: hai yêu cầu đồng thời có thể vượt quota một lần; chạy nhiều worker thì giới hạn thực tế là 10 nhân số worker và khởi động lại sẽ xoá bộ đếm.
- Sensor (Self Service) hoãn, chưa có route.
- Cài đặt hoạt động (activity settings) của cổng khách chưa có: bản chính cũng chưa có. Một tab trên cổng vẫn ẩn.
- Tự động hoá AI (Talon v2) chưa làm: cần nâng nền hoặc dịch vụ phân tích; tính năng này vẫn ẩn trên giao diện.
- Khoá API của hệ thống điều phối tự động (Shuffle) vẫn đọc được bởi quản trị viên theo thiết kế cũ.
- Hỏi SOC: thông báo cho SOC khi khách hỏi chưa có (hàm gửi thông báo hiện không làm gì ngoài ghi log); SOC xem danh sách trên Console. Cấu trúc bảng lấy từ bản trước khi có Talon chat, nên khi nâng nền lên bản chính cần thêm migration cột.
- Nâng nền lên bản chính cần migration hợp nhất, vì `7a6d5b0e1c01` và migration của bản chính cùng tạo bảng `customer_knowledge_item`.
- Không có cách xoá secret của tích hợp hoặc kết nối mạng qua API (gửi rỗng là giữ cũ).
- Log cảnh báo số liệu thu thập log không có mã HTTP vì hàm gửi GET dùng chung bỏ mất mã; chẩn đoán trên staging phải xem log khác.

## 7. Kết quả kiểm thử đã biết lỗi

Năm test lỗi, đều không do đợt này:

- `test_redirect_slashes` (1) và `test_soc_management_routes` (3): cần cơ sở dữ liệu MySQL thật.
- `test_a_time_zone_is_an_iana_name[US/Mountain]` (1): máy thiếu bí danh múi giờ trong tzdata.

## 8. Việc còn mở

Nhỏ, chưa sửa, nên làm khi có dịp:

- Mật khẩu đăng ký ở route cập nhật meta cũ (đã deprecated): vì trường này vẫn bắt buộc và GET không còn trả, gửi rỗng sẽ ghi đè mật khẩu đã lưu. Cần xem lại.
- Dịch vụ đánh giá web còn vài thông báo 404 cũ có tên nền tảng. Journal thu thập log thành công nhưng thiếu trường vẫn có thể 500.
- Rò kết nối mới được sửa ở job tạo alert tự động; còn sáu nơi gọi theo request chưa đóng client kho dữ liệu (agents vulnerabilities, velo_sigma, case_tasks, mitre, hai nơi trong wazuh_indexer alerts).
- Self Service: audit ghi trạng thái cũ tự tính; bộ giới hạn không dọn khoá rỗng; thiếu test cho analyst được gán bị từ chối khách khác; vài test dùng `datetime.utcnow()`.
- Hỏi SOC: thiếu test nhánh rollback của hook đánh dấu đã trả lời; mô tả OpenAPI còn nhắc tên nền tảng.
- Knowledge: ba action audit nằm giữa nhóm Authentication, nên dời xuống cuối để dễ hợp nhất với bản chính.
- Test: định dạng lại `test_integration_secrets_not_returned.py` theo cấu hình isort của repo; đổi tên một test cho đúng nghĩa.

## 9. Việc cần lấy trên staging

- Lỗi metrics: thân phản hồi `/api/graylog/metrics` bằng tài khoản connector, phiên bản dịch vụ thu thập log, log backend lúc lỗi, cấu hình proxy cho đường ingest metrics.
- Lỗi đánh giá web: traceback đầy đủ (lớp lỗi) và trạng thái container của module đánh giá web.
- Lỗi rò kết nối: interval các job trong bảng job scheduler, log quanh chuỗi "SSL shutdown timed out" (job nào chạy trước đó), số alert xử lý mỗi lượt.
- Lỗi alert chưa tạo: không cần thêm log; xác nhận bằng traceback `ResponseValidationError` trong log backend.
