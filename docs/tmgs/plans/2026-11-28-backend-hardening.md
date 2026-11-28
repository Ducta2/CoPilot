# Kế hoạch: củng cố backend SOC Core cho TMGS SOC Console

Ngày: 28/11/2026. Nhánh: `tmgs/backend-hardening` (worktree `/home/tmgs/projects/CoPilot-tmgs-backend`), tách từ `origin/feat/tmgs-frontend-v0.1.96` (06c1c80c, bản đang chạy trên staging).

Mục tiêu: sửa các lỗi 500 và rò rỉ secret đang thấy trên staging, đóng kết nối TLS bị rò, và bổ sung các API mà TMGS SOC Console đang chờ (knowledge, soc_requests, self service bộ cài EDR) theo đúng quy ước của mã nguồn hiện có.

Spec / nguồn sự thật (đọc phần liên quan, không đọc hết):

- Sổ tay quy ước backend: `/tmp/claude-1000/-home-tmgs/4ea2e671-46e0-4c0d-b85a-fbf2db693cdb/scratchpad/review/backend-patterns.md`
- Điều tra lỗi: `/tmp/claude-1000/-home-tmgs/4ea2e671-46e0-4c0d-b85a-fbf2db693cdb/scratchpad/review/backend-bugs.md`
- Hợp đồng API frontend cần: `/tmp/claude-1000/-home-tmgs/4ea2e671-46e0-4c0d-b85a-fbf2db693cdb/scratchpad/review/frontend-review.md` mục 4
- Thiết kế Self Service: `git show origin/feat/tmgs-self-service-api:docs/tmgs/self-service-api-design.md`

## Global Constraints

1. Nền là phiên bản 0.1.96. Không nâng cấp phụ thuộc, không sửa `frontend/`, `customer-portal/`, `docker-compose.yml`.
2. Đọc mã nhánh khác bằng `git show <ref>:<path>`; không checkout nhánh khác trong worktree này.
3. Lỗi trả về theo chuẩn của dự án: `HTTPException`, handler chung trả `{"success": false, "message": ...}`. Response thành công có `success` và `message`.
4. Thông báo lỗi mới trả cho người dùng **không chứa tên nền tảng** (Wazuh, Graylog, Shuffle, Velociraptor, CoPilot, SOCFortress, InfluxDB, Nuclei...) và không chứa host, URL nội bộ. Log nội bộ (loguru) thì được ghi chi tiết.
5. Migration Alembic dùng revision id riêng của TMGS, xếp nối tiếp đúng thứ tự sau, **không** dùng lại id của upstream:
   - knowledge: `7a6d5b0e1c01`, `down_revision = "d1195a7b3c4e"`
   - soc_requests: `7a6d5b0e1c02`, `down_revision = "7a6d5b0e1c01"`
   - self service: `7a6d5b0e1c03`, `down_revision = "7a6d5b0e1c02"`
   Sau mỗi task có migration, `alembic heads` chỉ có một head.
6. Không đưa secret, mật khẩu, token vào mã, test hay commit. Test dùng giá trị giả.
7. Lệnh test (từ thư mục `backend/` của worktree):
   ```
   S=/tmp/claude-1000/-home-tmgs/4ea2e671-46e0-4c0d-b85a-fbf2db693cdb/scratchpad
   JWT_SECRET=test-only-secret-not-the-compromised-default MYSQL_PASSWORD=x MYSQL_ROOT_PASSWORD=x \
     $S/venv-copilot/bin/python -m pytest <test files> -q -p no:cacheprovider
   ```
   Toàn bộ suite trên nền: 1716 passed, 4 failed (`test_redirect_slashes` 1, `test_soc_management_routes` 3, cần MySQL thật). Không được làm tăng số fail ngoài 4 test này.
