"""Scheduled reporting: builds a summary report with Polars and writes it to reports/."""
import os
from datetime import datetime, timezone
from pathlib import Path

import polars as pl
from sqlalchemy import select

from app.database import Record, SessionLocal

REPORT_DIR = Path(os.getenv("REPORT_DIR", "reports"))


def build_report() -> dict:
    with SessionLocal() as s:
        rows = s.execute(select(Record.customer, Record.amount, Record.region,
                                Record.order_date)).all()
    df = pl.DataFrame(rows, schema=["customer", "amount", "region", "order_date"], orient="row")
    if df.is_empty():
        return {"record_count": 0, "file": None, "by_region": []}

    by_region = (df.group_by("region")
                   .agg(pl.col("amount").sum().round(2).alias("total_amount"),
                        pl.len().alias("records"),
                        pl.col("amount").mean().round(2).alias("avg_amount"))
                   .sort("total_amount", descending=True))

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = REPORT_DIR / f"region_report_{stamp}.csv"
    by_region.write_csv(path)
    return {"record_count": df.height, "total_amount": round(df["amount"].sum(), 2),
            "file": str(path), "by_region": by_region.to_dicts()}
