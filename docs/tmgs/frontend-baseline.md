# Baseline frontend TMGS SOC

| Mốc | SHA / trạng thái |
| --- | --- |
| Upstream `main` tại thời điểm fork | `24be8480d13ddb2e933316f8a5946d9a8af592f7` |
| Nguồn build staging | `v0.1.96` · `e5bc2ba17159ce124e95b382c47b511e0c2cf438` |
| Backend mục tiêu của staging | CoPilot `0.1.96`, phiên bản ghi trong hồ sơ nghiệm thu staging ngày 08/10/2026 |
| Backend, frontend và portal production | Chưa xác minh image digest hoặc revision. Chưa xác nhận tương thích production. |

Hồ sơ cài đặt staging ghi Compose riêng, image được ghim theo RepoDigests và có hai frontend. Repo commit lúc cài và image digest là hai loại bằng chứng. SSH không tương tác bị từ chối và HTTPS dùng chứng chỉ công khai đã lưu hết thời gian chờ. Hồ sơ sau cài có ghi các connector chỉ đọc tới nguồn SOC. Bản xem thử localhost dùng fixture tổng hợp trong kiểm thử trình duyệt và tách khỏi các môi trường đã triển khai.

Mã tại tag có Vue 3, Vite, Pinia, Naive UI, Tailwind, hai lockfile pnpm, hai Dockerfile và hai template Nginx. Dùng Node 24 theo Dockerfile. Script `lint` mặc định có `--fix`; chạy `pnpm exec eslint .` để kiểm tra. Suite `frontend/e2e` có bước seed nên không dùng với các hệ thống đang vận hành. Suite `frontend/e2e-mocked` chạy API giả lập ở tầng trình duyệt.

Các tài liệu liên quan nằm trong [bảng chức năng](feature-parity.md), [thiết kế](design-system.md) và [hướng dẫn đóng gói](deploy-frontend-only.md).
