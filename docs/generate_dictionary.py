"""Generate exact field/type documentation from the running schema."""

from contextlib import closing
from etl.common import ROOT, ch_connect, source_connect, staging_connect, project_lock

DESCRIPTIONS = {
    "user_id": "Khóa nghiệp vụ học viên, dùng distinct learner qua nhiều phiên bản.",
    "history_id": "Khóa phiên bản lịch sử nguồn; một user có thể nhiều dòng.",
    "full_name": "Tên giả lập Faker; Silver trim khoảng trắng.",
    "email": "Email giả example.invalid; Bronze giữ raw, Silver trim và lowercase.",
    "city": "Thành phố; lịch sử lưu tại user_history / dim_user.",
    "country": "ISO alpha-2; dữ liệu hiện tại VN, Silver uppercase.",
    "created_at": "Thời điểm tạo UTC, đầu kỳ 2022 trong bộ dữ liệu này.",
    "valid_from": "Bắt đầu hiệu lực SCD2, inclusive (UTC).",
    "valid_to": "Kết thúc hiệu lực SCD2, exclusive; sentinel 2100-01-01.",
    "is_current": "1 nếu phiên bản hiện hành (valid_to=2100-01-01), ngược lại 0.",
    "instructor_id": "Khóa nghiệp vụ giảng viên.",
    "expertise": "Lĩnh vực chuyên môn giảng viên giả lập.",
    "course_id": "Khóa nghiệp vụ khóa học.",
    "title": "Tiêu đề khóa/bài/quiz theo bảng.",
    "category": "Nhóm khóa: Data, Programming, Business, Design, Language.",
    "difficulty": "beginner, intermediate, advanced.",
    "price_vnd": "Giá hiện tại khóa, VND integer ≥0.",
    "lesson_id": "Khóa nghiệp vụ bài học, mỗi khóa có 10 bài.",
    "position": "Thứ tự bài trong khóa, 1–10.",
    "quiz_id": "Khóa nghiệp vụ quiz, một quiz/khóa.",
    "total_questions": "Số câu hỏi, hiện tại 20 mỗi quiz/attempt.",
    "method_id": "Khóa nghiệp vụ phương thức thanh toán.",
    "method_name": "bank_transfer, card, wallet.",
    "enrollment_id": "Khóa ghi danh; unique user/course; degenerate reference trên facts.",
    "enrolled_at": "Thời điểm ghi danh UTC; Gold user version được tra tại thời điểm này.",
    "completed_at": "Thời điểm hoàn thành UTC; nullable cho enrollment chưa hoàn thành, không null cho lesson completion.",
    "lessons_completed": "Số bài đã hoàn thành cuối kỳ; 10 nếu complete, 6 nếu chưa complete trong generator.",
    "payment_id": "Khóa nghiệp vụ thanh toán, 1 payment/enrollment.",
    "transaction_id": "Mã giao dịch unique TXN-…; degenerate dimension.",
    "paid_at": "Thời điểm thanh toán UTC = enrolled_at + 60 giây trong generator.",
    "original_vnd": "Giá gốc tại giao dịch, VND integer.",
    "discount_vnd": "Số tiền giảm, VND integer trong [0,original_vnd].",
    "charged_vnd": "Số tiền thu trước hoàn tiền = original_vnd - discount_vnd.",
    "refunded": "Cờ 0/1 hoàn tiền toàn phần; không có thời điểm refund riêng.",
    "net_vnd": "charged_vnd × (1-refunded), giữ lại cuối kỳ quy về ngày giao dịch gốc.",
    "completion_id": "Khóa sự kiện hoàn thành bài; unique enrollment/lesson.",
    "time_spent_seconds": "Thời gian học/làm quiz, giây dương; additive trên events.",
    "attempt_id": "Khóa lần làm quiz.",
    "attempt_number": "Lần 1 hoặc 2 trong mỗi enrollment/quiz.",
    "attempted_at": "Thời điểm làm quiz UTC.",
    "correct_count": "Số câu đúng từ 0 đến total_questions.",
    "is_passed": "1 khi correct_count/total_questions ≥70%, ngược lại 0.",
    "is_completed": "1 khi enrollment có completed_at; metric numerator completion rate.",
    "date_sk": "Khóa ngày YYYYMMDD, khóa 0 dành cho unknown.",
    "enrolled_date_sk": "Role enrolled của dim_date, suy từ enrolled_at.",
    "completed_date_sk": "Role completed của dim_date; 0 nếu chưa complete.",
    "full_date": "Ngày lịch; 1970-01-01 là placeholder riêng dòng unknown.",
    "year": "Năm lịch (0 cho unknown).",
    "quarter": "Quý 1–4 (0 cho unknown).",
    "month": "Tháng 1–12 (0 cho unknown).",
    "day": "Ngày trong tháng (0 cho unknown).",
    "user_sk": "Khóa thay thế theo phiên bản SCD2 = history_id+10000000.",
    "course_sk": "Khóa dimension course = course_id+1000000.",
    "instructor_sk": "Khóa dimension instructor = instructor_id+2000000.",
    "lesson_sk": "Khóa dimension lesson = lesson_id+3000000.",
    "quiz_sk": "Khóa dimension quiz = quiz_id+4000000.",
    "method_sk": "Khóa dimension method = method_id+5000000.",
    "_run_id": "UUID hex nhận diện snapshot ETL.",
    "_loaded_at": "Thời điểm ingest UTC.",
    "_source": "Tên nguồn postgres.oltp.<table>.",
}


