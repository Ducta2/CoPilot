# Thiết kế TMGS SOC

Logo lấy nguyên tệp từ website TMGS. Trang công ty sử dụng Be Vietnam Pro. `#ED3237` xuất hiện trong tệp logo. Các màu vận hành bên dưới được chọn cho ứng dụng SOC. Nguồn [logo TMGS](https://tmgs.vn/image/tmgs.svg), [website TMGS](https://tmgs.vn/) và [TMGS Malware Analysis](https://malware.tmgs.vn/).

| Vai trò | Sáng | Tối |
| --- | --- | --- |
| Nền workspace | `#EEF2F7` | `#0D1522` |
| Surface | `#FFFFFF` | `#172233` |
| Chữ chính | `#162235` | `#F2F5FA` |
| Viền | `#CCD6E3` | `#344559` |
| Màu tương tác | `#2256A5` | `#80B6F4` |

Màu đỏ của logo làm dấu nhận diện. Tông xanh dùng cho điều hướng và nút chính. Token trạng thái riêng phục vụ các mức cảnh báo và nhãn trạng thái hiện hữu. Dùng Be Vietnam Pro cục bộ và font monospace hiện hữu cho nội dung kỹ thuật.

- Core dùng thanh điều hướng dọc và toolbar hiện hữu. Logo, breadcrumb, thao tác tài khoản và scope khách hàng nằm ở các vùng quen thuộc. Overview làm nổi thứ bậc giữa tiêu đề, điều khiển scope và số liệu vận hành.
- Trên màn hình nhỏ, dùng điểm ngắt của app và menu hiện hữu. Nút mở menu có thể thao tác bằng bàn phím. Kích thước bảng và biểu mẫu theo component hiện hữu.
- Màn hình đăng nhập dùng khối nhận diện tĩnh, form và các nhánh đăng nhập của CoPilot. Portal ưu tiên logo/tên cấu hình từ backend, dùng TMGS SOC khi chưa có thương hiệu riêng.
- Core dùng Vue I18n hiện hữu cho chuỗi mới, giữ lựa chọn tiếng Anh. Portal tiếp tục tuân theo cấu hình ngôn ngữ mà backend cung cấp. Nội dung log, enum, identifier, tên trường và dữ liệu tenant giữ dạng gốc.

## Trình tự thực hiện

1. Chạy baseline frozen lockfile, build, unit, lint chỉ đọc và thử browser fixture.
2. Áp dụng token, logo, shell và focus state trên hai app. Giữ nguyên các handler và hợp đồng API.
3. Kiểm tra Overview, đăng nhập, tenant scope, điều hướng và mobile. So sánh request trước/sau bằng fixture giống nhau.
4. Đóng gói dist và chuẩn bị image riêng bằng Dockerfile của từng app. So sánh diff và mở draft PR vào nhánh baseline staging.
