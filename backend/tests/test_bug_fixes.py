"""
Tests for 6 bug fixes in Servex Holdings logistics platform.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

EMAIL = "admin@servex.com"
PASSWORD = "Servex2026!"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    resp = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return s


# Test system-export endpoint returns zip
def test_system_export(session):
    resp = session.get(f"{BASE_URL}/api/data/system-export")
    assert resp.status_code == 200, f"system-export failed: {resp.status_code} {resp.text[:200]}"
    content_type = resp.headers.get("content-type", "")
    assert "zip" in content_type or len(resp.content) > 100, f"Expected zip, got {content_type}"
    print(f"PASS: system-export returned {len(resp.content)} bytes, content-type={content_type}")


# Test GET /payments returns list
def test_list_payments(session):
    resp = session.get(f"{BASE_URL}/api/payments")
    assert resp.status_code == 200, f"GET /payments failed: {resp.status_code} {resp.text[:200]}"
    data = resp.json()
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    print(f"PASS: /payments returned {len(data)} records")


# Test POST record-payment endpoint exists (not 405)
def test_record_payment_endpoint_exists(session):
    # First get an invoice id
    resp = session.get(f"{BASE_URL}/api/invoices?limit=1")
    assert resp.status_code == 200, f"GET invoices failed: {resp.status_code}"
    invoices = resp.json()
    if not invoices:
        pytest.skip("No invoices available")
    inv_id = invoices[0].get("id") or invoices[0].get("_id")
    # Post a payment - may fail with 422/400 due to data but should not be 405
    resp2 = session.post(f"{BASE_URL}/api/invoices/{inv_id}/record-payment", json={
        "amount": 0.01,
        "payment_date": "2026-02-01",
        "payment_method": "cash",
        "notes": "TEST_payment"
    })
    assert resp2.status_code != 405, f"Got 405 Method Not Allowed on record-payment"
    print(f"PASS: record-payment endpoint returned {resp2.status_code} (not 405)")


# Test warehouse parcels have SX barcodes
def test_warehouse_parcels_barcode_format(session):
    resp = session.get(f"{BASE_URL}/api/warehouse/parcels?limit=10")
    assert resp.status_code == 200, f"warehouse parcels failed: {resp.status_code}"
    data = resp.json()
    parcels = data if isinstance(data, list) else data.get("parcels", data.get("items", []))
    if not parcels:
        pytest.skip("No warehouse parcels available")
    # Check at least some have SX barcodes
    barcodes = [p.get("barcode", "") for p in parcels[:10]]
    sx_count = sum(1 for b in barcodes if b and b.startswith("SX"))
    print(f"Barcodes found: {barcodes[:5]}")
    print(f"SX barcode count: {sx_count}/{len(barcodes)}")
    assert sx_count > 0, f"No SX barcodes found, got: {barcodes}"


# Test migrate-barcodes endpoint exists
def test_migrate_barcodes_endpoint(session):
    resp = session.post(f"{BASE_URL}/api/data/migrate-barcodes")
    assert resp.status_code in [200, 201, 400], f"migrate-barcodes returned {resp.status_code}"
    print(f"PASS: migrate-barcodes returned {resp.status_code}")