8. Test theo phong cách sẵn có: không có conftest chung ở nền; async dùng `asyncio.run`; route test dùng SQLite trong bộ nhớ (`sqlite+aiosqlite`, StaticPool) + `app.dependency_overrides[get_db]`, giả đăng nhập bằng cách patch `AuthHandler.decode_token` / `_resolve_user`. Mỗi lỗi sửa phải có test tái hiện chạy đỏ trước khi sửa.
9. Commit nhỏ, thông điệp tiếng Việt, kết thúc bằng dòng:
   `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
   Git identity đã đặt sẵn trong worktree. Không push.
10. Scope hiện có: `admin`, `analyst`, `scheduler`, `customer_user`. Không có `responder`.
11. Điểm dễ vấp theo `CLAUDE.md` của repo: router mới cần **hai** chỗ (file trong `app/routers/` và import + `include_router` trong `backend/copilot.py`); **không sửa** `backend/app/routers/__init__.py` và `backend/app/db/all_models.py`; model đặt trong file model đã có (`universal_models.py`) thì không cần sửa `alembic/env.py`, đặt file mới thì phải import trong `env.py`; định dạng black line-length 140, isort `force_single_line`; route trong `customer_portal` bắt lỗi qua `routes/errors.py:internal_errors`, không đưa `str(e)` vào response; dùng `app/time_utils.py:now_utc()` thay `datetime.utcnow()`; `sqlmodel.Field` dùng `regex=`, Pydantic/FastAPI dùng `pattern=`.
12. Mỗi task thêm route có `customer_user` ghi dữ liệu phải cập nhật `ALLOWED_CUSTOMER_USER_WRITES` trong `tests/test_customer_user_write_allowlist.py` (nếu file này có trên nền) và chạy test đó.

## Task 1: Không trả secret của connector và tích hợp trong response

Bối cảnh: `GET /api/connectors` trả mật khẩu connector dạng rõ. Commit `a97d96f7` (nhánh local `fix/tmgs-connector-secrets`) đã sửa cho `/connectors`; báo cáo `backend-bugs.md` mục 5 chỉ ra các chỗ còn lộ.

Việc:

1. `git cherry-pick a97d96f7` vào nhánh này (giữ commit gốc; nếu xung đột thì giải quyết và ghi lại).
2. Áp cùng cách (schema public không có trường secret + cờ `<field>_set: bool`; khi cập nhật, trường secret bỏ trống hoặc không gửi thì giữ giá trị cũ) cho:
   - `GET /integrations/customer_integrations` và `/customer_integrations/{customer_code}` — trường `auth_value` trong `app/integrations/schema.py` (khoảng dòng 166). Xem các route PUT/POST tương ứng để giữ nguyên ngữ nghĩa cập nhật.
   - `GET /network_connectors/customer_network_connectors` và `/{customer_code}` — trường tương ứng.
   - `GET /customers/{customer_code}/meta` — `customer_meta_wazuh_auth_password` (`app/customers/schema/customers.py` khoảng dòng 162): thay bằng cờ `customer_meta_wazuh_auth_password_set`. Kiểm tra mọi nơi trong backend dùng schema response này để không làm hỏng luồng nội bộ (luồng nội bộ đọc từ DB model, không đọc response).
3. Trước khi đổi, grep repo frontend `/home/tmgs/projects/tmgs-soc-console/src` xem có đọc các trường secret này không; ghi kết quả vào báo cáo (không sửa frontend).
4. Ngoài phạm vi: credentials của Shuffle (`app/connectors/shuffle/routes/integrations.py:22`) — chỉ ghi chú trong báo cáo.

Test: với mỗi route GET ở trên, response không chứa giá trị secret đã lưu và có cờ `_set` đúng; cập nhật không gửi secret thì secret trong DB giữ nguyên; gửi secret mới thì đổi. Chạy kèm `backend/tests/test_connector_secrets_not_returned.py` từ commit cherry-pick.

## Task 2: Sửa ba endpoint trả 500

Chi tiết nguyên nhân ở `backend-bugs.md` lỗi 1, 2, 3.

1. **Alert chưa tạo**: route ở `app/incidents/routes/incident_alert.py` (khoảng dòng 99-106) khai báo `AlertsPayload` nhưng service `get_alerts_not_created_in_copilot` (`app/incidents/services/alert_collection.py` khoảng dòng 120,152) trả tuple `(AlertsPayload, int)`. Sửa ở route: unpack và trả phần tử đầu. Kiểm tra các nơi gọi khác của service để không làm vỡ.
2. **Metrics log collector** (`GET /graylog/metrics`): `app/connectors/graylog/services/monitoring.py` (khoảng dòng 98) truy cập cứng `["data"]["gauges"]`. Sửa: nếu phản hồi không thành công hoặc thiếu `data`/`gauges` thì ghi log cảnh báo (kèm mã HTTP, không kèm thân có thể chứa secret) và raise `HTTPException(502, "Không lấy được số liệu từ dịch vụ thu thập log")`. Không đổi hành vi khi dữ liệu đầy đủ. Không sửa `send_get_request` dùng chung (ghi chú rủi ro của nó trong báo cáo).
3. **Báo cáo đánh giá web** (`GET /nuclei/all_reports` và các route cùng service): `app/integrations/nuclei/services/nuclei.py` gọi `http://copilot-nuclei-module` không bắt lỗi mạng. Bắt `httpx` lỗi kết nối/timeout và phản hồi 5xx → `HTTPException(503, "Dịch vụ đánh giá web chưa sẵn sàng")`; JSON sai schema → 502. Ghi log chi tiết.

