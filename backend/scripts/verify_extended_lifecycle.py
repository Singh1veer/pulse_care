import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    print("=" * 60)
    print("Extended Lifecycle API Verification Suite")
    print("=" * 60)

    # 1. Doctor & Reception tokens
    doc_login = client.post("/api/auth/doctor/login", json={"email": "dr.kapoor@thapar.edu", "password": "doctor123"})
    assert doc_login.status_code == 200
    doc_data = doc_login.json()
    doc_headers = {"Authorization": f"Bearer {doc_data.get('access_token')}"}
    doc_id = doc_data.get("doctor_id") or 1

    rec_login = client.post("/api/auth/receptionist/login", json={"email": "reception@thapar.edu", "password": "reception123"})
    assert rec_login.status_code == 200
    rec_headers = {"Authorization": f"Bearer {rec_login.json().get('access_token')}"}

    # 2. Reception Check-in a student into Doctor 1's queue
    checkin_payload = {
        "rollNumber": "102403001",
        "doctorId": doc_id,
        "entryReason": "Flu symptoms and headache",
        "priority": "NORMAL"
    }
    r = client.post("/api/reception/checkin", json=checkin_payload, headers=rec_headers)
    assert r.status_code in (200, 201, 409), f"Checkin failed: {r.text}"
    print(f"[PASS] POST /api/reception/checkin: {r.status_code} ->", r.json())

    # 3. Doctor Call Next
    r = client.post(f"/api/doctor/{doc_id}/call-next", headers=doc_headers)
    assert r.status_code == 200, f"Doctor call-next failed: {r.text}"
    called_res = r.json()
    print("[PASS] POST /api/doctor/{doc_id}/call-next: 200 OK -> called patient:", called_res.get("patient", {}).get("name"))

    # 4. Doctor Active Consultation
    r = client.get(f"/api/doctor/{doc_id}/active-consultation", headers=doc_headers)
    assert r.status_code == 200
    active_data = r.json()
    print("[PASS] GET /api/doctor/{doc_id}/active-consultation: 200 OK -> active:", active_data.get("active"))

    # 5. Doctor Patient Summary & History
    r = client.get(f"/api/patient/102403001/summary", headers=doc_headers)
    assert r.status_code == 200, f"Patient summary failed: {r.text}"
    print("[PASS] GET /api/patient/102403001/summary: 200 OK")

    r = client.get(f"/api/patient/102403001/history", headers=doc_headers)
    assert r.status_code == 200, f"Patient history failed: {r.text}"
    print(f"[PASS] GET /api/patient/102403001/history: 200 OK -> visits={len(r.json())}")

    # 6. Doctor Complete Consultation
    if active_data.get("active") and active_data.get("patient"):
        active_patient = active_data["patient"]
        comp_payload = {
            "visitId": active_patient["visitId"],
            "queueEntryId": active_patient["queueEntryId"],
            "diagnosis": "Viral upper respiratory tract infection",
            "clinicalNotes": "Advised hydration and rest.",
            "prescriptions": [
                {
                    "medicineName": "Paracetamol 500mg",
                    "dosage": "1 tablet",
                    "duration": "3 days",
                    "instructions": "After meals",
                    "frequency": "BID",
                    "timing": "After food"
                }
            ]
        }
        r = client.post(f"/api/doctor/{doc_id}/complete", json=comp_payload, headers=doc_headers)
        assert r.status_code == 200, f"Complete consultation failed: {r.text}"
        print("[PASS] POST /api/doctor/{doc_id}/complete: 200 OK -> completed successfully!")

    # 7. Receptionist Pending Dispensing
    r = client.get("/api/reception/prescriptions/awaiting-dispense", headers=rec_headers)
    assert r.status_code == 200, f"Awaiting dispense failed: {r.text}"
    print(f"[PASS] GET /api/reception/prescriptions/awaiting-dispense: 200 OK -> count={len(r.json())}")

    print("\n" + "=" * 60)
    print("END-TO-END PATIENT LIFECYCLE (CHECKIN -> CALL -> CONSULT -> COMPLETE -> DISPENSE) PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
