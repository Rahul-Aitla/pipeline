from statistics import median
from decimal import Decimal
from typing import Any

DOMESTIC_MERCHANTS = {"SWIGGY", "OLA", "IRCTC"}


def detect_anomalies(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    amounts_by_key: dict[tuple[str, str], list[Decimal]] = {}
    for txn in transactions:
        key = (txn["account_id"], txn["currency"])
        amounts_by_key.setdefault(key, []).append(txn["amount"])

    medians = {
        key: median(amounts)
        for key, amounts in amounts_by_key.items()
    }

    for txn in transactions:
        reasons = []

        key = (txn["account_id"], txn["currency"])
        threshold = Decimal("3") * medians.get(key, Decimal("0"))
        if txn["amount"] > threshold:
            reasons.append(
                f"Amount {txn['amount']} exceeds 3x {txn['currency']} median ({medians[key]})"
            )

        if txn["currency"] == "USD" and txn["merchant"].upper() in DOMESTIC_MERCHANTS:
            reasons.append(
                f"USD transaction with domestic merchant {txn['merchant']}"
            )

        txn["is_anomaly"] = bool(reasons)
        txn["anomaly_reason"] = "; ".join(reasons) if reasons else None

    return transactions
