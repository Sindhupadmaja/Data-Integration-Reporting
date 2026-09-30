import os
import tempfile

# Use a throwaway database and report folder for every test run.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["REPORT_DIR"] = f"{_tmp}/reports"
os.environ["DISABLE_SCHEDULER"] = "1"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:  # runs startup, which creates tables
        yield c
