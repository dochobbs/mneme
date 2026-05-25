"""Backend smoke tests for Mneme EMR (W2.5).

These tests exercise the API surface without touching real Supabase.
Supabase is mocked at the `SupabaseDB` and `get_supabase()` level.

Run from backend/ with:
  .venv/bin/python -m pytest tests/ -v
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure env vars exist BEFORE importing src.* (pydantic Settings requires them)
os.environ.setdefault("SUPABASE_URL", "http://test.supabase.local")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")

# Make `src.*` importable when tests run from anywhere
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
  sys.path.insert(0, str(BACKEND_ROOT))

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.db.helpers import first_or_500  # noqa: E402
from src.main import app  # noqa: E402


# --- Helpers ---

class FakeResponse:
  """Mimics the shape returned by supabase-py: an object with `.data`."""

  def __init__(self, data):
    self.data = data


def make_chainable_supabase(execute_data):
  """Build a MagicMock that supports the chain `.table(...).select(...).eq(...).execute()`.

  Any chained attribute access or call returns the same mock; only
  `.execute()` returns a FakeResponse with the supplied data.
  """
  chain = MagicMock()
  chain.execute.return_value = FakeResponse(execute_data)

  table_mock = MagicMock()
  # Every chained call returns `chain` so .select().eq().single() etc. all work
  for method in ("select", "insert", "update", "delete", "eq", "single",
                 "order", "limit", "range", "gte", "lte"):
    setattr(chain, method, MagicMock(return_value=chain))
    setattr(table_mock, method, MagicMock(return_value=chain))

  client = MagicMock()
  client.table.return_value = table_mock
  # also allow client.table(...).select(...) to chain
  table_mock.select.return_value = chain
  return client


@pytest.fixture
def client():
  """FastAPI TestClient with no startup/shutdown side effects required."""
  return TestClient(app)


# --- /health ---

def test_health_endpoint_returns_200(client):
  resp = client.get("/health")
  assert resp.status_code == 200
  assert resp.json() == {"status": "healthy"}


def test_root_endpoint_returns_200(client):
  resp = client.get("/")
  assert resp.status_code == 200
  body = resp.json()
  assert body["name"] == "Mneme EMR"
  assert body["status"] == "running"


# --- Auth: signup + login (paths are /auth/signup and /auth/login) ---

def test_auth_signup_happy_path(client):
  """POST /auth/signup with mocked Supabase auth returns 200 + tokens."""
  fake_user = MagicMock(id="user-123", email="new@example.com")
  fake_session = MagicMock(
    access_token="access-tok", refresh_token="refresh-tok"
  )
  fake_auth_response = MagicMock(user=fake_user, session=fake_session)

  fake_supabase = MagicMock()
  fake_supabase.auth.sign_up.return_value = fake_auth_response

  fake_admin = MagicMock()
  fake_admin.table.return_value.update.return_value.eq.return_value.execute.return_value = FakeResponse([])

  with patch("src.routers.auth.get_supabase", return_value=fake_supabase), \
       patch("src.routers.auth.get_supabase_admin", return_value=fake_admin):
    resp = client.post(
      "/auth/signup",
      json={
        "email": "new@example.com",
        "password": "supersecret123",
        "display_name": "Test User",
        "role": "student",
      },
    )

  assert resp.status_code == 200, resp.text
  body = resp.json()
  assert body["access_token"] == "access-tok"
  assert body["refresh_token"] == "refresh-tok"
  assert body["user"]["email"] == "new@example.com"


def test_auth_login_happy_path(client):
  """POST /auth/login with mocked Supabase auth returns 200 + tokens."""
  fake_user = MagicMock(id="user-456", email="existing@example.com")
  fake_session = MagicMock(
    access_token="login-access", refresh_token="login-refresh"
  )
  fake_auth_response = MagicMock(user=fake_user, session=fake_session)

  fake_supabase = MagicMock()
  fake_supabase.auth.sign_in_with_password.return_value = fake_auth_response
  # learner profile lookup
  fake_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = FakeResponse(
    {"display_name": "Existing", "role": "resident"}
  )

  with patch("src.routers.auth.get_supabase", return_value=fake_supabase):
    resp = client.post(
      "/auth/login",
      json={
        "email": "existing@example.com",
        "password": "supersecret123",
      },
    )

  assert resp.status_code == 200, resp.text
  body = resp.json()
  assert body["access_token"] == "login-access"
  assert body["user"]["role"] == "resident"
  assert body["user"]["display_name"] == "Existing"


def test_auth_login_invalid_credentials_returns_401(client):
  """Login with bad credentials surfaces as 401."""
  fake_supabase = MagicMock()
  # Supabase returns no user/session for bad creds
  fake_supabase.auth.sign_in_with_password.return_value = MagicMock(
    user=None, session=None
  )

  with patch("src.routers.auth.get_supabase", return_value=fake_supabase):
    resp = client.post(
      "/auth/login",
      json={"email": "x@example.com", "password": "wrong"},
    )

  assert resp.status_code == 401


# --- Patients (auth-gated) ---

def test_patients_without_auth_returns_401(client):
  """GET /api/patients without Authorization header must return 401."""
  resp = client.get("/api/patients")
  assert resp.status_code == 401
  assert "authenticated" in resp.json()["detail"].lower()


# --- Import: /api/import/oread/json ---

MINIMAL_OREAD_PAYLOAD = {
  "demographics": {
    "given_names": ["Test"],
    "family_name": "Patient",
    "date_of_birth": "2020-01-01",
    "sex_at_birth": "male",
  },
  "problem_list": [],
  "medication_list": [],
  "allergy_list": [],
  "encounters": [],
  "observations": [],
  "immunization_record": [],
  "patient_messages": [],
  "growth_data": [],
}


def test_import_oread_json_happy_path(client):
  """POST /api/import/oread/json with mocked DB returns success."""
  fake_db = MagicMock()
  fake_db.create_import_record.return_value = FakeResponse(
    [{"id": "import-123"}]
  )
  # Importer needs to succeed without touching real DB
  fake_importer_result = {
    "success": True,
    "patient_id": "patient-abc",
    "counts": {"conditions": 0, "medications": 0},
    "errors": [],
  }

  with patch("src.routers.import_.SupabaseDB", return_value=fake_db), \
       patch("src.routers.import_.OreadImporter") as MockImporter:
    MockImporter.return_value.import_patient.return_value = fake_importer_result
    resp = client.post(
      "/api/import/oread/json",
      json=MINIMAL_OREAD_PAYLOAD,
    )

  assert resp.status_code == 200, resp.text
  body = resp.json()
  assert body["success"] is True
  assert body["import_id"] == "import-123"
  assert body["details"]["patient_id"] == "patient-abc"


def test_import_oread_json_empty_db_response_returns_500(client):
  """When create_import_record returns empty data, first_or_500 should 500."""
  fake_db = MagicMock()
  fake_db.create_import_record.return_value = FakeResponse([])  # empty -> 500

  with patch("src.routers.import_.SupabaseDB", return_value=fake_db):
    resp = client.post(
      "/api/import/oread/json",
      json=MINIMAL_OREAD_PAYLOAD,
    )

  assert resp.status_code == 500
  assert "import record" in resp.json()["detail"].lower()


# --- first_or_500 unit tests ---

def test_first_or_500_returns_first_row_on_populated_data():
  result = FakeResponse([{"id": "a"}, {"id": "b"}])
  assert first_or_500(result, "thing") == {"id": "a"}


def test_first_or_500_raises_500_on_empty_data():
  result = FakeResponse([])
  with pytest.raises(HTTPException) as exc_info:
    first_or_500(result, "widget")
  assert exc_info.value.status_code == 500
  assert "widget" in exc_info.value.detail


def test_first_or_500_raises_500_on_none_data():
  result = FakeResponse(None)
  with pytest.raises(HTTPException) as exc_info:
    first_or_500(result, "gadget")
  assert exc_info.value.status_code == 500
  assert "gadget" in exc_info.value.detail
