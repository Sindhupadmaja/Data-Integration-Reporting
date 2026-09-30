import json

from app.etl import normalize
from app.schemas import SalesRecord

CSV_OK = b"customer_name,value,area,date\nAlice,10.5,east,2026-01-05\nBob,20,west,2026-01-06\n"


def post_csv(client, content, name="sales.csv"):
    return client.post("/ingest/csv", files={"file": (name, content, "text/csv")})


# ---------- unit tests: normalization and validation ----------

def test_normalize_maps_aliases_to_canonical_names():
    out = normalize({"Client": "Acme", "Total": "5", "Territory": "north", "txn_date": "2026-02-01"})
    assert out == {"customer": "Acme", "amount": "5", "region": "north", "order_date": "2026-02-01"}


def test_schema_cleans_currency_and_commas():
    rec = SalesRecord(customer=" Acme ", amount="$1,200.50", region="east", order_date="2026-03-01")
    assert rec.customer == "Acme" and rec.amount == 1200.50 and rec.region == "EAST"


def test_schema_accepts_multiple_date_formats():
    for d in ["2026-03-01", "01/03/2026", "03-01-2026", "2026/03/01"]:
        assert SalesRecord(customer="A", amount=1, order_date=d).order_date.isoformat() == "2026-03-01"


def test_schema_defaults_missing_region():
    assert SalesRecord(customer="A", amount=1, order_date="2026-01-01").region == "UNKNOWN"


# ---------- API tests: ingestion from each source ----------

def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_csv_ingest_valid_rows(client):
    r = post_csv(client, CSV_OK)
    assert r.status_code == 200
    body = r.json()
    assert body["inserted"] == 2 and body["rejected"] == 0 and body["source_type"] == "csv"


def test_csv_rejects_invalid_rows_with_reasons(client):
    bad = (b"customer,amount,order_date\n"
           b",10,2026-01-01\n"          # missing customer
           b"Carl,-5,2026-01-01\n"      # negative amount
           b"Dana,abc,2026-01-01\n"     # non-numeric amount
           b"Eve,10,not-a-date\n"       # bad date
           b"Finn,10,2026-01-01\n")     # valid
    body = post_csv(client, bad).json()
    assert body["received"] == 5 and body["inserted"] == 1 and body["rejected"] == 4
    reasons = " ".join(r["reason"] for r in body["sample_rejections"])
    assert "customer" in reasons and "amount" in reasons and "order_date" in reasons


def test_json_file_ingest(client):
    data = [{"client": "Gina", "total": 30, "region": "east", "transaction_date": "2026-01-07"}]
    r = client.post("/ingest/json-file",
                    files={"file": ("crm.json", json.dumps(data).encode(), "application/json")})
    assert r.status_code == 200 and r.json()["inserted"] == 1


def test_json_file_rejects_malformed_json(client):
    r = client.post("/ingest/json-file", files={"file": ("bad.json", b"{not json", "application/json")})
    assert r.status_code == 400


def test_api_push_ingest(client):
    r = client.post("/ingest/api?source=billing",
                    json=[{"customer": "Hal", "amount": 40, "order_date": "2026-01-08"}])
    assert r.status_code == 200 and r.json()["source"] == "billing"


# ---------- analytics, audit log and reports ----------

def test_analytics_combine_all_sources(client):
    post_csv(client, CSV_OK)
    client.post("/ingest/api", json=[{"customer": "Alice", "amount": 4.5, "region": "east",
                                      "order_date": "2026-01-09"}])
    summary = client.get("/analytics/summary").json()
    assert summary["record_count"] == 3 and summary["total_amount"] == 35.0
    top = client.get("/analytics/by-customer").json()[0]
    assert top == {"customer": "Bob", "total": 20.0}
    regions = {r["region"]: r["total"] for r in client.get("/analytics/by-region").json()}
    assert regions == {"EAST": 15.0, "WEST": 20.0}


def test_ingestion_runs_are_audited(client):
    post_csv(client, CSV_OK)
    runs = client.get("/ingestion/runs").json()
    assert len(runs) == 1 and runs[0]["inserted"] == 2 and runs[0]["source"] == "sales.csv"


def test_report_generates_csv_file(client):
    post_csv(client, CSV_OK)
    report = client.post("/reports/run").json()
    assert report["record_count"] == 2 and report["file"].endswith(".csv")
    assert {r["region"] for r in report["by_region"]} == {"EAST", "WEST"}


def test_report_handles_empty_database(client):
    assert client.post("/reports/run").json()["record_count"] == 0
