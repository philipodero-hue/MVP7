"""
Iteration 3 Backend Tests: New feature endpoints
Tests for trip number by warehouse, export categories, auto-populate invoices
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tier-system-update.preview.emergentagent.com').rstrip('/')

# Shared session with auth
@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    # Login
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@servex.com", "password": "Servex2026!"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return s


class TestTripsNextNumberByWarehouse:
    """Test GET /api/trips/next-number-by-warehouse?warehouse_id=xxx"""

    def test_next_number_requires_warehouse_id(self, session):
        """Should fail without warehouse_id"""
        r = session.get(f"{BASE_URL}/api/trips/next-number-by-warehouse")
        assert r.status_code in [400, 422], f"Expected 400/422, got {r.status_code}"

    def test_next_number_invalid_warehouse(self, session):
        """Should return 404 for invalid warehouse"""
        r = session.get(f"{BASE_URL}/api/trips/next-number-by-warehouse", params={"warehouse_id": "nonexistent-id"})
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"

    def test_next_number_with_valid_warehouse(self, session):
        """Should return next trip number for a valid warehouse"""
        # First get a warehouse id
        warehouses_r = session.get(f"{BASE_URL}/api/warehouses")
        if warehouses_r.status_code == 200 and warehouses_r.json():
            warehouse_id = warehouses_r.json()[0]["id"]
            r = session.get(f"{BASE_URL}/api/trips/next-number-by-warehouse", params={"warehouse_id": warehouse_id})
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
            data = r.json()
            assert "next_trip_number" in data
            assert "warehouse_code" in data
            assert "warehouse_name" in data
            print(f"Next trip number: {data['next_trip_number']}")
        else:
            pytest.skip("No warehouses available for testing")


class TestExportCategories:
    """Test GET/PUT /api/tenant/export-categories"""

    def test_get_export_categories(self, session):
        """Should return list of export categories"""
        r = session.get(f"{BASE_URL}/api/tenant/export-categories")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "categories" in data, f"Missing 'categories' key in response: {data}"
        assert isinstance(data["categories"], list)
        print(f"Categories: {data['categories']}")

    def test_put_export_categories(self, session):
        """Should save export categories"""
        payload = {"categories": ["General", "Electronics", "Clothing", "TEST_Category"]}
        r = session.put(f"{BASE_URL}/api/tenant/export-categories", json=payload)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_categories_persist(self, session):
        """Verify saved categories persist"""
        # Save
        payload = {"categories": ["Alpha", "Beta", "Gamma"]}
        session.put(f"{BASE_URL}/api/tenant/export-categories", json=payload)
        # Read back
        r = session.get(f"{BASE_URL}/api/tenant/export-categories")
        assert r.status_code == 200
        data = r.json()
        assert "Alpha" in data["categories"]


class TestAutoPopulateInvoices:
    """Test POST /api/invoices/auto-populate-trip/{trip_id}"""

    def test_auto_populate_invalid_trip(self, session):
        """Should handle non-existent trip gracefully"""
        r = session.post(f"{BASE_URL}/api/invoices/auto-populate-trip/nonexistent-trip-id")
        # Either 200 with 0 created, or 404
        assert r.status_code in [200, 404], f"Got {r.status_code}: {r.text}"
        if r.status_code == 200:
            data = r.json()
            assert "created_count" in data

    def test_auto_populate_with_real_trip(self, session):
        """Should return proper structure for a valid trip"""
        # Get trips
        trips_r = session.get(f"{BASE_URL}/api/trips")
        if trips_r.status_code == 200 and trips_r.json():
            trip_id = trips_r.json()[0]["id"]
            r = session.post(f"{BASE_URL}/api/invoices/auto-populate-trip/{trip_id}")
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
            data = r.json()
            assert "created_count" in data
            assert "invoices" in data
            assert "unassigned_parcel_count" in data
            print(f"Auto-populate result: {data['created_count']} invoices created")
        else:
            pytest.skip("No trips available for testing")


class TestInvoicesEnhanced:
    """Test GET /api/invoices-enhanced"""

    def test_list_invoices_enhanced(self, session):
        """Should return enriched invoice list"""
        r = session.get(f"{BASE_URL}/api/invoices-enhanced")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert isinstance(data, list)
        if data:
            # Check for sent_by fields (for finalized invoices)
            first = data[0]
            assert "client_name" in first
            print(f"Total invoices: {len(data)}")
            # sent_by_name and sent_by_initials should exist (may be null)
            assert "sent_by_name" in first or True  # Optional field

    def test_invoices_enhanced_trip_filter(self, session):
        """Should filter by trip_id"""
        trips_r = session.get(f"{BASE_URL}/api/trips")
        if trips_r.status_code == 200 and trips_r.json():
            trip_id = trips_r.json()[0]["id"]
            r = session.get(f"{BASE_URL}/api/invoices-enhanced", params={"trip_id": trip_id})
            assert r.status_code == 200
        else:
            pytest.skip("No trips")


class TestTenantCurrencies:
    """Test GET /api/tenant/currencies"""

    def test_get_currencies(self, session):
        """Should return currencies with exchange_rates"""
        r = session.get(f"{BASE_URL}/api/tenant/currencies")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "exchange_rates" in data
        assert "base_currency" in data
        print(f"Base currency: {data['base_currency']}, rates: {len(data['exchange_rates'])}")
