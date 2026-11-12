# Kiểm thử bản TMGS SOC trên baseline v0.1.96

## Kết quả

| Hạng mục | Baseline | Bản TMGS |
| --- | --- | --- |
| Frozen lockfile | Cài thành công cả hai app | Giữ hai lockfile |
| Type-check | Core và Portal đạt | Core và Portal đạt |
| Production build | Core và Portal đạt | Core và Portal đạt |
| Lint chỉ đọc | Core 3 lỗi upstream trong `e2e/soc-management.spec.ts` và `src/components/fileAnalysis/submit/mock.ts`. Portal đạt. | Portal đạt. Core còn các lỗi upstream nêu trên. |
| Unit Portal | 100 đạt, 1 timeout ở router wiring | 100 đạt, cùng bài kiểm tra timeout |
| Unit Core | 486 bài chạy đạt. 5 suite không tải được trên Windows do URL asset trang login. | 486 bài đạt trong lượt đầy đủ, cùng 5 suite ban đầu không tải được do URL logo mới. Đã đổi cách bind URL logo và chạy lại 5 suite đó, 43 bài đạt. |
| So sánh trên trình duyệt | Hai production build được chạy với cùng fixture | Chữ ký request của hai form login và lượt đọc alert, deep link tenant và hành vi logout khớp |
| Playwright trên fixture | Asset của alert và Event Search dùng source trong baseline | 6 bài đạt gồm 5 bài Event Search và 1 bài login/locale mobile |
| Kiểm tra bundle | Core chứa mã fixture File Analysis dù nhánh gọi bị chặn ở runtime production | Build cuối không còn marker `mock-full`, marker của E2E hoặc private-key marker đã kiểm |

So sánh trình duyệt gồm HTTP method, path, query, tên field multipart, content type và việc có bearer header. Dùng dữ liệu tổng hợp với `customer_code=ACME`. Core chuyển từ asset của alert sang Event Search giữ nguyên tham số customer, index và query. Portal vẫn dùng title trả về từ cấu hình. Kiểm thử responsive dùng viewport 1440 px và 390 px.

## Phạm vi diff

Các thay đổi gồm HTML entry, asset TMGS và giấy phép font, theme, CSS, thành phần trình bày của shell và login, chuỗi i18n của Core, bố cục Overview, kiểm thử login và tài liệu. Ba component File Analysis dùng thêm điều kiện build-time `import.meta.env.DEV` ngay tại nhánh fixture để production tree-shake mã này. Đường gọi API thật và điều kiện fixture trong dev giữ hành vi baseline. Giữ thông báo bản quyền và LICENSE của SOCFortress.

So sánh Git với `e5bc2ba17159ce124e95b382c47b511e0c2cf438` cho kết quả 0 file thay đổi trong các nhóm backend, Compose, Dockerfile, Nginx, pnpm lockfile, client API, router, store và composable của cả hai app.

## Điều kiện nghiệm thu còn thiếu

- Chưa có kiểm thử backend staging live với digest đã xác minh. RBAC, đổi tenant thật, cookie/SSO/MFA/passkey, session expiry, export, upload, AI/MCP, SSE, cancel, approval và các thao tác ghi cần kiểm thử trên dữ liệu thử và runtime tương ứng.
- Giữ hỗ trợ tiếng Anh. Tiếng Việt áp dụng cho chuỗi mới ở Core và màn hình login/Overview được chỉnh. Những chuỗi nghiệp vụ còn lại theo baseline. Ngôn ngữ khả dụng của Portal theo thiết lập phía server.
- Docker CLI có trên máy kiểm thử, Docker daemon Linux không phản hồi. Đã build hai thư mục dist. Chưa build, chạy hoặc xác nhận Nginx/TLS của hai image TMGS.
- Chưa xác nhận tương thích production. Chưa thay frontend đang phục vụ.
