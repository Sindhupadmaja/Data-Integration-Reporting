# Data Integration & Reporting API

![CI](https://github.com/Sindhupadmaja/Data-Integration-Reporting/actions/workflows/ci.yml/badge.svg)

A FastAPI service that pulls sales data from **three kinds of sources** (CSV files, JSON files, and API pushes), maps each source's different column names onto one schema, **validates every record with Pydantic**, stores the clean data, and produces **scheduled reports with Polars**. Every load is logged, and every rejected row comes back with a reason.

> Originally built in June 2023; moved to GitHub and extended in September 2026.


## Why it exists

Finance and operations teams often get the same data from several systems, each with its own column names, date formats and quality problems. Before anyone can report on it, someone has to clean it by hand. This service automates that step: messy data goes in, and reporting-ready data plus an audit trail come out.

## Measured results

Run on generated sample data: 25,000 rows per source, about 5% deliberately invalid.

| Source | Rows received | Inserted | Rejected | Load time |
|---|---|---|---|---|
| `finance_export.csv` (dd/mm/yyyy dates, `customer_name`/`value`) | 25,000 | 23,777 | 1,223 (4.9%) | ~1.1 s |
| `crm_feed.json` (ISO dates, `client`/`total`) | 25,000 | 23,680 | 1,320 (5.3%) | ~0.9 s |

- **50,000 records from 2 differently-structured sources** ingested, validated and reported in about **5 seconds** end to end
- **14 automated tests, 96% code coverage**, run by GitHub Actions on every push

Reproduce it yourself:

```bash
python scripts/generate_sample_data.py   # creates data/finance_export.csv and data/crm_feed.json
python scripts/benchmark.py              # ingests both, runs the report, prints the numbers
```

## How it works

```
CSV file ─┐
JSON file ─┼─► normalize column names ─► Pydantic validation ─┬─► records table ─► analytics endpoints
API push ─┘   (customer_name → customer,   (types, ranges,     │                  └► scheduled Polars report (CSV)
               value → amount, …)           4 date formats)     └─► rejected rows returned with reasons
                                                                 ingestion_runs table: audit log of every load
```

**Validation rules** (`app/schemas.py`): customer must be non-empty; amount must be a number ≥ 0 (values like `$1,200.50` are cleaned); dates are accepted in four formats; a missing region defaults to `UNKNOWN`.

## Tech stack

| Area | Tools |
|---|---|
| API | FastAPI, Uvicorn |
| Validation | Pydantic v2 |
| Storage | SQLAlchemy (SQLite by default; set `DATABASE_URL` for PostgreSQL) |
| Reporting | Polars, APScheduler |
| Testing and CI | pytest, pytest-cov, GitHub Actions |
| Deployment | Docker, Docker Compose |

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/ingest/csv` | Upload a CSV file |
| POST | `/ingest/json-file` | Upload a JSON file (a list of records) |
| POST | `/ingest/api?source=name` | Push records directly as a JSON body |
| GET | `/analytics/summary` | Total amount, record count, date range |
| GET | `/analytics/by-customer` | Top customers by amount |
| GET | `/analytics/by-region` | Totals by region |
| GET | `/ingestion/runs` | Audit log of every load |
| POST | `/reports/run` | Run the scheduled report now |

## Run it

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs to try every endpoint in the browser. The report also runs automatically every 24 hours (set `REPORT_INTERVAL_HOURS` to change it) and saves to `reports/`.

With Docker: `docker compose up --build`

## Tests

```bash
pytest --cov=app
```

## Project structure

```
app/
  main.py       API routes and scheduler
  schemas.py    Pydantic validation models
  etl.py        normalize → validate → load, with audit logging
  reports.py    Polars reporting job
  database.py   SQLAlchemy models (records, ingestion_runs)
scripts/        sample data generator and benchmark
tests/          14 unit and API tests
```

## Next steps

PostgreSQL in Docker Compose, duplicate detection across loads, and incremental loads from a live source API.
