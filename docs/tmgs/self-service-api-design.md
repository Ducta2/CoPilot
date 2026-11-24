# Thiết kế API SOC Self Service (TMGS)

Trạng thái: **đề xuất, chưa cài đặt**. Tài liệu này mô tả router FastAPI cần thêm để hai trang "Bộ cài EDR Agent" và "Bộ cài TMGS Sensor" của TMGS SOC Console hoạt động. Frontend tương ứng: `Ducta2/tmgs-soc-console`, `src/lib/api3.ts` (`api3.selfService`) và `src/pages/SelfService.tsx`. Hai cờ `FEATURES.edrPackages` và `FEATURES.sensors` trong `src/lib/features.ts` đang tắt cho tới khi API này có mặt.

## 1. Phạm vi

| Route | Mục đích |
|---|---|
| `GET /api/self_service/edr_packages?customer_code=` | Liệt kê bộ cài EDR đã tạo của một khách hàng |
| `POST /api/self_service/edr_packages` | Tạo bộ cài EDR (nền tảng, nhóm, hạn dùng, số máy tối đa) |
| `DELETE /api/self_service/edr_packages/{package_id}` | Thu hồi bộ cài |
| `GET /api/self_service/sensors?customer_code=` | Liệt kê yêu cầu Sensor của một khách hàng |
| `POST /api/self_service/sensors` | Tạo yêu cầu dựng image Sensor |
| `POST /api/self_service/sensors/{sensor_id}/activation` | Cấp mã kích hoạt dùng một lần |

Ngoài phạm vi đợt đầu: dựng image Sensor thật (cần pipeline build riêng), tải image qua backend, đếm EPS và heartbeat của Sensor. Các phần này được chừa chỗ trong model và mô tả ở mục 7.

## 2. Bố cục mã

Theo đúng quy ước module hiện có (ví dụ `app/customer_waf`):

```
backend/app/self_service/
  routes/edr_packages.py      # self_service_edr_router
  routes/sensors.py           # self_service_sensors_router
  schema/edr_packages.py
  schema/sensors.py
  services/edr_packages.py
  services/sensors.py
  services/tokens.py          # sinh và băm mã kích hoạt
backend/app/routers/self_service.py   # router.include_router(..., prefix="/self_service")
backend/copilot.py                    # api_router.include_router(self_service.router)
backend/app/db/universal_models.py    # hai bảng mới
backend/alembic/versions/<rev>_add_self_service_tables.py
backend/tests/self_service/
```

## 3. Model (SQLModel, `universal_models.py`)

### `SelfServiceEdrPackage` — bảng `self_service_edr_packages`

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | `str(20)` PK | Dạng `PKG-` + 8 ký tự base32 ngẫu nhiên (`secrets`); frontend hiển thị mã này |
| `customer_code` | `str(11)` FK `customers.customer_code` `ON DELETE CASCADE`, index | |
| `platform` | `str(16)` | `windows` \| `linux` \| `macos` |
| `arch` | `str(16)` | `x64` \| `arm64` \| `x86` |
| `group` | `str(64)` | Nhóm tài sản; mặc định bằng `customer_code` |
| `max_installs` | `int` | 1–500 |
| `enrolled` | `int` default 0 | Số agent đã đăng ký qua bộ cài này (xem mục 6) |
| `created_by` | `str(64)` | `username` của người tạo |
| `created_at` | `datetime` UTC | |
| `expires_at` | `datetime` UTC | `created_at + valid_days` |
| `revoked_at` | `datetime` null | |
| `revoked_by` | `str(64)` null | |

`status` không lưu: tính khi đọc (`revoked` nếu có `revoked_at`, `expired` nếu quá `expires_at`, còn lại `active`). Nhờ vậy không cần tác vụ định kỳ để đổi trạng thái.

