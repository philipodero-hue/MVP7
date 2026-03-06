"""Backend tests for Session Q, R, T features"""
import pytest
import requests
import os

BASE_URL = "https://tier-system-update.preview.emergentagent.com"

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    # Login
    resp = s.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@servex.com", "password": "Servex2026!"})
    if resp.status_code != 200:
        pytest.skip(f"Auth failed: {resp.status_code} {resp.text}")
    return s


class TestBarcodeFormat:
    """SESSION Q: 8-digit barcode format"""

    def test_barcode_service_generates_8digit(self, session):
        # Create a parcel to verify barcode format
        # First get clients
        clients_resp = session.get(f"{BASE_URL}/api/clients")
        assert clients_resp.status_code == 200
        clients = clients_resp.json()
        assert len(clients) > 0, "No clients found"
        client_id = clients[0]['id']

        # Create a shipment/parcel
        resp = session.post(f"{BASE_URL}/api/shipments", json={
            "client_id": client_id,
            "recipient_name": "TEST_BarcodeTester",
            "pieces": 1,
            "weight": 1.0,
            "description": "Test barcode"
        })
        assert resp.status_code in [200, 201]
        data = resp.json()
        barcode = data.get('barcode', '')
        print(f"Generated barcode: {barcode}")
        # Verify format: SX + 8 digits = 10 chars
        assert barcode.startswith('SX'), f"Barcode should start with SX, got: {barcode}"
        assert len(barcode) == 10, f"Barcode should be 10 chars (SX + 8 digits), got: {barcode} (len={len(barcode)})"
        digits = barcode[2:]
        assert digits.isdigit(), f"Barcode digits part should be numeric, got: {digits}"


class TestPaymentRecording:
    """SESSION T: Payment recording endpoint"""

    def test_record_payment_endpoint_exists(self, session):
        # Get an invoice to test with
        resp = session.get(f"{BASE_URL}/api/invoices/search?status=finalized&limit=1")
        if resp.status_code != 200:
            pytest.skip("Could not get invoices")
        data = resp.json()
        invoices = data if isinstance(data, list) else data.get('invoices', [])
        if not invoices:
            pytest.skip("No finalized invoices to test payment recording")
        invoice_id = invoices[0]['id']

        # Test record-payment endpoint
        payment_resp = session.post(f"{BASE_URL}/api/invoices/{invoice_id}/record-payment", json={
            "amount": 10.00,
            "payment_date": "2026-02-01",
            "payment_method": "cash",
            "notes": "TEST payment"
        })
        print(f"Record payment status: {payment_resp.status_code}, response: {payment_resp.text[:200]}")
        assert payment_resp.status_code in [200, 201, 400], f"Unexpected status: {payment_resp.status_code}"


class TestSystemExport:
    """SESSION R: System export endpoint"""

    def test_system_export_endpoint(self, session):
        resp = session.get(f"{BASE_URL}/api/data/system-export")
        print(f"System export status: {resp.status_code}, content-type: {resp.headers.get('content-type','')}")
        assert resp.status_code == 200
        content_type = resp.headers.get('content-type', '')
        assert 'zip' in content_type or 'octet' in content_type or len(resp.content) > 0


class TestEmailAlerts:
    """SESSION R: Email alerts settings endpoints"""

    def test_get_email_alerts(self, session):
        resp = session.get(f"{BASE_URL}/api/settings/email-alerts")
        print(f"Email alerts GET: {resp.status_code}, {resp.text[:200]}")
        assert resp.status_code == 200

    def test_update_email_alerts(self, session):
        resp = session.put(f"{BASE_URL}/api/settings/email-alerts", json={
            "enabled": False,
            "alert_hours": 4
        })
        print(f"Email alerts PUT: {resp.status_code}, {resp.text[:200]}")
        assert resp.status_code in [200, 201]


class TestWarehouseNoTrip:
    """SESSION T: Warehouse no-trip destination"""

    def test_warehouse_parcels_api(self, session):
        resp = session.get(f"{BASE_URL}/api/warehouse/parcels?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        parcels = data if isinstance(data, list) else data.get('parcels', data.get('items', []))
        print(f"Got {len(parcels)} parcels from warehouse")
        # Check parcels without trip_id
        no_trip = [p for p in parcels if not p.get('trip_id')]
        print(f"Parcels without trip: {len(no_trip)}")