Test: mỗi lỗi một test tái hiện (mock service/HTTP client), đỏ trước sửa, xanh sau sửa; kèm test đường thành công không đổi.

## Task 3: Đóng client kho dữ liệu, chấm dứt rò kết nối TLS

Chi tiết ở `backend-bugs.md` lỗi 4. `create_wazuh_indexer_client_async` (`app/connectors/wazuh_indexer/utils/universal.py` khoảng dòng 118) tạo `AsyncElasticsearch` mới mỗi lần, các nơi gọi trong `app/incidents/services/alert_collection.py` (khoảng dòng 133, 181) và `app/incidents/routes/incident_alert.py` (khoảng dòng 213, 384) không `close()`. Job tạo alert tự động (`incident_alert.py` khoảng 247-340) gọi lặp cho từng alert.

Việc:

1. Thêm async context manager dùng chung (ví dụ `wazuh_indexer_client_async()` trong cùng module utils) đảm bảo `await client.close()` trong `finally`.
2. Chuyển các nơi gọi nêu trên sang context manager; trong vòng lặp tạo alert, tạo **một** client cho cả lượt và truyền xuống thay vì tạo cho từng alert (giữ chữ ký hàm cũ tương thích: tham số client tuỳ chọn).
3. Grep thêm các nơi khác gọi `create_wazuh_indexer_client_async` mà không đóng; sửa những chỗ nằm trong luồng job định kỳ, liệt kê phần còn lại trong báo cáo.

Test: mock `AsyncElasticsearch` đếm số lần khởi tạo và `close()`; luồng tạo alert tự động với N alert chỉ tạo 1 client và đóng đúng 1 lần, kể cả khi có ngoại lệ giữa chừng.

## Task 4: Backport Knowledge của khách hàng

Nguồn: `origin/main`. Chi tiết và bản thử đã chạy ở `backend-patterns.md` mục 2.3 và 3.1; bản sao thử ở `/tmp/claude-1000/-home-tmgs/4ea2e671-46e0-4c0d-b85a-fbf2db693cdb/scratchpad/src-kb/backend` (dùng để đối chiếu, không chép mù).

Việc:

1. Chép từ `origin/main`: `app/customer_knowledge/` (cả module), `app/routers/customer_knowledge.py`, hàm `to_naive_utc` vào `app/time_utils.py`, class `CustomerKnowledgeItem` vào `app/db/universal_models.py`, 3 action `CUSTOMER_KNOWLEDGE_*` vào `AuditAction`, test `tests/test_customer_knowledge.py`.
2. Bỏ phần phụ thuộc chỉ có trên main (`app/customers/services/section_status.py`, route Talon v2).
3. Đăng ký router trong `backend/copilot.py`.
4. Migration mới `7a6d5b0e1c01_add_customer_knowledge_item.py` (nội dung bảng như migration `c0d98a0b1c2d` của main, id và `down_revision` theo Global Constraints 5).
5. Hợp đồng frontend (frontend-review mục 4.2): `GET/POST/DELETE /api/customers/{code}/knowledge[/{id}]`, response list có `items`, POST có `warnings`. Đối chiếu tên trường với `KnowledgeItem` của frontend, ghi chênh lệch (nếu có) vào báo cáo, không đổi hợp đồng của main.

Test: `tests/test_customer_knowledge.py` qua (ngoại lệ chấp nhận: `test_a_time_zone_is_an_iana_name[US/Mountain]` do tzdata máy thiếu alias — ghi rõ). Nếu test cần fixture audit thì đặt conftest/fixture cục bộ cho file test đó như bản thử, không thêm conftest toàn cục.

## Task 5: Backport "Hỏi SOC" (soc_requests)

Nguồn: `origin/main`. Chi tiết ở `backend-patterns.md` mục 3.2.

Việc:

1. Chép `app/customer_portal/routes/soc_requests.py`, `services/soc_requests.py`, `services/soc_request_answers.py`, `schema/soc_requests.py`, hai model `CustomerPortalSocRequestSettings` và `CustomerPortalSocRequest`, 3 `AuditAction` `SOC_REQUEST_*`, test tương ứng; đăng ký route dưới router `customer_portal` hiện có.
2. Phụ thuộc chưa có trên nền:
   - `read_only`: thêm `app/auth/services/read_only.py` tối giản với `READ_ONLY` và `is_read_only_for(...)` luôn trả `False` (ghi docstring: tạm thời cho tới khi có cột `read_only`). Không thêm cột DB.
   - `SOC_ROLES`: định nghĩa `{admin, analyst}` cạnh `RoleEnum` hiện có.
   - Thông báo `CUSTOMER_QUESTION`: chỉ backport nếu ≤ 3 file notifications cần chỉnh và không cần migration; nếu không, gọi qua một hàm `emit` an toàn bỏ qua khi trigger chưa có (log debug). Ghi lựa chọn vào báo cáo.
   - Hook đánh dấu đã trả lời khi SOC bình luận (`incidents/routes/db_operations.py`, `mark_answered_by_comment`): backport phần gọi hook, bọc try/except để lỗi hook không làm hỏng việc tạo comment.
