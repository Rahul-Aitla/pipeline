import os
import time
import json
from typing import Any

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL = "llama-3.1-8b-instant"

CATEGORIES = [
    "Food", "Shopping", "Travel", "Transport",
    "Utilities", "Cash Withdrawal", "Entertainment", "Other",
]

MAX_RETRIES = 3
BASE_DELAY = 2


def _get_client():
    from groq import Groq
    return Groq(api_key=GROQ_API_KEY)


def classify_categories(rows: list[dict[str, Any]]) -> list[dict[str, str]] | None:
    if not rows:
        return []
    if not GROQ_API_KEY:
        return None

    prompt_rows = [
        {"txn_id": r["txn_id"], "merchant": r["merchant"], "notes": r.get("notes", "")}
        for r in rows
    ]

    prompt = f"""You are a transaction categoriser. Assign one of these categories to each transaction: {', '.join(CATEGORIES)}.

Return ONLY a JSON array of objects with keys "txn_id" and "category". No explanation, no markdown.

Transactions:
{json.dumps(prompt_rows, indent=2)}"""

    for attempt in range(MAX_RETRIES):
        try:
            client = _get_client()
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            data = json.loads(raw)
            if isinstance(data, dict) and "transactions" in data:
                data = data["transactions"]
            if isinstance(data, list):
                return data
            return None
        except Exception:
            if attempt < MAX_RETRIES - 1:
                time.sleep(BASE_DELAY ** (attempt + 1))
            else:
                return None
    return None


def generate_summary(stats: dict[str, Any]) -> dict[str, Any] | None:
    if not GROQ_API_KEY:
        return None

    prompt = f"""You are a financial analyst. Given these transaction statistics, produce a JSON summary.

Statistics:
- Total INR spend: {stats['total_inr']}
- Total USD spend: {stats['total_usd']}
- Top 3 merchants: {stats['top_merchants']}
- Anomaly count: {stats['anomaly_count']}
- Total transactions: {stats['total_txns']}

Return ONLY a JSON object with these exact keys:
- narrative: a 2-3 sentence spending analysis in plain English
- risk_level: one of "low", "medium", or "high"

No explanation, no markdown. Return only valid JSON."""

    for attempt in range(MAX_RETRIES):
        try:
            client = _get_client()
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            return json.loads(raw)
        except Exception:
            if attempt < MAX_RETRIES - 1:
                time.sleep(BASE_DELAY ** (attempt + 1))
            else:
                return None
    return None
