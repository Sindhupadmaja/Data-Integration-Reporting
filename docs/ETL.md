# ETL design

**Extract:** three source adapters: CSV upload (`/ingest/csv`), JSON file upload (`/ingest/json-file`) and direct API push (`/ingest/api`).

**Transform:** `app/etl.py` maps each source's column names onto one schema (for example `customer_name`, `client` → `customer`). `app/schemas.py` then validates every row with Pydantic: it trims text, cleans currency values, parses four date formats, and rejects rows with a missing customer, a negative or non-numeric amount, or an unreadable date.

**Load:** valid rows go to the `records` table in one transaction. Each load writes an `ingestion_runs` row (received, inserted, rejected, duration) as an audit trail, and the response lists up to 20 rejected rows with reasons.

**Report:** `app/reports.py` aggregates totals by region with Polars and writes a timestamped CSV. APScheduler runs it every 24 hours, and `/reports/run` triggers it on demand.

**Next improvements:** PostgreSQL in Docker Compose, duplicate detection across loads, incremental loads, and data lineage.