### `SelfServiceSensor` — bảng `self_service_sensors`

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | `str(20)` PK | Dạng `SEN-` + 8 ký tự |
| `customer_code` | FK như trên, index | |
| `name` | `str(41)` | `^[a-z0-9][a-z0-9-]{2,40}$`; unique theo `(customer_code, name)` |
| `site` | `str(128)` | |
| `hypervisor` | `str(16)` | `vmware` \| `hyperv` \| `kvm` \| `iso` |
| `size` | `str(1)` | `s` \| `m` \| `l` |
| `network` | `JSON` | `{mode, ip?, gateway?, dns?}` |
| `sources` | `JSON` | Danh sách `syslog_udp`, `syslog_tcp`, `syslog_tls`, `netflow`, `span` |
| `state` | `str(16)` | `building` \| `ready` \| `verifying` \| `online` \| `failed` |
| `image_file`, `image_size_mb`, `image_sha256`, `image_expires_at` | null | Điền khi pipeline dựng xong |
| `activation_hash` | `str(64)` null | SHA-256 của mã kích hoạt; **không lưu mã dạng rõ** |
| `activation_expires_at` | `datetime` null | |
| `eps`, `last_seen` | null | Do Sensor báo về (mục 7) |
| `created_by`, `created_at` | | |

## 4. Schema (Pydantic)

Tên trường khớp đúng kiểu `EdrPackage` và `SensorRequest` của frontend để không phải đổi giao diện.

```python
class EdrPlatform(str, Enum): windows = "windows"; linux = "linux"; macos = "macos"

class EdrPackageCreate(BaseModel):
    customer_code: str
    platform: EdrPlatform
    arch: Literal["x64", "arm64", "x86"]
    group: str = Field(pattern=r"^[A-Za-z0-9_-]{1,40}$")
    max_installs: int = Field(ge=1, le=500)
    valid_days: Literal[1, 7, 30]

class EdrPackageOut(BaseModel):
    id: str; customer_code: str; platform: EdrPlatform; arch: str; group: str
    created_by: str; created_at: datetime; expires_at: datetime
    max_installs: int; enrolled: int
    status: Literal["active", "expired", "revoked"]

class EdrPackageListResponse(BaseModel):   # {packages, success, message}
class EdrPackageResponse(BaseModel):       # {package, success, message}

class SensorNetwork(BaseModel):
    mode: Literal["dhcp", "static"]
    ip: Optional[IPvAnyInterface] = None
    gateway: Optional[IPvAnyAddress] = None
    dns: Optional[IPvAnyAddress] = None
    # model_validator: mode == "static" thì bắt buộc đủ ip, gateway, dns

class SensorCreate(BaseModel):
    customer_code: str
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,40}$")
    site: str = Field(min_length=1, max_length=128)
    hypervisor: Literal["vmware", "hyperv", "kvm", "iso"]
    size: Literal["s", "m", "l"]
    network: SensorNetwork
    sources: List[Literal["syslog_udp", "syslog_tcp", "syslog_tls", "netflow", "span"]] = Field(min_length=1)

class SensorOut(BaseModel):                # như SensorRequest của frontend; image là object lồng hoặc null
class SensorListResponse(BaseModel):       # {sensors, success, message}
class SensorResponse(BaseModel):           # {sensor, success, message}
class SensorActivationResponse(BaseModel): # {activation_code, expires_at, success, message}
```

## 5. Route và phân quyền

Dùng lại cơ chế sẵn có: `AuthHandler().require_any_scope(...)` và kiểm tra quyền theo khách hàng (`customer_access_handler.check_customer_access`). `verify_customer_code_access` chỉ đọc `customer_code` từ path, nên với route nhận `customer_code` ở query hoặc body thì gọi `check_customer_access` trong hàm xử lý; route theo id thì nạp bản ghi trước rồi kiểm tra `customer_code` của bản ghi.

| Route | Scope | Kiểm tra khách hàng | Audit |
|---|---|---|---|
| `GET /edr_packages` | admin, analyst, customer_user | theo `customer_code` ở query (bắt buộc) | không |
| `POST /edr_packages` | admin, analyst, customer_user | theo `customer_code` ở body | có |
| `DELETE /edr_packages/{id}` | admin, analyst, customer_user | theo bản ghi | có |
| `GET /sensors` | admin, analyst, customer_user | theo query | không |
| `POST /sensors` | admin, analyst, customer_user | theo body | có |
| `POST /sensors/{id}/activation` | admin, analyst, customer_user | theo bản ghi | có |

Quy tắc nghiệp vụ:

