# Transaction Pipeline

Backend API for processing dirty CSV financial transactions with LLM-powered classification and anomaly detection.

## Stack

- FastAPI (API)
- PostgreSQL (database)
- Celery + Redis (async job queue)
- Groq (LLM classification & narrative)
- Docker Compose (orchestration)

## Quick Start

```bash
# 1. Clone the repo
git clone <repo-url>
cd transaction-pipeline

# 2. Set your Groq API key
echo "GROQ_API_KEY=your_key_here" > .env

# 3. Start everything
docker compose up --build
```

Visit http://localhost:8000/docs for interactive API docs.

## API Endpoints

### Upload a CSV

```bash
curl -X POST http://localhost:8000/jobs/upload \
  -F "file=@transactions.csv"
```

### Check job status

```bash
curl http://localhost:8000/jobs/{job_id}/status
```

### Get full results

```bash
curl http://localhost:8000/jobs/{job_id}/results
```

### List all jobs

```bash
curl http://localhost:8000/jobs?status=completed
```

## Design Decisions

- **No Alembic**: `Base.metadata.create_all()` runs on startup — no migration overhead.
- **Raw CSV in DB**: Avoids Docker volume-sharing issues across containers.
- **Decimal for money**: No float rounding errors.
- **Batch LLM calls**: One Groq API call for all missing-category rows instead of N calls.
- **Graceful LLM failure**: Retries with exponential backoff (2s/4s/8s); job continues if LLM is down.
- **Total spend = SUCCESS only**: `total_spend_inr` and `total_spend_usd` include only SUCCESS transactions. FAILED/PENDING are excluded since "total spend" implies completed transactions. Category breakdown uses the same filter.
- **Currency-aware anomaly detection**: The 3× median outlier rule groups by `(account_id, currency)` pair rather than account alone, so INR and USD amounts are never compared against each other.
- **USD-domestic merchant rule**: The domestic merchant list is `{Swiggy, Ola, IRCTC}` per the spec. The provided dataset has zero USD rows for these merchants, so the rule is untested at integration level — it is covered by a unit test (`test_usd_domestic_anomaly`). Extending the merchant list is a one-line config change.
