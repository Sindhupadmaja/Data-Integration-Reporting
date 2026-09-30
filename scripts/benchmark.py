"""Ingest the generated sample files end to end and print measured results.

Usage: python scripts/generate_sample_data.py && python scripts/benchmark.py
"""
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `app` importable

tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/bench.db"
os.environ["REPORT_DIR"] = f"{tmp}/reports"
os.environ["DISABLE_SCHEDULER"] = "1"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

with TestClient(app) as c:
    start = time.perf_counter()
    with open("data/finance_export.csv", "rb") as f:
        a = c.post("/ingest/csv", files={"file": ("finance_export.csv", f, "text/csv")}).json()
    with open("data/crm_feed.json", "rb") as f:
        b = c.post("/ingest/json-file", files={"file": ("crm_feed.json", f, "application/json")}).json()
    report = c.post("/reports/run").json()
    total = time.perf_counter() - start

for r in (a, b):
    print(f"{r['source']:<20} received={r['received']:>7,} inserted={r['inserted']:>7,} "
          f"rejected={r['rejected']:>6,} ({r['rejected'] / r['received']:.1%})  {r['duration_ms']:,.0f} ms")
print(f"Report rows by region: {len(report['by_region'])}, records reported: {report['record_count']:,}")
print(f"End-to-end (2 sources + report): {total:.2f} s")
