# Hoàn thiện dự án · phiên bản 3

Nghiệm thu cục bộ ngày 10/11/2026. Mã chuẩn ở thư mục gốc bản bàn giao, tương ứng `btl` trong workspace phát triển. Báo cáo Word và số đo v2 được giữ trong bộ bàn giao v2, không ghi đè và không dùng làm số đo mới.

## Các phần đã hoàn thiện

| Phần | Thay đổi và kết quả |
|---|---|
| Khởi tạo | Dockerfile nhiều target dùng chung base, dashboard build độc lập, dependency lock cho cả runner và portal, healthcheck đúng database, cổng và project name cấu hình được |
| CLI | Một entry point cho setup, generate, pipeline, validate, reports, benchmark, doctor và all. All khởi tạo được volume trống và tái sử dụng nguồn khi chạy lại |
| Nguồn | Giữ PK/FK và dữ liệu seed tái lập. Trigger tạo change journal trong cùng giao dịch nguồn cho insert, update và delete |
| Incremental | Checkpoint theo transaction ID an toàn với snapshot, revision từng khóa và tombstone chống replay. Đã kiểm tra commit lệch thứ tự và full snapshot nhìn thấy delete trước checkpoint |
| Silver | Ghi theo transaction, chuẩn hóa kiểu và miền giá trị, upsert theo khóa. Pending changes tồn tại qua lỗi dựng Gold; cờ needs_full bảo vệ retry sau full stage |
| Cách ly | Payload gốc, mã lỗi, nguồn, thời điểm và resolved_at. Sửa nguồn hợp lệ giải quyết lỗi, cập nhật sai giữ bản sạch đã biết |
| Gold | 4 fact, 7 dimension, 2 bảng tổng hợp. Giữ partition không đổi, dựng lại fact khi cần, quality gate trước công bố |
| Phục hồi | Lưu kế hoạch UUID trước exchange. Phục hồi sau khi tiến trình thực sự thoát giữa công bố. Checkpoint chỉ commit cùng manifest thành công |
| Consumers | Khóa đọc/ghi dùng chung. Portal lấy toàn bộ dữ liệu biểu đồ trong cùng snapshot. Báo cáo xuất trọn bộ rồi mới đổi manifest |
| Portal | Sáu trang có thanh điều hướng, nền sáng/navy, KPI gọn và so sánh cùng kỳ, biểu đồ phân bổ và waterfall, bộ lọc ngày/lĩnh vực, tìm đề thi, CSV và trạng thái rỗng/bận |
| Analytics | 10 báo cáo giữ ngữ nghĩa subtotal và drill across. Benchmark sao cùng Gold sang PostgreSQL, kiểm tra toàn bộ dòng và kết quả từng truy vấn trước khi đo |
| Chất lượng mã | Định dạng Python thống nhất, Ruff, 12 bài unit/integration, script smoke riêng và CI workflow có thể chạy trên GitHub |
| Tài liệu | README, architecture, mapping, dictionary sinh từ schema đang chạy và runbook thống nhất. Tài liệu lịch sử và công cụ cũ được giữ ngoài gói hiện hành |
| Bàn giao | Chọn file cần thiết, loại env thật/cache/volume/zip cũ. Manifest SHA-256, kiểm tra hash từng file và CRC của ZIP |

## Bằng chứng mới

