import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Test 1: Faculty login with employee ID 260112
resp1 = client.post("/api/auth/faculty/login", json={"email": "260112", "password": "password123"})
print("Login with 260112:", resp1.status_code, resp1.json().get("name"), resp1.json().get("employee_code"))
assert resp1.status_code == 200, f"Expected 200, got {resp1.status_code}: {resp1.text}"

# Test 2: Faculty login with email dr.sharma@thapar.edu
resp2 = client.post("/api/auth/faculty/login", json={"email": "dr.sharma@thapar.edu", "password": "password123"})
print("Login with email:", resp2.status_code, resp2.json().get("name"), resp2.json().get("employee_code"))
assert resp2.status_code == 200, f"Expected 200, got {resp2.status_code}: {resp2.text}"

# Test 3: Faculty /me endpoint
fac_token = resp2.json()["access_token"]
resp_me = client.get("/api/faculty/me", headers={"Authorization": f"Bearer {fac_token}"})
print("Faculty /me status:", resp_me.status_code, "data:", resp_me.json().get("data", {}).get("employee_code"))
assert resp_me.status_code == 200

# Test 4: Receptionist login and lookup identifier 260112
resp_rec = client.post("/api/auth/receptionist/login", json={"email": "reception@thapar.edu", "password": "reception123"})
if resp_rec.status_code != 200:
    resp_rec = client.post("/api/auth/login", json={"email": "reception@thapar.edu", "password": "reception123"})
rec_token = resp_rec.json()["access_token"]

resp_lookup = client.get("/api/reception/lookup-identifier/260112", headers={"Authorization": f"Bearer {rec_token}"})
print("Lookup 260112 status:", resp_lookup.status_code, "type:", resp_lookup.json().get("type"))
assert resp_lookup.status_code == 200

# Test 5: Direct other check-in
resp_checkin = client.post(
    "/api/reception/other/checkin",
    json={
        "full_name": "Ramesh",
        "category": "CARETAKER",
        "department": "hostel",
        "age": 31,
        "gender": "Male",
        "doctor_id": 1,
        "complaint": "Acute headache",
    },
    headers={"Authorization": f"Bearer {rec_token}"},
)
print("Direct other checkin status:", resp_checkin.status_code, "visitId:", resp_checkin.json().get("visitId"))
assert resp_checkin.status_code == 201

print("\n>>> ALL TESTS PASSED SUCCESSFULLY! <<<")
