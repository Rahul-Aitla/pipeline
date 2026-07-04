from datetime import date
from decimal import Decimal
from app.services.cleaning import clean_csv, parse_date, parse_amount


def test_date_normalization():
    assert parse_date("04-09-2024") == date(2024, 9, 4)
    assert parse_date("2024/02/05") == date(2024, 2, 5)
    assert parse_date("2024-07-15") == date(2024, 7, 15)
    assert parse_date("invalid") is None


def test_amount_strips_dollar():
    assert parse_amount("$11325.79") == Decimal("11325.79")
    assert parse_amount("10882.55") == Decimal("10882.55")


def test_duplicate_removal():
    csv = """txn_id,date,merchant,amount,currency,status,category,account_id,notes
A,04-09-2024,Flipkart,100,INR,SUCCESS,Shopping,ACC001,
B,04-09-2024,Amazon,200,INR,SUCCESS,Shopping,ACC002,
A,04-09-2024,Flipkart,100,INR,SUCCESS,Shopping,ACC001,"""
    result = clean_csv(csv)
    assert len(result) == 2


def test_currency_aware_median():
    from app.services.anomaly import detect_anomalies

    txns = [
        {"txn_id": "I1", "merchant": "A", "amount": Decimal("10"), "currency": "INR",
         "status": "SUCCESS", "category": "X", "account_id": "ACC1",
         "date": date(2024, 1, 1), "notes": "", "needs_llm": False},
        {"txn_id": "I2", "merchant": "A", "amount": Decimal("12"), "currency": "INR",
         "status": "SUCCESS", "category": "X", "account_id": "ACC1",
         "date": date(2024, 1, 1), "notes": "", "needs_llm": False},
        {"txn_id": "U1", "merchant": "B", "amount": Decimal("5"), "currency": "USD",
         "status": "SUCCESS", "category": "X", "account_id": "ACC1",
         "date": date(2024, 1, 1), "notes": "", "needs_llm": False},
        {"txn_id": "U2", "merchant": "B", "amount": Decimal("7"), "currency": "USD",
         "status": "SUCCESS", "category": "X", "account_id": "ACC1",
         "date": date(2024, 1, 1), "notes": "", "needs_llm": False},
        {"txn_id": "I3", "merchant": "C", "amount": Decimal("100"), "currency": "INR",
         "status": "SUCCESS", "category": "X", "account_id": "ACC1",
         "date": date(2024, 1, 1), "notes": "", "needs_llm": False},
    ]
    result = detect_anomalies(txns)
    flagged = {t["txn_id"] for t in result if t["is_anomaly"]}
    assert "I3" in flagged
    assert "U1" not in flagged
    assert "U2" not in flagged
    assert "I1" not in flagged
    assert "I2" not in flagged


def test_outlier_detection():
    from app.services.anomaly import detect_anomalies

    txns = [
        {"txn_id": "N1", "merchant": "A", "amount": Decimal("10"), "currency": "INR",
         "status": "SUCCESS", "category": "X", "account_id": "ACC1",
         "date": date(2024, 1, 1), "notes": "", "needs_llm": False},
        {"txn_id": "N2", "merchant": "B", "amount": Decimal("12"), "currency": "INR",
         "status": "SUCCESS", "category": "X", "account_id": "ACC1",
         "date": date(2024, 1, 2), "notes": "", "needs_llm": False},
        {"txn_id": "N3", "merchant": "C", "amount": Decimal("11"), "currency": "INR",
         "status": "SUCCESS", "category": "X", "account_id": "ACC1",
         "date": date(2024, 1, 3), "notes": "", "needs_llm": False},
        {"txn_id": "N4", "merchant": "D", "amount": Decimal("100"), "currency": "INR",
         "status": "SUCCESS", "category": "X", "account_id": "ACC1",
         "date": date(2024, 1, 4), "notes": "", "needs_llm": False},
    ]
    result = detect_anomalies(txns)
    flagged = [t for t in result if t["is_anomaly"]]
    assert len(flagged) == 1
    assert flagged[0]["txn_id"] == "N4"


def test_usd_domestic_anomaly():
    from app.services.anomaly import detect_anomalies

    txns = [
        {"txn_id": "T1", "merchant": "Swiggy", "amount": Decimal("50"), "currency": "USD",
         "status": "SUCCESS", "category": "Food", "account_id": "ACC1",
         "date": date(2024, 1, 1), "notes": "", "needs_llm": False},
        {"txn_id": "T2", "merchant": "Swiggy", "amount": Decimal("50"), "currency": "INR",
         "status": "SUCCESS", "category": "Food", "account_id": "ACC1",
         "date": date(2024, 1, 1), "notes": "", "needs_llm": False},
        {"txn_id": "T3", "merchant": "Amazon", "amount": Decimal("50"), "currency": "USD",
         "status": "SUCCESS", "category": "Shopping", "account_id": "ACC1",
         "date": date(2024, 1, 1), "notes": "", "needs_llm": False},
    ]
    result = detect_anomalies(txns)
    flagged = {t["txn_id"]: t["anomaly_reason"] for t in result if t["is_anomaly"]}
    assert "T1" in flagged
    assert "T2" not in flagged
    assert "T3" not in flagged
