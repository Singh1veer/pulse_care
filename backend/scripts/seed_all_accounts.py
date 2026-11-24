"""
Seeds all roles and test accounts required for development and testing.
"""
import os
import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.core.database import get_db_connection
from app.core.security import hash_password


def seed_all():
    print("Seeding all development accounts...")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 1. SPECIALTY
            cur.execute("SELECT specialty_id FROM SPECIALTY WHERE name = %s", ("General Physician",))
            row = cur.fetchone()
            if row:
                spec_id = row["specialty_id"]
            else:
                cur.execute("INSERT INTO SPECIALTY (name, description, is_active) VALUES (%s, %s, 1)", ("General Physician", "Primary Care"))
                spec_id = cur.lastrowid

            # 2. DOCTORS
            doctors = [
                ("dr.kapoor@thapar.edu", "doctor123", "Dr. Neha Kapoor", "DOC-THP-001"),
                ("neha.kapoor@campuscare.edu", "doctor123", "Dr. Neha Kapoor", "DOC-CC-002"),
            ]
            for email, pwd, name, lic in doctors:
                cur.execute("SELECT user_id FROM USER_ACCOUNT WHERE email = %s", (email,))
                u = cur.fetchone()
                if not u:
                    cur.execute(
                        "INSERT INTO USER_ACCOUNT (email, password_hash, account_type, status) VALUES (%s, %s, 'STAFF', 'ACTIVE')",
                        (email, hash_password(pwd)),
                    )
                    uid = cur.lastrowid
                else:
                    uid = u["user_id"]
                    cur.execute("UPDATE USER_ACCOUNT SET password_hash = %s, status = 'ACTIVE' WHERE user_id = %s", (hash_password(pwd), uid))

                cur.execute("SELECT staff_id FROM STAFF WHERE user_id = %s", (uid,))
                s = cur.fetchone()
                if not s:
                    cur.execute("INSERT INTO STAFF (user_id, role, status) VALUES (%s, 'DOCTOR', 'ACTIVE')", (uid,))
                    staff_id = cur.lastrowid
                else:
                    staff_id = s["staff_id"]
                    cur.execute("UPDATE STAFF SET role = 'DOCTOR', status = 'ACTIVE' WHERE staff_id = %s", (staff_id,))

                cur.execute("SELECT doctor_id FROM DOCTOR WHERE staff_id = %s", (staff_id,))
                d = cur.fetchone()
                if not d:
                    cur.execute("INSERT INTO DOCTOR (staff_id, specialty_id, license_number) VALUES (%s, %s, %s)", (staff_id, spec_id, lic))

            # 3. RECEPTIONISTS
            receptionists = [
                ("reception@thapar.edu", "reception123"),
                ("receptionist@thapar.edu", "reception123"),
            ]
            for email, pwd in receptionists:
                cur.execute("SELECT user_id FROM USER_ACCOUNT WHERE email = %s", (email,))
                u = cur.fetchone()
                if not u:
                    cur.execute(
                        "INSERT INTO USER_ACCOUNT (email, password_hash, account_type, status) VALUES (%s, %s, 'STAFF', 'ACTIVE')",
                        (email, hash_password(pwd)),
                    )
                    uid = cur.lastrowid
                else:
                    uid = u["user_id"]
                    cur.execute("UPDATE USER_ACCOUNT SET password_hash = %s, status = 'ACTIVE' WHERE user_id = %s", (hash_password(pwd), uid))

                cur.execute("SELECT staff_id FROM STAFF WHERE user_id = %s", (uid,))
                s = cur.fetchone()
                if not s:
                    cur.execute("INSERT INTO STAFF (user_id, role, status) VALUES (%s, 'RECEPTIONIST', 'ACTIVE')", (uid,))
                else:
                    cur.execute("UPDATE STAFF SET role = 'RECEPTIONIST', status = 'ACTIVE' WHERE staff_id = %s", (s["staff_id"],))

            # 4. ADMIN
            cur.execute("SELECT user_id FROM USER_ACCOUNT WHERE email = %s", ("admin@thapar.edu",))
            u = cur.fetchone()
            if not u:
                cur.execute(
                    "INSERT INTO USER_ACCOUNT (email, password_hash, account_type, status) VALUES (%s, %s, 'STAFF', 'ACTIVE')",
                    ("admin@thapar.edu", hash_password("admin123")),
                )
                uid = cur.lastrowid
            else:
                uid = u["user_id"]
                cur.execute("UPDATE USER_ACCOUNT SET password_hash = %s, status = 'ACTIVE' WHERE user_id = %s", (hash_password("admin123"), uid))

            cur.execute("SELECT staff_id FROM STAFF WHERE user_id = %s", (uid,))
            s = cur.fetchone()
            if not s:
                cur.execute("INSERT INTO STAFF (user_id, role, status) VALUES (%s, 'ADMIN', 'ACTIVE')", (uid,))
            else:
                cur.execute("UPDATE STAFF SET role = 'ADMIN', status = 'ACTIVE' WHERE staff_id = %s", (s["staff_id"],))

            # 5. STUDENTS
            students = [
                ("1024030109", "hsingh1024030109@thapar.edu", "Harshveer Singh", "student123"),
                ("102403001", "102403001@thapar.edu", "Neha Kapoor", "student123"),
                ("102403112", "102403112@thapar.edu", "Kriti", "student123"),
                ("102403107", "102403107@thapar.edu", "Test Student", "student123"),
                ("102403205", "102403205@thapar.edu", "Daman", "student123"),
                ("102403348", "102403348@thapar.edu", "Matha Naparin", "student123"),
                ("102403499", "102403499@thapar.edu", "Simar Singh", "student123"),
            ]
            for roll, email, name, pwd in students:
                cur.execute("SELECT user_id FROM USER_ACCOUNT WHERE email = %s", (email,))
                u = cur.fetchone()
                if not u:
                    cur.execute(
                        "INSERT INTO USER_ACCOUNT (email, password_hash, account_type, status) VALUES (%s, %s, 'STUDENT', 'ACTIVE')",
                        (email, hash_password(pwd)),
                    )
                    uid = cur.lastrowid
                else:
                    uid = u["user_id"]
                    cur.execute("UPDATE USER_ACCOUNT SET password_hash = %s, status = 'ACTIVE' WHERE user_id = %s", (hash_password(pwd), uid))

                cur.execute("SELECT roll_number FROM STUDENT WHERE roll_number = %s", (roll,))
                st = cur.fetchone()
                if not st:
                    cur.execute(
                        "INSERT INTO STUDENT (roll_number, user_id, full_name, date_of_birth, sex, status) VALUES (%s, %s, %s, '2004-01-01', 'OTHER', 'ACTIVE')",
                        (roll, uid, name),
                    )
                else:
                    cur.execute("UPDATE STUDENT SET user_id = %s, full_name = %s, status = 'ACTIVE' WHERE roll_number = %s", (uid, name, roll))

                # Ensure MEDICAL_PROFILE_STATUS exists
                cur.execute(
                    """
                    INSERT INTO MEDICAL_PROFILE_STATUS (roll_number, allergy_status, condition_status, medication_status, updated_at)
                    VALUES (%s, 'NOT_REPORTED', 'NOT_REPORTED', 'NOT_REPORTED', datetime('now'))
                    ON CONFLICT (roll_number) DO NOTHING
                    """,
                    (roll,),
                )

        conn.commit()
        print("All development accounts successfully seeded!")
    finally:
        conn.close()


if __name__ == "__main__":
    seed_all()
