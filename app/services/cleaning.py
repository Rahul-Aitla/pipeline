import uuid
import io
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


DATE_FORMATS = [
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%Y-%m-%d",
]


def parse_date(raw: str) -> date | None:
    from datetime import datetime
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def parse_amount(raw: str) -> Decimal | None:
    cleaned = raw.strip().lstrip("$").replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def clean_row(row: dict[str, str]) -> dict[str, Any] | None:
    txn_id = row.get("txn_id", "").strip()
    if not txn_id:
        txn_id = str(uuid.uuid4())

    raw_date = row.get("date", "").strip()
    parsed_date = parse_date(raw_date)
    if parsed_date is None:
        return None

    amount = parse_amount(row.get("amount", ""))
    if amount is None:
        return None

    currency = row.get("currency", "").strip().upper()
    if not currency:
        currency = "INR"

    status = row.get("status", "").strip().upper()
    if status not in ("SUCCESS", "FAILED", "PENDING"):
        status = "PENDING"

    raw_category = row.get("category", "").strip()
    needs_llm = not raw_category
    category = raw_category if raw_category else "Uncategorised"

    merchant = row.get("merchant", "").strip()
    account_id = row.get("account_id", "").strip()

    return {
        "txn_id": txn_id,
        "date": parsed_date,
        "merchant": merchant,
        "amount": amount,
        "currency": currency,
        "status": status,
        "category": category,
        "account_id": account_id,
        "notes": row.get("notes", "").strip(),
        "needs_llm": needs_llm,
    }


def clean_csv(raw_csv: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(raw_csv))
    cleaned: list[dict[str, Any]] = []
    seen: set[tuple] = set()

    for row in reader:
        result = clean_row(row)
        if result is None:
            continue

        duplicate_key = (
            result["txn_id"],
            result["date"],
            result["merchant"],
            result["amount"],
            result["currency"],
            result["status"],
            result["category"],
            result["account_id"],
        )
        if duplicate_key in seen:
            continue
        seen.add(duplicate_key)

        cleaned.append(result)

    return cleaned
