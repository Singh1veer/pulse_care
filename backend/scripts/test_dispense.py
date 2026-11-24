import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_dispensing():
    print("Testing Dispensing Endpoint...")
    
    # 1. Login receptionist
    rec_login = client.post("/api/auth/receptionist/login", json={"email": "reception@thapar.edu", "password": "reception123"})
    assert rec_login.status_code == 200
    rec_token = rec_login.json().get("access_token")
    rec_headers = {"Authorization": f"Bearer {rec_token}"}
    
    # 2. Get awaiting dispense list
    r = client.get("/api/reception/prescriptions/awaiting-dispense", headers=rec_headers)
    assert r.status_code == 200
    awaiting = r.json()
    print(f"Found {len(awaiting)} visits awaiting dispense:")
    for v in awaiting:
        print(f"  - Visit #{v.get('visitId') or v.get('visit_id')} for {v.get('name')}")

    target_visit_id = None
    if awaiting:
        target_visit_id = awaiting[0].get("visitId") or awaiting[0].get("visit_id")
    else:
        # Check if Visit 8 exists
        target_visit_id = 8

    print(f"Dispensing visit #{target_visit_id}...")
    dispense_payload = {
        "remarks": "Verified student roll number and dispensed prescribed medication",
        "status": "FULL"
    }
    r = client.post(f"/api/reception/dispense/{target_visit_id}", json=dispense_payload, headers=rec_headers)
    print(f"Response status: {r.status_code}")
    print(f"Response body: {r.text}")
    assert r.status_code in (200, 201), f"Dispensing failed: {r.text}"
    print("[SUCCESS] Medication successfully dispensed!")

if __name__ == "__main__":
    test_dispensing()
