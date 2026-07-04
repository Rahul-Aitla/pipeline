#!/bin/bash
CSV="${1:-transactions.csv}"

if [ ! -f "$CSV" ]; then
  echo "File not found: $CSV"
  exit 1
fi

JOB_ID=$(curl -s --fail http://localhost:8000/jobs/upload -F "file=@$CSV" | python -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
echo "Job started: $JOB_ID"

while true; do
  STATUS=$(curl -s http://localhost:8000/jobs/$JOB_ID/status | python -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "Status: $STATUS"
  [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ] && break
  sleep 1
done

echo ""
echo "--- Final Results ---"
curl -s http://localhost:8000/jobs/$JOB_ID/results | python -m json.tool
