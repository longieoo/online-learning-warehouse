"""Luật nghiệp vụ áp dụng sau bước ép kiểu."""

import re

EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def validate_row(row):
    if "email" in row:
        row["email"] = row["email"].lower()
        if not EMAIL.fullmatch(row["email"]):
            return None, "ERR_INVALID_EMAIL", "Email sai định dạng"
    if "country" in row:
        row["country"] = row["country"].upper()
    if any(
        row.get(col, 0) < 0 for col in ("price_vnd", "original_vnd", "discount_vnd", "charged_vnd")
    ):
        return None, "ERR_NEGATIVE_AMOUNT", "Số tiền âm"
    if "charged_vnd" in row and row["charged_vnd"] != row["original_vnd"] - row["discount_vnd"]:
        return None, "ERR_INVALID_AMOUNT", "Tiền thực thu không khớp giá và giảm giá"
    if (
        row.get("completed_at")
        and row.get("enrolled_at")
        and row["completed_at"] < row["enrolled_at"]
    ):
        return None, "ERR_TIME_INCONSISTENCY", "Hoàn thành trước khi ghi danh"
    if any(row.get(col, 1) <= 0 for col in ("total_questions", "attempt_number", "position")):
        return None, "ERR_INVALID_DOMAIN", "Số câu hỏi, lần thi và vị trí phải dương"
    if any(
        row.get(col, 0) < 0 for col in ("correct_count", "time_spent_seconds", "lessons_completed")
    ):
        return None, "ERR_INVALID_DOMAIN", "Điểm, thời lượng và số bài học phải không âm"
    if row.get("correct_count", 0) > row.get("total_questions", 2**63 - 1):
        return None, "ERR_INVALID_SCORE", "Số câu đúng vượt tổng số câu"
    if row.get("refunded", 0) not in (0, 1):
        return None, "ERR_INVALID_DOMAIN", "Cờ hoàn tiền chỉ nhận 0 hoặc 1"
    if "valid_from" in row and row["valid_from"] >= row["valid_to"]:
        return None, "ERR_TIME_INCONSISTENCY", "Khoảng lịch sử phải có độ dài dương"
    return tuple(row.values()), None, None
