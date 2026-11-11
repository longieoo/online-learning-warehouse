# Data dictionary · v3

Sinh từ PostgreSQL và ClickHouse đang chạy. Timestamps theo UTC, tiền nguyên VND. 
Gold dùng DateTime cho sự kiện, độ chính xác giây. Khóa ngoại Gold được kiểm tra bằng quality gate.
Grain, công thức và phạm vi xem architecture.md và mapping.md.

## PostgreSQL learning_oltp.oltp.change_journal

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| revision | bigint | NO | Số thứ tự thay đổi dùng chống replay bản cũ. |
| source_xid | bigint | NO | Full transaction ID của giao dịch nguồn ghi journal. |
| table_name | text | NO | Tên bảng nguồn thuộc danh sách contract của ETL. |
| source_id | bigint | NO | Khóa nghiệp vụ của dòng nguồn. |
| operation | text | NO | INSERT, UPDATE, DELETE hoặc trạng thái delta được ETL lưu. |
| raw_payload | jsonb | NO | JSON gốc để tái hiện thay đổi hoặc điều tra dòng lỗi. |
| changed_at | timestamp with time zone | NO | Thời điểm trigger ghi sự kiện vào journal. |
## PostgreSQL learning_oltp.oltp.courses

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| course_id | bigint | NO | Khóa nghiệp vụ khóa học. |
| instructor_id | bigint | NO | Khóa nghiệp vụ giảng viên. |
| title | text | NO | Tiêu đề khóa/bài/quiz theo bảng. |
| category | text | NO | Nhóm khóa: Data, Programming, Business, Design, Language. |
| difficulty | text | NO | beginner, intermediate, advanced. |
| price_vnd | bigint | NO | Giá hiện tại khóa, VND integer ≥0. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
| dw_revision | bigint | NO | Revision tăng đơn điệu từ sequence; 0 là baseline bulk seed hoặc dữ liệu nâng cấp. |
## PostgreSQL learning_oltp.oltp.enrollments

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| enrollment_id | bigint | NO | Khóa ghi danh; unique user/course; degenerate reference trên facts. |
| user_id | bigint | NO | Khóa nghiệp vụ học viên, dùng distinct learner qua nhiều phiên bản. |
| course_id | bigint | NO | Khóa nghiệp vụ khóa học. |
| enrolled_at | timestamp without time zone | NO | Thời điểm ghi danh UTC; Gold user version được tra tại thời điểm này. |
| completed_at | timestamp without time zone | YES | Thời điểm hoàn thành UTC; nullable cho enrollment chưa hoàn thành, không null cho lesson completion. |
| lessons_completed | smallint | NO | Số bài đã hoàn thành cuối kỳ; 10 nếu complete, 6 nếu chưa complete trong generator. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
| dw_revision | bigint | NO | Revision tăng đơn điệu từ sequence; 0 là baseline bulk seed hoặc dữ liệu nâng cấp. |
## PostgreSQL learning_oltp.oltp.instructors

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| instructor_id | bigint | NO | Khóa nghiệp vụ giảng viên. |
| full_name | text | NO | Tên giả lập Faker; Silver trim khoảng trắng. |
| expertise | text | NO | Lĩnh vực chuyên môn giảng viên giả lập. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
| dw_revision | bigint | NO | Revision tăng đơn điệu từ sequence; 0 là baseline bulk seed hoặc dữ liệu nâng cấp. |
## PostgreSQL learning_oltp.oltp.lesson_completions

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| completion_id | bigint | NO | Khóa sự kiện hoàn thành bài; unique enrollment/lesson. |
| enrollment_id | bigint | NO | Khóa ghi danh; unique user/course; degenerate reference trên facts. |
| user_id | bigint | NO | Khóa nghiệp vụ học viên, dùng distinct learner qua nhiều phiên bản. |
| course_id | bigint | NO | Khóa nghiệp vụ khóa học. |
| lesson_id | bigint | NO | Khóa nghiệp vụ bài học, mỗi khóa có 10 bài. |
| completed_at | timestamp without time zone | NO | Thời điểm hoàn thành UTC; nullable cho enrollment chưa hoàn thành, không null cho lesson completion. |
| time_spent_seconds | integer | NO | Thời gian học/làm quiz, giây dương; additive trên events. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
| dw_revision | bigint | NO | Revision tăng đơn điệu từ sequence; 0 là baseline bulk seed hoặc dữ liệu nâng cấp. |
## PostgreSQL learning_oltp.oltp.lessons

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| lesson_id | bigint | NO | Khóa nghiệp vụ bài học, mỗi khóa có 10 bài. |
| course_id | bigint | NO | Khóa nghiệp vụ khóa học. |
| title | text | NO | Tiêu đề khóa/bài/quiz theo bảng. |
| position | smallint | NO | Thứ tự bài trong khóa, 1–10. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
| dw_revision | bigint | NO | Revision tăng đơn điệu từ sequence; 0 là baseline bulk seed hoặc dữ liệu nâng cấp. |
## PostgreSQL learning_oltp.oltp.payment_methods

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| method_id | bigint | NO | Khóa nghiệp vụ phương thức thanh toán. |
| method_name | text | NO | bank_transfer, card, wallet. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
| dw_revision | bigint | NO | Revision tăng đơn điệu từ sequence; 0 là baseline bulk seed hoặc dữ liệu nâng cấp. |
## PostgreSQL learning_oltp.oltp.payments

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| payment_id | bigint | NO | Khóa nghiệp vụ thanh toán, 1 payment/enrollment. |
| enrollment_id | bigint | NO | Khóa ghi danh; unique user/course; degenerate reference trên facts. |
| user_id | bigint | NO | Khóa nghiệp vụ học viên, dùng distinct learner qua nhiều phiên bản. |
| course_id | bigint | NO | Khóa nghiệp vụ khóa học. |
| method_id | bigint | NO | Khóa nghiệp vụ phương thức thanh toán. |
| transaction_id | text | NO | Mã giao dịch unique TXN-…; degenerate dimension. |
| paid_at | timestamp without time zone | NO | Thời điểm thanh toán UTC = enrolled_at + 60 giây trong generator. |
| original_vnd | bigint | NO | Giá gốc tại giao dịch, VND integer. |
| discount_vnd | bigint | NO | Số tiền giảm giá, VND; additive trong bảng tổng hợp. |
| charged_vnd | bigint | NO | Số tiền thu trước hoàn tiền = original_vnd - discount_vnd. |
| refunded | smallint | NO | Cờ 0/1 hoàn tiền toàn phần; không có thời điểm refund riêng. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
| dw_revision | bigint | NO | Revision tăng đơn điệu từ sequence; 0 là baseline bulk seed hoặc dữ liệu nâng cấp. |
## PostgreSQL learning_oltp.oltp.quiz_attempts

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| attempt_id | bigint | NO | Khóa lần làm quiz. |
| enrollment_id | bigint | NO | Khóa ghi danh; unique user/course; degenerate reference trên facts. |
| user_id | bigint | NO | Khóa nghiệp vụ học viên, dùng distinct learner qua nhiều phiên bản. |
| course_id | bigint | NO | Khóa nghiệp vụ khóa học. |
| quiz_id | bigint | NO | Khóa nghiệp vụ quiz, một quiz/khóa. |
| attempt_number | smallint | NO | Lần 1 hoặc 2 trong mỗi enrollment/quiz. |
| attempted_at | timestamp without time zone | NO | Thời điểm làm quiz UTC. |
| correct_count | smallint | NO | Số câu đúng từ 0 đến total_questions. |
| total_questions | smallint | NO | Số câu hỏi, hiện tại 20 mỗi quiz/attempt. |
| time_spent_seconds | integer | NO | Thời gian học/làm quiz, giây dương; additive trên events. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
| dw_revision | bigint | NO | Revision tăng đơn điệu từ sequence; 0 là baseline bulk seed hoặc dữ liệu nâng cấp. |
## PostgreSQL learning_oltp.oltp.quizzes

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| quiz_id | bigint | NO | Khóa nghiệp vụ quiz, một quiz/khóa. |
| course_id | bigint | NO | Khóa nghiệp vụ khóa học. |
| title | text | NO | Tiêu đề khóa/bài/quiz theo bảng. |
| total_questions | smallint | NO | Số câu hỏi, hiện tại 20 mỗi quiz/attempt. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
| dw_revision | bigint | NO | Revision tăng đơn điệu từ sequence; 0 là baseline bulk seed hoặc dữ liệu nâng cấp. |
## PostgreSQL learning_oltp.oltp.user_history

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| history_id | bigint | NO | Khóa phiên bản lịch sử nguồn; một user có thể nhiều dòng. |
| user_id | bigint | NO | Khóa nghiệp vụ học viên, dùng distinct learner qua nhiều phiên bản. |
| full_name | text | NO | Tên giả lập Faker; Silver trim khoảng trắng. |
| email | text | NO | Email giả example.invalid; Silver trim và lowercase. |
| city | text | NO | Thành phố; lịch sử lưu tại user_history / dim_user. |
| country | character | NO | ISO alpha-2; dữ liệu hiện tại VN, Silver uppercase. |
| valid_from | timestamp without time zone | NO | Bắt đầu hiệu lực SCD2, inclusive (UTC). |
| valid_to | timestamp without time zone | NO | Kết thúc hiệu lực SCD2, exclusive; sentinel 2100-01-01. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
| dw_revision | bigint | NO | Revision tăng đơn điệu từ sequence; 0 là baseline bulk seed hoặc dữ liệu nâng cấp. |
## PostgreSQL learning_oltp.oltp.users

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| user_id | bigint | NO | Khóa nghiệp vụ học viên, dùng distinct learner qua nhiều phiên bản. |
| full_name | text | NO | Tên giả lập Faker; Silver trim khoảng trắng. |
| email | text | NO | Email giả example.invalid; Silver trim và lowercase. |
| city | text | NO | Thành phố; lịch sử lưu tại user_history / dim_user. |
| country | character | NO | ISO alpha-2; dữ liệu hiện tại VN, Silver uppercase. |
| created_at | timestamp without time zone | NO | Thời điểm tạo UTC, đầu kỳ 2022 trong bộ dữ liệu này. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
| dw_revision | bigint | NO | Revision tăng đơn điệu từ sequence; 0 là baseline bulk seed hoặc dữ liệu nâng cấp. |
## PostgreSQL dwh_staging.quarantine.quarantine_records

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| table_name | text | NO | Tên bảng nguồn thuộc danh sách contract của ETL. |
| source_id | bigint | NO | Khóa nghiệp vụ của dòng nguồn. |
| source_updated_at | timestamp with time zone | NO | updated_at của phiên bản bị từ chối. |
| error_code | text | NO | Mã phân loại lỗi schema, nghiệp vụ hoặc quan hệ. |
| rejection_reason | text | NO | Mô tả nguyên nhân cách ly. |
| detected_at | timestamp with time zone | YES | Thời điểm phát hiện lỗi trong staging. |
| raw_payload | jsonb | NO | JSON gốc để tái hiện thay đổi hoặc điều tra dòng lỗi. |
| resolved_at | timestamp with time zone | YES | Thời điểm phiên bản nguồn hợp lệ thay thế lỗi; NULL khi chưa giải quyết. |
## PostgreSQL dwh_staging.silver.courses

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| course_id | bigint | NO | Khóa nghiệp vụ khóa học. |
| instructor_id | bigint | NO | Khóa nghiệp vụ giảng viên. |
| title | text | NO | Tiêu đề khóa/bài/quiz theo bảng. |
| category | text | NO | Nhóm khóa: Data, Programming, Business, Design, Language. |
| difficulty | text | NO | beginner, intermediate, advanced. |
| price_vnd | bigint | NO | Giá hiện tại khóa, VND integer ≥0. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
## PostgreSQL dwh_staging.silver.enrollments

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| enrollment_id | bigint | NO | Khóa ghi danh; unique user/course; degenerate reference trên facts. |
| user_id | bigint | NO | Khóa nghiệp vụ học viên, dùng distinct learner qua nhiều phiên bản. |
| course_id | bigint | NO | Khóa nghiệp vụ khóa học. |
| enrolled_at | timestamp without time zone | NO | Thời điểm ghi danh UTC; Gold user version được tra tại thời điểm này. |
| completed_at | timestamp without time zone | YES | Thời điểm hoàn thành UTC; nullable cho enrollment chưa hoàn thành, không null cho lesson completion. |
| lessons_completed | bigint | NO | Số bài đã hoàn thành cuối kỳ; 10 nếu complete, 6 nếu chưa complete trong generator. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
## PostgreSQL dwh_staging.silver.instructors

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| instructor_id | bigint | NO | Khóa nghiệp vụ giảng viên. |
| full_name | text | NO | Tên giả lập Faker; Silver trim khoảng trắng. |
| expertise | text | NO | Lĩnh vực chuyên môn giảng viên giả lập. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
## PostgreSQL dwh_staging.silver.lesson_completions

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| completion_id | bigint | NO | Khóa sự kiện hoàn thành bài; unique enrollment/lesson. |
| enrollment_id | bigint | NO | Khóa ghi danh; unique user/course; degenerate reference trên facts. |
| user_id | bigint | NO | Khóa nghiệp vụ học viên, dùng distinct learner qua nhiều phiên bản. |
| course_id | bigint | NO | Khóa nghiệp vụ khóa học. |
| lesson_id | bigint | NO | Khóa nghiệp vụ bài học, mỗi khóa có 10 bài. |
| completed_at | timestamp without time zone | NO | Thời điểm hoàn thành UTC; nullable cho enrollment chưa hoàn thành, không null cho lesson completion. |
| time_spent_seconds | bigint | NO | Thời gian học/làm quiz, giây dương; additive trên events. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
## PostgreSQL dwh_staging.silver.lessons

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| lesson_id | bigint | NO | Khóa nghiệp vụ bài học, mỗi khóa có 10 bài. |
| course_id | bigint | NO | Khóa nghiệp vụ khóa học. |
| title | text | NO | Tiêu đề khóa/bài/quiz theo bảng. |
| position | bigint | NO | Thứ tự bài trong khóa, 1–10. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
## PostgreSQL dwh_staging.silver.payment_methods

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| method_id | bigint | NO | Khóa nghiệp vụ phương thức thanh toán. |
| method_name | text | NO | bank_transfer, card, wallet. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
## PostgreSQL dwh_staging.silver.payments

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| payment_id | bigint | NO | Khóa nghiệp vụ thanh toán, 1 payment/enrollment. |
| enrollment_id | bigint | NO | Khóa ghi danh; unique user/course; degenerate reference trên facts. |
| user_id | bigint | NO | Khóa nghiệp vụ học viên, dùng distinct learner qua nhiều phiên bản. |
| course_id | bigint | NO | Khóa nghiệp vụ khóa học. |
| method_id | bigint | NO | Khóa nghiệp vụ phương thức thanh toán. |
| transaction_id | text | NO | Mã giao dịch unique TXN-…; degenerate dimension. |
| paid_at | timestamp without time zone | NO | Thời điểm thanh toán UTC = enrolled_at + 60 giây trong generator. |
| original_vnd | bigint | NO | Giá gốc tại giao dịch, VND integer. |
| discount_vnd | bigint | NO | Số tiền giảm giá, VND; additive trong bảng tổng hợp. |
| charged_vnd | bigint | NO | Số tiền thu trước hoàn tiền = original_vnd - discount_vnd. |
| refunded | bigint | NO | Cờ 0/1 hoàn tiền toàn phần; không có thời điểm refund riêng. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
## PostgreSQL dwh_staging.silver.quiz_attempts

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| attempt_id | bigint | NO | Khóa lần làm quiz. |
| enrollment_id | bigint | NO | Khóa ghi danh; unique user/course; degenerate reference trên facts. |
| user_id | bigint | NO | Khóa nghiệp vụ học viên, dùng distinct learner qua nhiều phiên bản. |
| course_id | bigint | NO | Khóa nghiệp vụ khóa học. |
| quiz_id | bigint | NO | Khóa nghiệp vụ quiz, một quiz/khóa. |
| attempt_number | bigint | NO | Lần 1 hoặc 2 trong mỗi enrollment/quiz. |
| attempted_at | timestamp without time zone | NO | Thời điểm làm quiz UTC. |
| correct_count | bigint | NO | Số câu đúng từ 0 đến total_questions. |
| total_questions | bigint | NO | Số câu hỏi, hiện tại 20 mỗi quiz/attempt. |
| time_spent_seconds | bigint | NO | Thời gian học/làm quiz, giây dương; additive trên events. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
## PostgreSQL dwh_staging.silver.quizzes

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| quiz_id | bigint | NO | Khóa nghiệp vụ quiz, một quiz/khóa. |
| course_id | bigint | NO | Khóa nghiệp vụ khóa học. |
| title | text | NO | Tiêu đề khóa/bài/quiz theo bảng. |
| total_questions | bigint | NO | Số câu hỏi, hiện tại 20 mỗi quiz/attempt. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
## PostgreSQL dwh_staging.silver.user_history

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| history_id | bigint | NO | Khóa phiên bản lịch sử nguồn; một user có thể nhiều dòng. |
| user_id | bigint | NO | Khóa nghiệp vụ học viên, dùng distinct learner qua nhiều phiên bản. |
| full_name | text | NO | Tên giả lập Faker; Silver trim khoảng trắng. |
| email | text | NO | Email giả example.invalid; Silver trim và lowercase. |
| city | text | NO | Thành phố; lịch sử lưu tại user_history / dim_user. |
| country | text | NO | ISO alpha-2; dữ liệu hiện tại VN, Silver uppercase. |
| valid_from | timestamp without time zone | NO | Bắt đầu hiệu lực SCD2, inclusive (UTC). |
| valid_to | timestamp without time zone | NO | Kết thúc hiệu lực SCD2, exclusive; sentinel 2100-01-01. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
## PostgreSQL dwh_staging.silver.users

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| user_id | bigint | NO | Khóa nghiệp vụ học viên, dùng distinct learner qua nhiều phiên bản. |
| full_name | text | NO | Tên giả lập Faker; Silver trim khoảng trắng. |
| email | text | NO | Email giả example.invalid; Silver trim và lowercase. |
| city | text | NO | Thành phố; lịch sử lưu tại user_history / dim_user. |
| country | text | NO | ISO alpha-2; dữ liệu hiện tại VN, Silver uppercase. |
| created_at | timestamp without time zone | NO | Thời điểm tạo UTC, đầu kỳ 2022 trong bộ dữ liệu này. |
| updated_at | timestamp with time zone | NO | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |
## PostgreSQL dwh_staging.staging.etl_watermarks

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| table_name | text | NO | Tên bảng nguồn thuộc danh sách contract của ETL. |
| last_processed_time | timestamp with time zone | NO | Mốc timestamp tham khảo sau lần công bố; không dùng thay journal checkpoint. |
| last_processed_id | bigint | NO | Khóa nguồn đi cùng mốc timestamp tham khảo. |
| last_run_id | text | NO | Run ID công bố đã xác nhận mốc tham khảo. |
## PostgreSQL dwh_staging.staging.pending_changes

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| table_name | text | NO | Tên bảng nguồn thuộc danh sách contract của ETL. |
| source_id | bigint | NO | Khóa nghiệp vụ của dòng nguồn. |
| operation | text | NO | INSERT, UPDATE, DELETE hoặc trạng thái delta được ETL lưu. |
| revision | bigint | NO | Số thứ tự thay đổi dùng chống replay bản cũ. |
## PostgreSQL dwh_staging.staging.pipeline_runs

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| run_id | text | NO | UUID của lần chạy pipeline. |
| phase | text | NO | extracting, building, publishing, completed, failed hoặc recovered. |
| manifest | jsonb | NO | JSON mô tả run, counts, fingerprint, quality và số đo. |
| publication | jsonb | YES | JSON kế hoạch UUID cũ/mới phục vụ rollback từng bảng. |
| started_at | timestamp with time zone | NO | Thời điểm bắt đầu lần chạy UTC. |
| finished_at | timestamp with time zone | YES | Thời điểm hoàn tất hoặc lỗi UTC. |
## PostgreSQL dwh_staging.staging.published_state

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| singleton | boolean | NO | Khóa boolean duy nhất, bắt buộc true. |
| manifest | jsonb | NO | JSON mô tả run, counts, fingerprint, quality và số đo. |
| safe_xid | bigint | YES | Checkpoint transaction ID; nhận journal từ giá trị này ở lần kế tiếp. |
| published_at | timestamp with time zone | NO | Thời điểm commit trạng thái đã công bố. |
## PostgreSQL dwh_staging.staging.source_versions

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| table_name | text | NO | Tên bảng nguồn thuộc danh sách contract của ETL. |
| source_id | bigint | NO | Khóa nghiệp vụ của dòng nguồn. |
| revision | bigint | NO | Số thứ tự thay đổi dùng chống replay bản cũ. |
## PostgreSQL dwh_staging.staging.stage_state

