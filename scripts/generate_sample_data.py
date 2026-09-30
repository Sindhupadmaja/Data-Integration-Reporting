"""Generate realistic messy sample data: a CSV export and a JSON CRM feed with different schemas.

Usage: python scripts/generate_sample_data.py [rows_per_source]
About 5% of rows are deliberately invalid so the validation layer has something to catch.
"""
import csv
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 25_000
OUT = Path("data")
OUT.mkdir(exist_ok=True)
CUSTOMERS = [f"Customer {i:04d}" for i in range(1, 501)]
REGIONS = ["east", "west", "north", "south", "central"]


def random_row():
    d = date(2026, 1, 1) + timedelta(days=random.randint(0, 240))
    row = {"customer": random.choice(CUSTOMERS), "amount": round(random.uniform(10, 5000), 2),
           "region": random.choice(REGIONS), "date": d}
    r = random.random()
    if r < 0.02:
        row["customer"] = ""                    # missing customer
    elif r < 0.035:
        row["amount"] = -row["amount"]          # negative amount
    elif r < 0.05:
        row["date"] = "unknown"                 # bad date
    return row


# Source 1: finance CSV export (customer_name / value / area / dd/mm/yyyy dates)
with open(OUT / "finance_export.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["customer_name", "value", "area", "date"])
    for _ in range(N):
        r = random_row()
        d = r["date"].strftime("%d/%m/%Y") if isinstance(r["date"], date) else r["date"]
        w.writerow([r["customer"], r["amount"], r["region"], d])

# Source 2: CRM JSON feed (client / total / territory / ISO dates)
records = []
for _ in range(N):
    r = random_row()
    d = r["date"].isoformat() if isinstance(r["date"], date) else r["date"]
    records.append({"client": r["customer"], "total": r["amount"], "territory": r["region"],
                    "transaction_date": d})
(OUT / "crm_feed.json").write_text(json.dumps(records))
print(f"Wrote {N:,} rows to data/finance_export.csv and {N:,} to data/crm_feed.json")
