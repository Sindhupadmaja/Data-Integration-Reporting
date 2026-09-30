"""Database setup. Set DATABASE_URL to point at PostgreSQL; SQLite is the local default."""
import os
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./integration.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Record(Base):
    __tablename__ = "records"
    id = Column(Integer, primary_key=True)
    customer = Column(String, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    region = Column(String, index=True, nullable=False)
    order_date = Column(Date, index=True, nullable=False)
    source = Column(String, nullable=False)


class IngestionRun(Base):
    """Audit log: one row per ingestion, so every load is traceable."""

    __tablename__ = "ingestion_runs"
    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    received = Column(Integer, nullable=False)
    inserted = Column(Integer, nullable=False)
    rejected = Column(Integer, nullable=False)
    duration_ms = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