| Cột | Kiểu | Nullable | Ý nghĩa |
|---|---|---|---|
| singleton | boolean | NO | Khóa boolean duy nhất, bắt buộc true. |
| needs_full | boolean | NO | Full stage đã commit và cần dựng Gold đầy đủ trước khi xóa cờ. |

## ClickHouse gold.dim_course

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| course_sk | Int64 | Khóa dimension course = course_id+1000000. |
| course_id | Int64 | Khóa nghiệp vụ khóa học. |
| title | String | Tiêu đề khóa/bài/quiz theo bảng. |
| category | LowCardinality(String) | Nhóm khóa: Data, Programming, Business, Design, Language. |
| difficulty | LowCardinality(String) | beginner, intermediate, advanced. |
| instructor_id | Int64 | Khóa nghiệp vụ giảng viên. |
| price_vnd | Int64 | Giá hiện tại khóa, VND integer ≥0. |

## ClickHouse gold.dim_date

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| date_sk | Int64 | Khóa ngày YYYYMMDD, khóa 0 dành cho unknown. |
| full_date | Date | Ngày lịch; 1970-01-01 là placeholder riêng dòng unknown. |
| year | Int64 | Năm lịch (0 cho unknown). |
| quarter | Int64 | Quý 1–4 (0 cho unknown). |
| month | Int64 | Tháng 1–12 ở dim_date; YYYYMM ở bảng tổng hợp doanh thu. |
| day | Int64 | Ngày trong tháng (0 cho unknown). |

