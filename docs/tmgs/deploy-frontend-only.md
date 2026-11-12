# Build và chuẩn bị thay frontend

## Bản xem thử trên localhost

Node 24, corepack và pnpm theo `packageManager` của từng thư mục. Chạy lệnh từ checkout của nhánh staging đã được duyệt.

```sh
cd frontend
corepack pnpm install --frozen-lockfile
corepack pnpm run build
cd ../customer-portal
corepack pnpm install --frozen-lockfile
corepack pnpm run build
cd ..
```

Mở hai terminal tại gốc repo, chạy một lệnh mỗi terminal rồi mở đường dẫn `/login`. Preview chỉ lắng nghe loopback và trả HTTP 503 cho `/api` khi chạy ngoài browser test. Các fixture thuộc bộ kiểm thử và được gắn ở tầng trình duyệt.

```sh
node docs/tmgs/preview.mjs frontend/dist 4173
node docs/tmgs/preview.mjs customer-portal/dist 4174
```

## Build hai image mang nhãn riêng

Từ gốc checkout, dùng Docker Linux đang hoạt động. Lấy tag từ SHA của checkout đã duyệt. Hai build context độc lập sử dụng Dockerfile, lockfile, entrypoint SSL và template Nginx của baseline. Xác minh trạng thái sạch của checkout trước khi gắn nhãn revision.

```sh
revision="$(git rev-parse HEAD)"
docker build --label "org.opencontainers.image.revision=$revision" -t "tmgs/copilot-frontend:0.1.96-$revision" frontend
docker build --label "org.opencontainers.image.revision=$revision" -t "tmgs/copilot-customer-portal:0.1.96-$revision" customer-portal
```

Sau build, đối chiếu nhãn revision và ghi ID/digest riêng cho từng image. Chạy kiểm thử Nginx/TLS và lưu evidence từ mạng staging biệt lập với dữ liệu thử. Hai Dockerfile gốc copy `dist` vào `/var/www/copilot`. Template phục vụ SPA và proxy `/api` tới `copilot-backend:5000`, Core còn có location cho báo cáo ScoutSuite. So sánh runtime template được render, HTTPS, upstream, header forwarding, cookie, upload size, streaming và timeout với frontend đang chạy.

## Điều kiện thay riêng frontend

1. Xác minh backend đang chạy và đối chiếu image digest hoặc revision. Chốt baseline tương ứng cho cả frontend Core lẫn portal. Hồ sơ staging cũ chưa xác minh cấu hình live.
2. Đọc project Compose đã dùng, đúng thứ tự file, tên service, volume, network và reverse proxy. Hồ sơ staging có tên `copilot-frontend` và `copilot-customer-portal`. Dùng tên này sau khi xác minh trên môi trường đích.
3. Ghim image/artifact cũ của từng frontend và lưu giá trị phục vụ rollback. Xác minh có sẵn bản cũ trước khi thay.
4. So sánh cấu hình đã merge với cấu hình live. Nếu dùng Compose override, bản chênh lệch chỉ gồm trường image của service frontend được chọn. Kiểm tra Nginx runtime và TLS mount, header, cookie domain, port, upstream, mạng và timeout.
5. Thực hiện thay một frontend mỗi lần. Thao tác phải chọn đích chính xác, bỏ qua dependencies và dùng image đã chuẩn bị. Đối chiếu ID của backend/MCP/DB trước và sau. Kiểm tra root, static asset, deep link, read-only auth/tenant, API và SSE theo luồng thuộc phạm vi.

Lệnh thay service cần được lập sau khi cấu hình môi trường đích đã được xác minh. Ở mốc bàn giao này, xem [rollback](rollback.md) và [kết quả kiểm thử](verification.md).
