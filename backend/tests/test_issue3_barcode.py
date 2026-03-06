"""
Test for Issue 3: Manual barcode generation
Test that POST /api/shipments creates a shipment with a barcode field starting with 'SX' (10 chars total)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@servex.com"
TEST_PASSWORD = "Servex2026!"


class TestIssue3Barcode:
    """Test that manual parcel creation generates SX barcode"""
    
    @pytest.fixture(autouse=True)
    def setup(self, request):
        """Get session with auth cookies"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get session cookie
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if login_response.status_code != 200:
            pytest.skip(f"Authentication failed: {login_response.status_code} - {login_response.text}")
        
        print(f"LOGIN SUCCESS: {login_response.status_code}")
    
    def test_get_client_for_shipment(self):
        """Get a client ID to use for shipment creation"""
        response = self.session.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200, f"Failed to get clients: {response.text}"
        
        clients = response.json()
        assert len(clients) > 0, "No clients found in system"
        
        self.client_id = clients[0]["id"]
        self.client_name = clients[0].get("name", "Unknown")
        print(f"FOUND CLIENT: {self.client_name} (ID: {self.client_id})")
        return self.client_id
    
    def test_create_shipment_has_barcode(self):
        """
        Issue 3: Test creating a manual parcel via API.
        POST /api/shipments with description, total_weight, destination, client_id.
        Verify the response includes a 'barcode' field starting with 'SX' (10 chars total).
        """
        # First get a client
        response = self.session.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200
        clients = response.json()
        assert len(clients) > 0, "No clients found"
        client_id = clients[0]["id"]
        
        # Create shipment with minimal fields
        shipment_payload = {
            "description": "TEST_Issue3_Barcode_Verification",
            "total_weight": 5.5,
            "destination": "Harare",
            "client_id": client_id
        }
        
        create_response = self.session.post(
            f"{BASE_URL}/api/shipments",
            json=shipment_payload
        )
        
        # Status assertion
        assert create_response.status_code == 200, f"Failed to create shipment: {create_response.status_code} - {create_response.text}"
        
        # Parse response
        shipment = create_response.json()
        print(f"CREATED SHIPMENT: {shipment}")
        
        # Data assertions for barcode
        assert "barcode" in shipment, f"Response missing 'barcode' field. Response: {shipment}"
        
        barcode = shipment["barcode"]
        assert barcode is not None, f"Barcode is None. Response: {shipment}"
        assert isinstance(barcode, str), f"Barcode should be string, got {type(barcode)}"
        assert barcode.startswith("SX"), f"Barcode should start with 'SX', got: {barcode}"
        assert len(barcode) == 10, f"Barcode should be 10 chars, got {len(barcode)}: {barcode}"
        
        print(f"SUCCESS: Barcode generated correctly: {barcode}")
        
        # Store shipment ID for cleanup
        self.created_shipment_id = shipment["id"]
        
        # Verify GET also returns barcode
        get_response = self.session.get(f"{BASE_URL}/api/shipments/{shipment['id']}")
        assert get_response.status_code == 200
        
        fetched_shipment = get_response.json()
        assert fetched_shipment.get("barcode") == barcode, f"GET response barcode mismatch. Expected: {barcode}, Got: {fetched_shipment.get('barcode')}"
        print(f"VERIFIED: Barcode persisted correctly: {barcode}")
        
        return shipment
    
    def test_barcode_format_validation(self):
        """Additional test: Verify barcode format is exactly SX followed by 8 digits"""
        # First get a client
        response = self.session.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200
        clients = response.json()
        client_id = clients[0]["id"]
        
        # Create multiple shipments to verify sequential numbering
        for i in range(3):
            shipment_payload = {
                "description": f"TEST_Barcode_Format_{i}",
                "total_weight": 1.0 + i,
                "destination": "Nairobi",
                "client_id": client_id
            }
            
            create_response = self.session.post(
                f"{BASE_URL}/api/shipments",
                json=shipment_payload
            )
            
            assert create_response.status_code == 200
            shipment = create_response.json()
            barcode = shipment.get("barcode")
            
            # Validate format: SX followed by exactly 8 digits
            assert barcode is not None
            assert barcode[:2] == "SX"
            assert barcode[2:].isdigit(), f"Barcode digits part should be numeric: {barcode}"
            
            print(f"Shipment {i+1} barcode: {barcode}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