## ClickHouse gold.dim_instructor

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| instructor_sk | Int64 | Khóa dimension instructor = instructor_id+2000000. |
| instructor_id | Int64 | Khóa nghiệp vụ giảng viên. |
| full_name | String | Tên giả lập Faker; Silver trim khoảng trắng. |
| expertise | LowCardinality(String) | Lĩnh vực chuyên môn giảng viên giả lập. |

## ClickHouse gold.dim_lesson

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| lesson_sk | Int64 | Khóa dimension lesson = lesson_id+3000000. |
| lesson_id | Int64 | Khóa nghiệp vụ bài học, mỗi khóa có 10 bài. |
| course_id | Int64 | Khóa nghiệp vụ khóa học. |
| title | String | Tiêu đề khóa/bài/quiz theo bảng. |
| position | Int64 | Thứ tự bài trong khóa, 1–10. |

## ClickHouse gold.dim_payment_method

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| method_sk | Int64 | Khóa dimension method = method_id+5000000. |
| method_id | Int64 | Khóa nghiệp vụ phương thức thanh toán. |
| method_name | LowCardinality(String) | bank_transfer, card, wallet. |

## ClickHouse gold.dim_quiz

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| quiz_sk | Int64 | Khóa dimension quiz = quiz_id+4000000. |
| quiz_id | Int64 | Khóa nghiệp vụ quiz, một quiz/khóa. |
| course_id | Int64 | Khóa nghiệp vụ khóa học. |
| title | String | Tiêu đề khóa/bài/quiz theo bảng. |
| total_questions | Int64 | Số câu hỏi, hiện tại 20 mỗi quiz/attempt. |

