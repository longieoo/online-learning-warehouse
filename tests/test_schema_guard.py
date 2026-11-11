import unittest

from etl.schema_guard import normalize


class SchemaGuardTests(unittest.TestCase):
    def test_text_amount_and_invalid_amount(self):
        self.assertEqual(normalize(["price_vnd"], ["bigint"], ["120"])[0], (120,))
        self.assertEqual(
            normalize(["price_vnd"], ["bigint"], ["invalid"])[1], "ERR_SCHEMA_TYPE_MISMATCH"
        )
        self.assertEqual(normalize(["price_vnd"], ["bigint"], [-5])[1], "ERR_NEGATIVE_AMOUNT")

    def test_bad_email_and_missing_lesson_timestamp(self):
        self.assertEqual(normalize(["email"], ["text"], ["bad-email"])[1], "ERR_INVALID_EMAIL")
        self.assertEqual(
            normalize(["completed_at"], ["timestamp without time zone"], [None])[1],
            "ERR_SCHEMA_TYPE_MISMATCH",
        )

    def test_enrollment_completion_before_enrollment(self):
        cols = ["enrolled_at", "completed_at"]
        types = ["timestamp without time zone"] * 2
        self.assertEqual(
            normalize(cols, types, ["2024-01-02", "2024-01-01"])[1], "ERR_TIME_INCONSISTENCY"
        )