DESCRIPTIONS.update(
    {
        "updated_at": "Thời điểm phiên bản nguồn được ghi, UTC. Trigger cập nhật tự động.",
        "dw_revision": "Revision tăng đơn điệu từ sequence; 0 là baseline bulk seed hoặc dữ liệu nâng cấp.",
        "revision": "Số thứ tự thay đổi dùng chống replay bản cũ.",
        "source_xid": "Full transaction ID của giao dịch nguồn ghi journal.",
        "source_id": "Khóa nghiệp vụ của dòng nguồn.",
        "table_name": "Tên bảng nguồn thuộc danh sách contract của ETL.",
        "operation": "INSERT, UPDATE, DELETE hoặc trạng thái delta được ETL lưu.",
        "raw_payload": "JSON gốc để tái hiện thay đổi hoặc điều tra dòng lỗi.",
        "changed_at": "Thời điểm trigger ghi sự kiện vào journal.",
        "source_updated_at": "updated_at của phiên bản bị từ chối.",
        "error_code": "Mã phân loại lỗi schema, nghiệp vụ hoặc quan hệ.",
        "rejection_reason": "Mô tả nguyên nhân cách ly.",
        "detected_at": "Thời điểm phát hiện lỗi trong staging.",
        "resolved_at": "Thời điểm phiên bản nguồn hợp lệ thay thế lỗi; NULL khi chưa giải quyết.",
        "last_processed_time": "Mốc timestamp tham khảo sau lần công bố; không dùng thay journal checkpoint.",
        "last_processed_id": "Khóa nguồn đi cùng mốc timestamp tham khảo.",
        "last_run_id": "Run ID công bố đã xác nhận mốc tham khảo.",
        "run_id": "UUID của lần chạy pipeline.",
        "phase": "extracting, building, publishing, completed, failed hoặc recovered.",
        "manifest": "JSON mô tả run, counts, fingerprint, quality và số đo.",
        "publication": "JSON kế hoạch UUID cũ/mới phục vụ rollback từng bảng.",
        "started_at": "Thời điểm bắt đầu lần chạy UTC.",
        "finished_at": "Thời điểm hoàn tất hoặc lỗi UTC.",
        "singleton": "Khóa boolean duy nhất, bắt buộc true.",
        "safe_xid": "Checkpoint transaction ID; nhận journal từ giá trị này ở lần kế tiếp.",
        "published_at": "Thời điểm commit trạng thái đã công bố.",
        "needs_full": "Full stage đã commit và cần dựng Gold đầy đủ trước khi xóa cờ.",
        "gmv": "Tổng giá gốc trước giảm giá và hoàn tiền, VND.",
        "net_vnd": "Thực thu sau hoàn tiền = charged_vnd × (1-refunded), quy về kỳ giao dịch gốc.",
        "discount_vnd": "Số tiền giảm giá, VND; additive trong bảng tổng hợp.",
        "payments": "Số giao dịch trong nhóm tổng hợp.",
        "refunds": "Số giao dịch hoàn tiền toàn phần trong nhóm.",
        "enrollments": "Số lượt ghi danh trong nhóm tổng hợp.",
        "completions": "Số lượt ghi danh có completed_at trong nhóm.",
        "completion_days": "Tổng số ngày hoàn thành của các lượt đã hoàn thành.",
    }
)
DESCRIPTIONS["email"] = "Email giả example.invalid; Silver trim và lowercase."
DESCRIPTIONS["month"] = "Tháng 1–12 ở dim_date; YYYYMM ở bảng tổng hợp doanh thu."
DESCRIPTIONS["refund_vnd"] = "Tổng tiền hoàn toàn phần = charged_vnd × refunded, VND."


def main():
    lines = [
        "# Data dictionary · v3",
        "",
        "Sinh từ PostgreSQL và ClickHouse đang chạy. Timestamps theo UTC, tiền nguyên VND. ",
        "Gold dùng DateTime cho sự kiện, độ chính xác giây. Khóa ngoại Gold được kiểm tra bằng quality gate.",
        "Grain, công thức và phạm vi xem architecture.md và mapping.md.",
        "",
    ]

    def description(column):
        return DESCRIPTIONS.get(column, "Cột được suy từ DDL; xem mapping của bảng tương ứng.")

    with project_lock(shared=True):
        for connector, schemas, label in [
            (source_connect, ("oltp",), "learning_oltp"),
            (staging_connect, ("silver", "staging", "quarantine"), "dwh_staging"),
        ]:
            with closing(connector()) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT table_schema,table_name,column_name,data_type,is_nullable
                    FROM information_schema.columns WHERE table_schema=ANY(%s)
                    ORDER BY table_schema,table_name,ordinal_position""",
                    (list(schemas),),
                )
                previous = None
                for schema, table, column, kind, nullable in cursor.fetchall():
                    if (schema, table) != previous:
                        lines += [
                            f"## PostgreSQL {label}.{schema}.{table}",
                            "",
                            "| Cột | Kiểu | Nullable | Ý nghĩa |",
                            "|---|---|---|---|",
                        ]
                        previous = schema, table
                    lines.append(f"| {column} | {kind} | {nullable} | {description(column)} |")
        with closing(ch_connect()) as client:
            for (table,) in client.query("SHOW TABLES FROM gold").result_rows:
                lines += [
                    "",
                    f"## ClickHouse gold.{table}",
                    "",
                    "| Cột | Kiểu | Ý nghĩa |",
                    "|---|---|---|",
                ]
                for column, kind, *_ in client.query(f"DESCRIBE TABLE gold.{table}").result_rows:
                    lines.append(f"| {column} | {kind} | {description(column)} |")
    (ROOT / "docs/data_dictionary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