## ClickHouse gold.dim_user

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| user_sk | Int64 | Khóa thay thế theo phiên bản SCD2 = history_id+10000000. |
| user_id | Int64 | Khóa nghiệp vụ học viên, dùng distinct learner qua nhiều phiên bản. |
| full_name | String | Tên giả lập Faker; Silver trim khoảng trắng. |
| email | String | Email giả example.invalid; Silver trim và lowercase. |
| city | LowCardinality(String) | Thành phố; lịch sử lưu tại user_history / dim_user. |
| country | LowCardinality(String) | ISO alpha-2; dữ liệu hiện tại VN, Silver uppercase. |
| valid_from | DateTime('UTC') | Bắt đầu hiệu lực SCD2, inclusive (UTC). |
| valid_to | DateTime('UTC') | Kết thúc hiệu lực SCD2, exclusive; sentinel 2100-01-01. |
| is_current | Int64 | 1 nếu phiên bản hiện hành (valid_to=2100-01-01), ngược lại 0. |

## ClickHouse gold.fact_enrollments

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| enrollment_id | Int64 | Khóa ghi danh; unique user/course; degenerate reference trên facts. |
| user_sk | Int64 | Khóa thay thế theo phiên bản SCD2 = history_id+10000000. |
| course_sk | Int64 | Khóa dimension course = course_id+1000000. |
| instructor_sk | Int64 | Khóa dimension instructor = instructor_id+2000000. |
| enrolled_date_sk | Int64 | Role enrolled của dim_date, suy từ enrolled_at. |
| completed_date_sk | Int64 | Role completed của dim_date; 0 nếu chưa complete. |
| enrolled_at | DateTime('UTC') | Thời điểm ghi danh UTC; Gold user version được tra tại thời điểm này. |
| completed_at | Nullable(DateTime('UTC')) | Thời điểm hoàn thành UTC; nullable cho enrollment chưa hoàn thành, không null cho lesson completion. |
| lessons_completed | Int64 | Số bài đã hoàn thành cuối kỳ; 10 nếu complete, 6 nếu chưa complete trong generator. |
| is_completed | Int64 | 1 khi enrollment có completed_at; metric numerator completion rate. |
| updated_at | DateTime64(6, 'UTC') | Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động. |