- Full load trên nguồn chính gồm **5.762.103 dòng**, kỳ 2022–2024, đạt **123 kiểm tra chất lượng**. Có thêm 10.000 lượt thi giả lập cho thử nghiệm journal so với mốc 5.752.103 dòng ban đầu của phiên này.
- **12 bài unit/integration** đạt trên Gold chính. Bao gồm SCD2 đúng ranh giới, unknown date, subtotal CUBE, drill across, checksum multiset và các miền giá trị mới.
- **15 kiểm tra hồi quy** đạt ở project Docker riêng, có thao tác ghi/xóa chủ động trên dữ liệu giả lập. Bao gồm late commit, delete, quarantine correction, lỗi quality, staging đã commit, crash sau exchange, retry full và tombstone.
- **13 kiểm tra dashboard** cho thiết kế mới, gồm sáu trang, bộ lọc, gộp quý, biểu đồ đề thi dạng phân loại, tìm kiếm, drilldown, trạng thái rỗng, reset, so sánh lịch và đối soát độc lập với PostgreSQL Silver. Có xem trực tiếp giao diện trên browser.
- Volume trống sinh **69.203 dòng** từ 5.000 ghi danh, chạy full → reports → benchmark rồi các tình huống lỗi. Cấu hình smoke hạ ngưỡng tối thiểu xuống 0; nguồn chính vẫn yêu cầu ít nhất 5 triệu dòng.
- Chi tiết hiện hành và đường dẫn bằng chứng nằm ở `artifacts/acceptance.json`.

## Hiệu năng đã đo

| Chế độ | Thời gian pipeline | Phạm vi |
|---|---:|---|
| Full | 205,439 giây | 5.762.103 dòng, peak RSS 241,04 MiB |
| Incremental có thay đổi | 12,543 giây | 10.000 lượt thi mới, đối soát Gold đầy đủ |
| Incremental rỗng | 0,806 giây | Tái sử dụng Gold, kiểm tra UUID và số dòng |

Trước khi bỏ ghi dư revision baseline 0, một lần full v3 mất 294,111 giây. Lần đo sau giảm khoảng 30% thời gian so với lần đó. Đây là hai lần đo cục bộ, không phải thử nghiệm kiểm soát riêng từng yếu tố.

Không so trực tiếp tốc độ full v3 với số đo v2 để kết luận nhanh hơn. V3 thêm trạng thái bền vững và bảo vệ retry, môi trường cũng có tải khác. Mục tiêu incremental có dữ liệu trong 1–2 giây **chưa đạt**. Lần rỗng nhanh không đại diện cho lần nạp có thay đổi.

Benchmark gồm hai lần warm-up và năm lần đo cho mỗi engine/query, luân phiên thứ tự. Xem `artifacts/benchmark/results.md`, `metadata.json`, `runs.csv` và `summary.csv`. Tỷ số PG/CH chỉ mô tả bộ dữ liệu, tài nguyên và truy vấn đã đo. Một benchmark smoke nhỏ có thể cho PostgreSQL nhanh hơn do chi phí client/network; không suy rộng từ đó ra dữ liệu lớn.

## Những giới hạn còn lại

- Đây là dự án học tập/demo cục bộ, chưa nghiệm thu production, không cam kết SLA, không có authentication portal hoặc điều phối lịch chạy.
- Gold đổi nguyên tử từng bảng. Consumer của dự án được khóa bảo vệ, SQL client bên ngoài phải tuân thủ cửa sổ công bố.
- Journal chưa tự động retention. Giao dịch mở lâu có thể trì hoãn incremental. Không tắt trigger hoặc dùng TRUNCATE để thay cho delete; cần full reload khi làm vậy.
- Sự kiện Gold có độ chính xác giây, lịch 2022–2024 và sentinel lịch sử 2100. Mở rộng kỳ/độ chính xác cần sửa schema, mapping và quality gate.
- Lịch sử người dùng phải được nguồn duy trì đúng; không tự suy ra SCD2 từ snapshot users. Cập nhật current users không tự sửa lịch sử user_history.
- Cơ chế feed là append theo block insert, không phải CDC cho thao tác UPDATE/DELETE trực tiếp trong ClickHouse. Mọi thay đổi phục vụ phải đi qua pipeline.
- Chưa thử phục hồi backup, tải đồng thời production hoặc equal-memory benchmark. CI đã cấu hình trong mã nguồn, chưa chạy trên dịch vụ GitHub trong phiên này.


