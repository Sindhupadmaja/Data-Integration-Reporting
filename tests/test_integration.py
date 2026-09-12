from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)
def test_ingest():
 csv=b'customer_name,value\nAlice,10.5\nBob,20'
 r=c.post('/ingest/csv',files={'file':('sales.csv',csv)}); assert r.status_code==200 and r.json()['inserted']>=2
def test_summary(): assert c.get('/analytics/summary').status_code==200