## ClickHouse gold.fact_lesson_completions

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| completion_id | Int64 | Khóa sự kiện hoàn thành bài; unique enrollment/lesson. |
| enrollment_id | Int64 | Khóa ghi danh; unique user/course; degenerate reference trên facts. |
| user_sk | Int64 | Khóa thay thế theo phiên bản SCD2 = history_id+10000000. |
| course_sk | Int64 | Khóa dimension course = course_id+1000000. |
| lesson_sk | Int64 | Khóa dimension lesson = lesson_id+3000000. |
| date_sk | Int64 | Khóa ngày YYYYMMDD, khóa 0 dành cho unknown. |
| completed_at | DateTime('UTC') | Thời điểm hoàn thành UTC; nullable cho enrollment chưa hoàn thành, không null cho lesson completion. |
| time_spent_seconds | Int64 | Thời gian học/làm quiz, giây dương; additive trên events. |

## ClickHouse gold.fact_payments

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| payment_id | Int64 | Khóa nghiệp vụ thanh toán, 1 payment/enrollment. |
| enrollment_id | Int64 | Khóa ghi danh; unique user/course; degenerate reference trên facts. |
| transaction_id | String | Mã giao dịch unique TXN-…; degenerate dimension. |
| user_sk | Int64 | Khóa thay thế theo phiên bản SCD2 = history_id+10000000. |
| course_sk | Int64 | Khóa dimension course = course_id+1000000. |
| instructor_sk | Int64 | Khóa dimension instructor = instructor_id+2000000. |
| method_sk | Int64 | Khóa dimension method = method_id+5000000. |
| date_sk | Int64 | Khóa ngày YYYYMMDD, khóa 0 dành cho unknown. |
| paid_at | DateTime('UTC') | Thời điểm thanh toán UTC = enrolled_at + 60 giây trong generator. |
| original_vnd | Int64 | Giá gốc tại giao dịch, VND integer. |
| discount_vnd | Int64 | Số tiền giảm giá, VND; additive trong bảng tổng hợp. |
| charged_vnd | Int64 | Số tiền thu trước hoàn tiền = original_vnd - discount_vnd. |
| refunded | Int64 | Cờ 0/1 hoàn tiền toàn phần; không có thời điểm refund riêng. |
| net_vnd | Int64 | Thực thu sau hoàn tiền = charged_vnd × (1-refunded), quy về kỳ giao dịch gốc. |