3. Migration `7a6d5b0e1c02_add_customer_portal_soc_requests.py` theo Global Constraints 5.
4. Hợp đồng frontend (frontend-review mục 4.3): `GET /customer_portal/soc_requests` trả `requests`, `total`, `open`; `POST /customer_portal/soc_requests/{id}/answered`. Đối chiếu và ghi chênh lệch.
5. Ngoài phạm vi: `/customer_portal/activity/settings/*` (không có trên main) — ghi chú.

Test: test của main cho soc_requests qua trên nền (bỏ test e2e cần dịch vụ ngoài, ghi rõ); thêm test: analyst chỉ thấy yêu cầu của khách hàng mình được phép; lỗi hook không chặn tạo comment.

## Task 6: Self Service — bộ cài EDR (Mức 1)

Thiết kế: `git show origin/feat/tmgs-self-service-api:docs/tmgs/self-service-api-design.md` mục 2–6, 8–9, chỉ phần **bộ cài EDR**. Quyết định đã chốt (28/11/2026):

- `customer_user` được tự tạo và thu hồi bộ cài của khách hàng mình (cùng admin, analyst).
- Mức 1: chỉ lưu bản ghi; hạn dùng và số máy **chưa cưỡng chế** ở máy chủ giám sát. Response có trường `enforced: false` để giao diện ghi rõ.
- Hạn mức chung: biến môi trường `SELF_SERVICE_EDR_INSTALL_QUOTA`, mặc định `1000`.
- **Sensor hoãn lại**: không tạo bảng, route hay model Sensor.

Việc:

1. Module `app/self_service/` (routes/schema/services) theo bố cục của thiết kế mục 2, chỉ phần edr_packages; router `app/routers/self_service.py` prefix `/self_service`, đăng ký trong `copilot.py`.
2. Model `SelfServiceEdrPackage` (bảng `self_service_edr_packages`) như thiết kế mục 3; `status` tính khi đọc.
3. Route: `GET /api/self_service/edr_packages?customer_code=`, `POST /api/self_service/edr_packages`, `DELETE /api/self_service/edr_packages/{package_id}` với phân quyền và quy tắc nghiệp vụ ở thiết kế mục 5 (404 thay vì 403 cho bản ghi khác khách hàng; 409 khi vượt hạn mức; thu hồi mềm, idempotent; audit cho POST/DELETE; giới hạn tần suất 10 lần/phút/người dùng cho POST, cài trong service như quy ước sổ tay mục 1.12).
4. Trường response khớp kiểu `EdrPackage` của frontend (frontend-review mục 4.1) cộng `enforced`.
5. Cập nhật `enrolled` (thiết kế mục 6) **chưa làm** ở đợt này; giữ 0 và ghi chú.
6. Migration `7a6d5b0e1c03_add_self_service_edr_packages.py` theo Global Constraints 5.

Test: tính `status`; hạn mức 409; người dùng khách hàng A không xem/thu hồi được bộ cài của B (404); thu hồi idempotent; scope không hợp lệ bị chặn; rate limit; validate đầu vào (platform, arch, group, max_installs, valid_days).

## Task 7: Kiểm tra tổng và tài liệu thay đổi

1. Chạy toàn bộ suite theo Global Constraints 7; số fail chỉ gồm 4 test đã biết (cộng test tz US/Mountain nếu có), ghi con số.
2. `alembic -c alembic/alembic.ini heads` ra đúng một head `7a6d5b0e1c03`; `alembic history` thể hiện chuỗi `d1195a7b3c4e → 7a6d5b0e1c01 → 7a6d5b0e1c02 → 7a6d5b0e1c03`.
3. `python -c "import copilot"` (với biến môi trường test) import được, và danh sách route của app có đủ route mới.
4. Viết `docs/tmgs/backend-changes.md` (tiếng Việt): danh sách thay đổi theo task, route mới (method, path, scope), migration, việc cần làm khi deploy (rebuild image backend, migration tự chạy lúc khởi động), giới hạn đã biết (Mức 1, Sensor hoãn, activity settings, Shuffle credentials, `send_get_request`), và việc cần lấy trên staging (mục cuối `backend-bugs.md`).
