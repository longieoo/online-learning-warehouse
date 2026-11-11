"""Kiểm tra hợp đồng cột và phân loại các dòng trước khi ghi staging."""

import re
from datetime import datetime, timezone
from etl.validator import validate_row


def normalize(columns, types, values):
    row = dict(zip(columns, values))
    try:
        for col, kind in zip(columns, types):
            value = row[col]
            if value is None and col == "completed_at" and "enrolled_at" in columns:
                continue
            if kind == "bigint":
                if isinstance(value, bool) or (
                    not isinstance(value, int) and not re.fullmatch(r"[+-]?\d+", str(value))
                ):
                    raise ValueError(col)
                row[col] = int(value)
                if not -(2**63) <= row[col] < 2**63:
                    raise ValueError(col)
            elif kind.startswith("timestamp"):
                parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
                if parsed.tzinfo is not None:
                    parsed = parsed.astimezone(timezone.utc)
                if kind == "timestamp without time zone":
                    parsed = parsed.replace(tzinfo=None)
                row[col] = parsed
            elif isinstance(value, str):
                row[col] = value.strip()
            else:
                raise ValueError(col)
    except (ValueError, TypeError, OverflowError) as exc:
        return None, "ERR_SCHEMA_TYPE_MISMATCH", str(exc)
    return validate_row(row)
