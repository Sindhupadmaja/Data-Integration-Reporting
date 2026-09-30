"""FastAPI service: multi-source ingestion, validation, analytics and scheduled reports."""
import json
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Body, Depends, FastAPI, File, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import IngestionRun, Record, get_db, init_db
from app.etl import load, parse_csv
from app.reports import build_report
from app.schemas import IngestResult


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler = None
    if os.getenv("DISABLE_SCHEDULER") != "1":
        hours = float(os.getenv("REPORT_INTERVAL_HOURS", "24"))
        scheduler = BackgroundScheduler()
        scheduler.add_job(build_report, "interval", hours=hours, id="region_report")
        scheduler.start()
    yield
    if scheduler:
        scheduler.shutdown()


app = FastAPI(title="Data Integration & Reporting API", version="2.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest/csv", response_model=IngestResult)
async def ingest_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        rows = parse_csv(await file.read())
    except UnicodeDecodeError:
        raise HTTPException(400, "File must be UTF-8 encoded CSV")
    return load(rows, source=file.filename or "upload.csv", source_type="csv", db=db)


@app.post("/ingest/json-file", response_model=IngestResult)
async def ingest_json_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        rows = json.loads(await file.read())
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(400, "File must contain valid JSON")
    if not isinstance(rows, list):
        raise HTTPException(400, "JSON must be a list of records")
    return load(rows, source=file.filename or "upload.json", source_type="json", db=db)


@app.post("/ingest/api", response_model=IngestResult)
def ingest_api(records: list[dict] = Body(...), source: str = "api",
               db: Session = Depends(get_db)):
    """For systems that push records directly as a JSON body."""
    return load(records, source=source, source_type="api", db=db)


@app.get("/analytics/summary")
def summary(db: Session = Depends(get_db)):
    total, count, first, last = db.query(func.coalesce(func.sum(Record.amount), 0),
                                         func.count(Record.id),
                                         func.min(Record.order_date),
                                         func.max(Record.order_date)).one()
    return {"total_amount": round(float(total), 2), "record_count": count,
            "first_order": first, "last_order": last}


@app.get("/analytics/by-customer")
def by_customer(limit: int = 10, db: Session = Depends(get_db)):
    rows = (db.query(Record.customer, func.sum(Record.amount).label("total"))
              .group_by(Record.customer).order_by(func.sum(Record.amount).desc())
              .limit(limit).all())
    return [{"customer": c, "total": round(float(t), 2)} for c, t in rows]


@app.get("/analytics/by-region")
def by_region(db: Session = Depends(get_db)):
    rows = (db.query(Record.region, func.sum(Record.amount), func.count(Record.id))
              .group_by(Record.region).order_by(func.sum(Record.amount).desc()).all())
    return [{"region": r, "total": round(float(t), 2), "records": n} for r, t, n in rows]


@app.get("/ingestion/runs")
def ingestion_runs(db: Session = Depends(get_db)):
    runs = db.query(IngestionRun).order_by(IngestionRun.id.desc()).limit(50).all()
    return [{"id": r.id, "source": r.source, "type": r.source_type, "received": r.received,
             "inserted": r.inserted, "rejected": r.rejected, "duration_ms": r.duration_ms,
             "created_at": r.created_at} for r in runs]


@app.post("/reports/run")
def run_report():
    """Trigger the scheduled report on demand."""
    return build_report()
