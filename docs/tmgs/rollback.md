# Rollback frontend

Trước khi chuyển, lưu image ID/digest hoặc artifact revision trước đó cho từng frontend, cấu hình route/proxy đang dùng và bộ kiểm tra nhanh. Xác minh image/artifact có thể đọc từ kho đích hoặc bộ lưu rollback.

Nếu lỗi tải SPA, đăng nhập, tenant scope, routing API, stream hoặc một màn hình trọng yếu, đưa lại image/artifact cũ cho đúng frontend đã thay. Xác minh cấu hình đã merge vẫn trỏ đến cùng backend, volume, network, TLS và service name. Khởi tạo lại đúng frontend được chọn và kiểm tra lại các luồng đọc. Đối chiếu backend/MCP/DB container ID trước và sau.

Rollback chỉ cần frontend cũ và cấu hình frontend tương ứng. Lệnh áp dụng và smoke test theo môi trường đích được lập khi có cấu hình live.
