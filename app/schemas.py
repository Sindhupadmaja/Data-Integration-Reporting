"""Pydantic models: every incoming record must pass SalesRecord before it is stored."""
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y", "%Y/%m/%d")


class SalesRecord(BaseModel):
    """Canonical schema that all sources are normalized into."""

    customer: str = Field(min_length=1, max_length=200)
    amount: float = Field(ge=0)
    region: str = Field(default="UNKNOWN", max_length=50)
    order_date: date

    @field_validator("customer", mode="before")
    @classmethod
    def clean_customer(cls, v):
        return str(v).strip() if v is not None else ""

    @field_validator("region", mode="before")
    @classmethod
    def clean_region(cls, v):
        v = str(v).strip().upper() if v not in (None, "") else "UNKNOWN"
        return v

    @field_validator("amount", mode="before")
    @classmethod
    def clean_amount(cls, v):
        # Accept "1,200.50" and "$1200.50" as well as plain numbers.
        if isinstance(v, str):
            v = v.replace(",", "").replace("$", "").strip()
        return v

    @field_validator("order_date", mode="before")
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, (date, datetime)):
            return v if isinstance(v, date) else v.date()
        text = str(v).strip()
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"unrecognized date format: {text!r}")


class RejectedRow(BaseModel):
    row_number: int
    reason: str


class IngestResult(BaseModel):
    source: str
    source_type: str
    received: int
    inserted: int
    rejected: int
    duration_ms: float
    sample_rejections: list[RejectedRow]
