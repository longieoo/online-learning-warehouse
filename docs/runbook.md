# Runbook

## Khởi động và cấu hình

Làm theo README từ thư mục gốc dự án. Docker Desktop cần ở chế độ Linux containers. Sao chép `.env.example` thành `.env` nếu muốn đổi project name, cổng và mật khẩu trước lần tạo volume đầu tiên. Thay mật khẩu sau khi volume đã có dữ liệu cần cập nhật role tương ứng trong PostgreSQL, không chỉ sửa env.

Cổng mặc định PostgreSQL 55432, ClickHouse HTTP 58123 và portal 8501, chỉ bind 127.0.0.1. Nếu Windows chặn cổng, đặt PG_PORT=15432, CH_PORT=18123, DASHBOARD_PORT=18501 trong .env và chạy lại. Các service nội bộ vẫn dùng cổng PostgreSQL 5432 và ClickHouse 8123.

```powershell
docker compose ps
docker compose logs --tail 80 postgres clickhouse dashboard
docker compose run --rm runner python cli.py doctor
```

`doctor` kiểm tra kết nối, vai trò nguồn chỉ đọc, staging không kết nối OLTP, trạng thái đã công bố và số lỗi chưa xử lý. Doctor không thay dữ liệu. `setup` được dùng khi khởi tạo hoặc nâng cấp schema điều khiển. Không chạy setup đồng thời với pipeline hay tác nghiệp nguồn.

## Lịch chạy gợi ý

1. Chạy full đầu tiên và kiểm tra quality gate.
2. Khi nguồn có thay đổi, chạy incremental. Giao dịch giữ mở có thể làm checkpoint chờ.
3. Chạy reports sau khi công bố. Manifest có đường dẫn thư mục CSV, run ID, số dòng và hash.
4. Chạy benchmark khi cần đo, ngoài giờ tác nghiệp. Có bước sao chép toàn Gold và đối chiếu hash, có thể tốn nhiều thời gian hơn truy vấn.
5. Mở portal, bấm Làm mới để đọc bản mới. Bộ nhớ đệm tối đa 60 giây và gắn run ID.

## Pipeline lỗi

Đọc `artifacts/pipeline.json`, file của run trong `artifacts/runs` và log runner. Dữ liệu lỗi có mã và payload trong quarantine. Gold đã công bố có thể vẫn dùng được dù lần thử gần nhất lỗi. Không tự sửa watermark, không xóa pending_changes hoặc source_versions.

```powershell
docker compose run --rm runner python cli.py pipeline --mode incremental
```

Lệnh trên phục hồi công bố dang dở trước khi nạp tiếp. Nếu báo UUID không khớp, dừng consumer và giữ `gold_build` cùng `staging.pipeline_runs`. Đối chiếu kế hoạch publication với `system.tables` để tìm thao tác ngoài pipeline. Không drop database tạm trước khi điều tra.

Nếu lỗi contract hoặc đã tắt trigger, sửa setup/schema/mapping rồi chạy `pipeline --mode full`. Quality gate không đạt thì kiểm tra quality.json và nguồn. Dòng lỗi schema/miền giá trị bị cách ly. Lỗi tổng hợp, SCD2 hoặc quan hệ phức tạp có thể chặn cả lần công bố để tránh mất dữ liệu âm thầm.

## Sao lưu và dừng

Sao lưu cả `learning_oltp` lẫn `dwh_staging` bằng pg_dump và Gold bằng cơ chế backup ClickHouse hoặc bản snapshot volume được tạo khi service dừng. Cần khôi phục checkpoint/control state cùng Gold tương ứng. Chưa có bài kiểm thử phục hồi backup trong phiên bản này.

```powershell
docker compose stop
# Khởi động lại, giữ nguyên volume
docker compose up -d --wait postgres clickhouse
docker compose --profile demo up -d --wait dashboard
```

`docker compose down` giữ volume. Lệnh `down -v` xóa toàn bộ dữ liệu dự án và không nằm trong quy trình thông thường.

## Kiểm thử độc lập

`scripts/verify.ps1` tạo project Docker riêng, sinh 5.000 ghi danh, chạy toàn luồng, unit/integration và các tình huống lỗi. Project kiểm thử dùng cổng khác và `DW_MIN_SOURCE_ROWS=0`. Đây là smoke test, không thay thế nghiệm thu hơn 5 triệu dòng. Test lỗi có quyền ghi/xóa dữ liệu giả lập và chỉ chạy khi `DW_ALLOW_SCENARIOS=1`.

Bằng chứng nghiệm thu có ngày, scope và đường dẫn ở `artifacts/acceptance.json`. Các số đo v2 ngày 04/11/2026 nằm trong history, không phải số đo mới. Gói bàn giao có MANIFEST.json với SHA-256 cho từng file. Không chứa .env, cache, database volume hoặc zip lồng nhau. Công cụ tạo gói được giữ trong workspace gốc.

