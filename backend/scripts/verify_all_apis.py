import sys
import os

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    print("=" * 60)
    print("Starting Comprehensive API Verification Suite")
    print("=" * 60)

    # 1. Health Probe
    resp = client.get("/health")
    assert resp.status_code == 200, f"/health failed: {resp.text}"
    print("[PASS] Health Probe: 200 OK ->", resp.json())

    # 2. Doctor Login & Endpoints
    print("\n--- Testing Doctor Portal ---")
    doc_login = client.post("/api/auth/doctor/login", json={
        "email": "dr.kapoor@thapar.edu",
        "password": "doctor123"
    })
    assert doc_login.status_code == 200, f"Doctor login failed: {doc_login.text}"
    doc_data = doc_login.json()
    doc_token = doc_data.get("token") or doc_data.get("access_token")
    doc_id = doc_data.get("doctor_id") or doc_data.get("doctorId") or 1
    doc_headers = {"Authorization": f"Bearer {doc_token}"}
    print(f"[PASS] Doctor Login: 200 OK (doctor_id={doc_id})")

    # Doctor Profile
    r = client.get(f"/api/doctor/{doc_id}/profile", headers=doc_headers)
    assert r.status_code == 200, f"Doctor profile failed: {r.text}"
    print(f"[PASS] GET /api/doctor/{doc_id}/profile: 200 OK")

    # Doctor Queue
    r = client.get(f"/api/doctor/{doc_id}/queue", headers=doc_headers)
    assert r.status_code == 200, f"Doctor queue failed: {r.text}"
    print(f"[PASS] GET /api/doctor/{doc_id}/queue: 200 OK -> count={len(r.json())}")

    # Doctor Stats
    r = client.get(f"/api/doctor/{doc_id}/stats", headers=doc_headers)
    assert r.status_code == 200, f"Doctor stats failed: {r.text}"
    print(f"[PASS] GET /api/doctor/{doc_id}/stats: 200 OK ->", r.json())

    # Doctor Active Consultation
    r = client.get(f"/api/doctor/{doc_id}/active-consultation", headers=doc_headers)
    assert r.status_code == 200, f"Doctor active consultation failed: {r.text}"
    print(f"[PASS] GET /api/doctor/{doc_id}/active-consultation: 200 OK ->", r.json())

    # 3. Receptionist Login & Endpoints
    print("\n--- Testing Receptionist Portal ---")
    rec_login = client.post("/api/auth/receptionist/login", json={
        "email": "reception@thapar.edu",
        "password": "reception123"
    })
    assert rec_login.status_code == 200, f"Receptionist login failed: {rec_login.text}"
    rec_data = rec_login.json()
    rec_token = rec_data.get("token") or rec_data.get("access_token")
    rec_headers = {"Authorization": f"Bearer {rec_token}"}
    print("[PASS] Receptionist Login: 200 OK")

    # Reception Doctors
    r = client.get("/api/reception/doctors", headers=rec_headers)
    assert r.status_code == 200, f"Reception doctors failed: {r.text}"
    print(f"[PASS] GET /api/reception/doctors: 200 OK -> count={len(r.json())}")

    # Reception Queue
    r = client.get("/api/reception/queue", headers=rec_headers)
    assert r.status_code == 200, f"Reception queue failed: {r.text}"
    print(f"[PASS] GET /api/reception/queue: 200 OK -> count={len(r.json())}")

    # Reception Student Search
    r = client.get("/api/reception/students?query=1024030109", headers=rec_headers)
    assert r.status_code == 200, f"Reception student search failed: {r.text}"
    print(f"[PASS] GET /api/reception/students: 200 OK -> results={len(r.json())}")

    # 4. Student Login & Endpoints
    print("\n--- Testing Student Portal ---")
    stud_login = client.post("/api/auth/student/login", json={
        "identifier": "1024030109",
        "password": "student123"
    })
    assert stud_login.status_code == 200, f"Student login failed: {stud_login.text}"
    stud_data = stud_login.json()
    stud_token = stud_data.get("token") or stud_data.get("access_token")
    stud_headers = {"Authorization": f"Bearer {stud_token}"}
    print("[PASS] Student Login: 200 OK")

    # Student Me
    r = client.get("/api/student/me", headers=stud_headers)
    assert r.status_code == 200, f"Student me failed: {r.text}"
    profile = r.json()
    stud_ident = profile.get("student", {})
    print(f"[PASS] GET /api/student/me: 200 OK -> name={stud_ident.get('fullName')}, roll={stud_ident.get('rollNumber')}")

    # Student Update Profile (Testing ON DUPLICATE KEY UPDATE -> ON CONFLICT logic)
    update_payload = {
        "phoneNumber": "9876543210",
        "bloodGroup": "B+",
        "emergencyContact": {
            "name": "Emergency Guardian",
            "relationship": "Parent",
            "phoneNumber": "9876543211",
            "alternativePhoneNumber": ""
        },
        "hasAllergies": True,
        "allergies": [
            {"allergen": "Penicillin", "severity": "SEVERE", "reaction": "Hives"}
        ],
        "hasChronicConditions": False,
        "chronicConditions": [],
        "hasMedications": False,
        "medications": []
    }
    r = client.put("/api/student/me", json=update_payload, headers=stud_headers)
    assert r.status_code == 200, f"Student update profile failed: {r.text}"
    print("[PASS] PUT /api/student/me: 200 OK -> profile saved cleanly without SQL syntax errors!")

    # Verify updated profile
    r = client.get("/api/student/me", headers=stud_headers)
    assert r.status_code == 200
    updated_profile = r.json()
    updated_stud = updated_profile.get("student", {})
    assert updated_stud.get("bloodGroup") == "B+", f"Expected B+, got {updated_stud.get('bloodGroup')}"
    completion = updated_profile.get("profileCompletion", {})
    print(f"[PASS] Re-fetch /api/student/me confirmed bloodGroup='B+', completeness={completion.get('percentage')}% ({completion.get('status')})")

    # 5. Admin Login & Endpoints
    print("\n--- Testing Admin Portal ---")
    admin_login = client.post("/api/auth/admin/login", json={
        "email": "admin@thapar.edu",
        "password": "admin123"
    })
    assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
    admin_data = admin_login.json()
    admin_token = admin_data.get("token") or admin_data.get("access_token")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("[PASS] Admin Login: 200 OK")

    print("\n" + "=" * 60)
    print("ALL 14 API SUITE TESTS PASSED WITH ZERO ERRORS!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