## ClickHouse gold.fact_quiz_attempts

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| attempt_id | Int64 | Khóa lần làm quiz. |
| enrollment_id | Int64 | Khóa ghi danh; unique user/course; degenerate reference trên facts. |
| user_sk | Int64 | Khóa thay thế theo phiên bản SCD2 = history_id+10000000. |
| course_sk | Int64 | Khóa dimension course = course_id+1000000. |
| quiz_sk | Int64 | Khóa dimension quiz = quiz_id+4000000. |
| date_sk | Int64 | Khóa ngày YYYYMMDD, khóa 0 dành cho unknown. |
| attempted_at | DateTime('UTC') | Thời điểm làm quiz UTC. |
| attempt_number | Int64 | Lần 1 hoặc 2 trong mỗi enrollment/quiz. |
| correct_count | Int64 | Số câu đúng từ 0 đến total_questions. |
| total_questions | Int64 | Số câu hỏi, hiện tại 20 mỗi quiz/attempt. |
| time_spent_seconds | Int64 | Thời gian học/làm quiz, giây dương; additive trên events. |
| is_passed | Int64 | 1 khi correct_count/total_questions ≥70%, ngược lại 0. |

## ClickHouse gold.feed_course_completion

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| course_sk | Int64 | Khóa dimension course = course_id+1000000. |
| enrollments | UInt64 | Số lượt ghi danh trong nhóm tổng hợp. |
| completions | Int64 | Số lượt ghi danh có completed_at trong nhóm. |
| completion_days | Int64 | Tổng số ngày hoàn thành của các lượt đã hoàn thành. |

