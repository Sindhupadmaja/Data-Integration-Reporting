"""Extract -> Transform (normalize + validate) -> Load."""
import csv
import io
import time

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import IngestionRun, Record
from app.schemas import IngestResult, RejectedRow, SalesRecord

# Different sources name the same field differently; map them all to one schema.
COLUMN_ALIASES = {
    "customer": ["customer", "customer_name", "client", "client_name"],
    "amount": ["amount", "value", "total", "sale_amount"],
    "region": ["region", "area", "territory"],
    "order_date": ["order_date", "date", "txn_date", "transaction_date"],
}
MAX_SAMPLE_REJECTIONS = 20


def normalize(row: dict) -> dict:
    """Map a raw row with any known column names onto canonical field names."""
    lowered = {str(k).strip().lower(): v for k, v in row.items() if k is not None}
    out = {}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lowered and lowered[alias] not in (None, ""):
                out[field] = lowered[alias]
                break
    return out


def parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig")  # handles Excel's BOM
    return list(csv.DictReader(io.StringIO(text)))


def load(rows: list[dict], source: str, source_type: str, db: Session) -> IngestResult:
    start = time.perf_counter()
    valid, rejections = [], []
    for i, raw in enumerate(rows, start=1):
        try:
            rec = SalesRecord(**normalize(raw))
            valid.append(Record(**rec.model_dump(), source=source))
        except ValidationError as e:
            err = e.errors()[0]
            field = ".".join(str(p) for p in err["loc"]) or "row"
            rejections.append(RejectedRow(row_number=i, reason=f"{field}: {err['msg']}"))
    db.add_all(valid)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    db.add(IngestionRun(source=source, source_type=source_type, received=len(rows),
                        inserted=len(valid), rejected=len(rejections), duration_ms=duration_ms))
    db.commit()
    return IngestResult(source=source, source_type=source_type, received=len(rows),
                        inserted=len(valid), rejected=len(rejections), duration_ms=duration_ms,
                        sample_rejections=rejections[:MAX_SAMPLE_REJECTIONS])
