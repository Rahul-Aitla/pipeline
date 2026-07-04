from datetime import datetime, timezone
from decimal import Decimal
from app.celery_app import celery_app
from app.database import create_tables, SessionLocal
from app.services.cleaning import clean_csv
from app.services.anomaly import detect_anomalies
from app.services.llm_client import classify_categories, generate_summary
from app.models.job import Job
from app.models.transaction import Transaction
from app.models.job_summary import JobSummary


@celery_app.task(bind=True, max_retries=3)
def process_transactions(self, job_id: str):
    create_tables()
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        job.status = "processing"
        db.commit()

        raw_rows = job.raw_csv.count("\n")
        job.row_count_raw = raw_rows

        cleaned = clean_csv(job.raw_csv)
        cleaned = detect_anomalies(cleaned)

        llm_classify_rows = [r for r in cleaned if r["needs_llm"]]
        llm_results = None
        if llm_classify_rows:
            llm_results = classify_categories(llm_classify_rows)

        llm_map: dict[str, str] = {}
        llm_failed_set: set[str] = set()
        if llm_results:
            for item in llm_results:
                txn_id = item.get("txn_id")
                cat = item.get("category")
                if txn_id and cat:
                    llm_map[txn_id] = cat
        elif llm_classify_rows:
            llm_failed_set = {r["txn_id"] for r in llm_classify_rows}

        txns = []
        for row in cleaned:
            txn = Transaction(
                job_id=job.id,
                txn_id=row["txn_id"],
                date=row["date"],
                merchant=row["merchant"],
                amount=row["amount"],
                currency=row["currency"],
                status=row["status"],
                category=row["category"],
                account_id=row["account_id"],
                is_anomaly=row["is_anomaly"],
                anomaly_reason=row["anomaly_reason"],
            )

            txn_id = row["txn_id"]
            if txn_id in llm_map:
                txn.llm_category = llm_map[txn_id]
                txn.category = llm_map[txn_id]
            if txn_id in llm_failed_set:
                txn.llm_failed = True

            txns.append(txn)

        db.bulk_save_objects(txns)
        db.commit()

        job.row_count_clean = len(txns)

        total_inr = sum(
            t.amount for t in txns if t.currency == "INR" and t.status == "SUCCESS"
        )
        total_usd = sum(
            t.amount for t in txns if t.currency == "USD" and t.status == "SUCCESS"
        )
        merchant_totals: dict[str, Decimal] = {}
        for t in txns:
            merchant_totals[t.merchant] = (
                merchant_totals.get(t.merchant, Decimal("0")) + t.amount
            )
        top_merchants = sorted(
            merchant_totals, key=merchant_totals.get, reverse=True
        )[:3]

        anomaly_count = sum(1 for t in txns if t.is_anomaly)

        stats = {
            "total_inr": float(total_inr),
            "total_usd": float(total_usd),
            "top_merchants": top_merchants,
            "anomaly_count": anomaly_count,
            "total_txns": len(txns),
        }

        llm_summary = generate_summary(stats)

        summary = JobSummary(
            job_id=job.id,
            total_spend_inr=total_inr,
            total_spend_usd=total_usd,
            top_merchants=top_merchants,
            anomaly_count=anomaly_count,
            narrative=llm_summary.get("narrative") if llm_summary else None,
            risk_level=llm_summary.get("risk_level", "low") if llm_summary else "low",
        )
        db.add(summary)

        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as exc:
        db.rollback()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(exc)
                db.commit()
        except Exception:
            db.rollback()
        raise self.retry(exc=exc, countdown=2)
    finally:
        db.close()