## ClickHouse gold.feed_monthly_revenue

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| month | UInt32 | Tháng 1–12 ở dim_date; YYYYMM ở bảng tổng hợp doanh thu. |
| net_vnd | Int64 | Thực thu sau hoàn tiền = charged_vnd × (1-refunded), quy về kỳ giao dịch gốc. |
| gmv | Int64 | Tổng giá gốc trước giảm giá và hoàn tiền, VND. |
| discount_vnd | Int64 | Số tiền giảm giá, VND; additive trong bảng tổng hợp. |
| refund_vnd | Int64 | Tổng tiền hoàn toàn phần = charged_vnd × refunded, VND. |
| refunds | Int64 | Số giao dịch hoàn tiền toàn phần trong nhóm. |
| payments | UInt64 | Số giao dịch trong nhóm tổng hợp. |

## ClickHouse gold.mv_course_completion_stats

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| course_sk | Int64 | Khóa dimension course = course_id+1000000. |
| enrollments | UInt64 | Số lượt ghi danh trong nhóm tổng hợp. |
| completions | Int64 | Số lượt ghi danh có completed_at trong nhóm. |
| completion_days | Int64 | Tổng số ngày hoàn thành của các lượt đã hoàn thành. |

## ClickHouse gold.mv_monthly_revenue_summary

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| month | UInt32 | Tháng 1–12 ở dim_date; YYYYMM ở bảng tổng hợp doanh thu. |
| net_vnd | Int64 | Thực thu sau hoàn tiền = charged_vnd × (1-refunded), quy về kỳ giao dịch gốc. |
| gmv | Int64 | Tổng giá gốc trước giảm giá và hoàn tiền, VND. |
| discount_vnd | Int64 | Số tiền giảm giá, VND; additive trong bảng tổng hợp. |
| refund_vnd | Int64 | Tổng tiền hoàn toàn phần = charged_vnd × refunded, VND. |
| refunds | Int64 | Số giao dịch hoàn tiền toàn phần trong nhóm. |
| payments | UInt64 | Số giao dịch trong nhóm tổng hợp. |