- Bản ghi không thuộc khách hàng người gọi được phép xem: trả **404**, không trả 403, để không lộ sự tồn tại của mã bộ cài.
- `POST /edr_packages`: từ chối (409) nếu tổng `max_installs - enrolled` của các bộ cài đang hiệu lực vượt hạn mức của khách hàng (hằng số cấu hình, mặc định 1000).
- `DELETE /edr_packages/{id}`: thu hồi mềm (đặt `revoked_at`), idempotent; không xoá bản ghi để giữ lịch sử.
- `POST /sensors/{id}/activation`: chỉ cho phép khi `state` là `ready` hoặc `verifying`; mỗi lần gọi sinh mã mới và làm mất hiệu lực mã cũ. Mã 24 ký tự từ `secrets.token_urlsafe`, hạn 30 phút, chỉ trả một lần trong response, cơ sở dữ liệu chỉ lưu SHA-256.
- Giới hạn tần suất cho hai lệnh POST tạo mới (ví dụ 10 lần/phút mỗi người dùng) để tránh lạm dụng.

## 6. Quan hệ với lệnh cài EDR hiện có

`GET /api/customer_provisioning/edr_install_commands/{customer_code}` hiện sinh lệnh cài dùng **mật khẩu đăng ký chung của khách hàng**. Vì vậy bộ cài ở đợt đầu chỉ là bản ghi quản lý; hạn dùng và số máy tối đa **chưa được cưỡng chế** ở phía máy chủ giám sát. Có hai mức:

- **Mức 1 (đợt đầu):** lưu bản ghi bộ cài, frontend lấy lệnh qua route hiện có. `enrolled` được cập nhật trong tác vụ `agent_sync`: đếm agent của khách hàng thuộc nhóm `group` và có ngày đăng ký sau `created_at`. Thu hồi chỉ ẩn lệnh trên giao diện. Phải ghi rõ giới hạn này trên giao diện.
- **Mức 2:** cưỡng chế thật. Mỗi bộ cài có khoá đăng ký riêng; khi thu hồi hoặc hết hạn thì khoá bị vô hiệu ở máy chủ giám sát. Cần khảo sát khả năng của máy chủ giám sát (khoá đăng ký theo nhóm hoặc đổi mật khẩu đăng ký) trước khi cam kết.

Đề nghị thêm tham số tuỳ chọn `package_id` vào route lệnh cài ở Mức 2, để lệnh trả về gắn với nhóm và khoá của bộ cài.

## 7. Sensor: phần chừa lại

- Dựng image: `POST /sensors` tạo bản ghi `state=building` rồi đẩy việc cho pipeline build (chưa có). Đợt đầu có thể để `state=building` và quản trị viên TMGS cập nhật thủ công; khi đó cần thêm route chỉ admin `PATCH /sensors/{id}` để đặt `state` và thông tin image.
- Tải image: nên dùng URL ký sẵn có hạn từ kho đối tượng sẵn có, không phát file qua backend.
- Kích hoạt và heartbeat từ Sensor: route riêng không dùng JWT người dùng, xác thực bằng mã kích hoạt rồi bằng khoá thiết bị. Thiết kế ở tài liệu khác.

## 8. Migration

Một revision Alembic tạo hai bảng, index trên `customer_code`, unique `(customer_code, name)` cho Sensor. Không sửa bảng hiện có. `downgrade` xoá hai bảng.

## 9. Kiểm thử

- Đơn vị: tính `status`, hạn mức, sinh và băm mã kích hoạt, validator mạng.
- Route (pytest + httpx, theo `backend/tests`): phân quyền theo scope; người dùng của khách hàng A không đọc, thu hồi hay lấy mã kích hoạt của khách hàng B (mong đợi 404); thu hồi idempotent; mã kích hoạt cũ mất hiệu lực khi cấp mã mới.

## 10. Bí danh ở cổng TMGS

Tiền tố `/api/self_service` không chứa tên nền tảng nên không cần bí danh trong `nginx.conf`, `install-docker.sh` và `tmgs_gateway.py` của `tmgs-soc-console`.

## 11. Câu hỏi cần chốt

1. `customer_user` có được tự tạo bộ cài và Sensor không, hay chỉ admin và analyst của TMGS? Bảng ở mục 5 đang giả định là có, vì đây là tính năng tự phục vụ.
2. Chấp nhận Mức 1 cho bộ cài EDR (không cưỡng chế hạn dùng) ở đợt đầu không?
3. Pipeline dựng image Sensor do ai làm và đặt ở đâu?
4. Hạn mức lượt cài mỗi khách hàng: hằng số chung hay theo hợp đồng?
