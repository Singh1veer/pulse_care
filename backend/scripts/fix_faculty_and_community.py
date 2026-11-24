import sqlite3
import os
import sys

def migrate(db_path):
    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Update FACULTY_DIRECTORY columns
    dir_cols = [r[1] for r in cur.execute("PRAGMA table_info(FACULTY_DIRECTORY)").fetchall()]
    print("FACULTY_DIRECTORY cols before:", dir_cols)
    if "employee_id" not in dir_cols:
        print("Adding employee_id to FACULTY_DIRECTORY...")
        cur.execute("ALTER TABLE FACULTY_DIRECTORY ADD COLUMN employee_id VARCHAR(50) NULL")
    if "employee_code" not in dir_cols:
        print("Adding employee_code to FACULTY_DIRECTORY...")
        cur.execute("ALTER TABLE FACULTY_DIRECTORY ADD COLUMN employee_code VARCHAR(50) NULL")

    # Sync employee_id <-> employee_code in FACULTY_DIRECTORY
    cur.execute("UPDATE FACULTY_DIRECTORY SET employee_id = employee_code WHERE employee_id IS NULL AND employee_code IS NOT NULL")
    cur.execute("UPDATE FACULTY_DIRECTORY SET employee_code = employee_id WHERE employee_code IS NULL AND employee_id IS NOT NULL")

    # 2. Update FACULTY columns
    fac_cols = [r[1] for r in cur.execute("PRAGMA table_info(FACULTY)").fetchall()]
    print("FACULTY cols before:", fac_cols)
    if "employee_id" not in fac_cols:
        print("Adding employee_id to FACULTY...")
        cur.execute("ALTER TABLE FACULTY ADD COLUMN employee_id VARCHAR(50) NULL")
    if "employee_code" not in fac_cols:
        print("Adding employee_code to FACULTY...")
        cur.execute("ALTER TABLE FACULTY ADD COLUMN employee_code VARCHAR(50) NULL")

    # Sync employee_id <-> employee_code in FACULTY
    cur.execute("UPDATE FACULTY SET employee_id = employee_code WHERE employee_id IS NULL AND employee_code IS NOT NULL")
    cur.execute("UPDATE FACULTY SET employee_code = employee_id WHERE employee_code IS NULL AND employee_id IS NOT NULL")

    # Sync from FACULTY_DIRECTORY into FACULTY where matching by user_id -> email
    cur.execute("""
        UPDATE FACULTY
        SET employee_id = (
            SELECT COALESCE(fd.employee_id, fd.employee_code)
            FROM USER_ACCOUNT ua
            JOIN FACULTY_DIRECTORY fd ON fd.institutional_email = ua.email
            WHERE ua.user_id = FACULTY.user_id
        )
        WHERE employee_id IS NULL OR employee_id = ''
    """)
    cur.execute("UPDATE FACULTY SET employee_code = employee_id WHERE employee_code IS NULL OR employee_code = ''")

    # Explicitly ensure Dr. Rajesh Sharma has 260112 in FACULTY_DIRECTORY and FACULTY
    cur.execute("""
        UPDATE FACULTY_DIRECTORY
        SET employee_code = '260112', employee_id = '260112'
        WHERE institutional_email = 'dr.sharma@thapar.edu'
    """)
    cur.execute("""
        UPDATE FACULTY
        SET employee_code = '260112', employee_id = '260112'
        WHERE user_id IN (SELECT user_id FROM USER_ACCOUNT WHERE email = 'dr.sharma@thapar.edu')
    """)

    # 3. Ensure COMMUNITY_SEQUENCE table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS COMMUNITY_SEQUENCE (
            id INTEGER PRIMARY KEY AUTOINCREMENT
        )
    """)

    # 4. Ensure VISIT.roll_number is nullable for community and faculty visits
    visit_info = cur.execute("PRAGMA table_info(VISIT)").fetchall()
    roll_col = next((r for r in visit_info if r[1] == 'roll_number'), None)
    if roll_col and roll_col[3] == 1:
        print("VISIT.roll_number is NOT NULL. Recreating VISIT table with nullable roll_number...")
        cur.execute("PRAGMA foreign_keys=OFF")
        cols = [r[1] for r in visit_info]
        cur.execute("""
            CREATE TABLE IF NOT EXISTS VISIT_temp (
                visit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id BIGINT NULL,
                roll_number TEXT NULL,
                doctor_id BIGINT NULL,
                checked_in_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                called_at DATETIME NULL,
                consultation_started_at DATETIME NULL,
                consultation_completed_at DATETIME NULL,
                completed_at DATETIME NULL,
                cancelled_at DATETIME NULL,
                status TEXT DEFAULT 'WAITING',
                queue_number INTEGER NULL,
                purpose TEXT NULL,
                exit_reason TEXT NULL,
                cancel_reason VARCHAR(255) NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        common_cols = [c for c in cols if c in [
            'visit_id', 'patient_id', 'roll_number', 'doctor_id', 'checked_in_at', 'called_at',
            'consultation_started_at', 'consultation_completed_at', 'completed_at', 'cancelled_at',
            'status', 'queue_number', 'purpose', 'exit_reason', 'cancel_reason', 'created_at', 'updated_at'
        ]]
        c_str = ", ".join(common_cols)
        cur.execute(f"INSERT INTO VISIT_temp ({c_str}) SELECT {c_str} FROM VISIT")
        cur.execute("DROP TABLE VISIT")
        cur.execute("ALTER TABLE VISIT_temp RENAME TO VISIT")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_visit_patient ON VISIT(patient_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_visit_status ON VISIT(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_visit_doctor_status ON VISIT(doctor_id, status)")
        cur.execute("PRAGMA foreign_keys=ON")
        print("VISIT table recreated successfully with nullable roll_number!")

    conn.commit()

    # Print results
    dir_cols_after = [r[1] for r in cur.execute("PRAGMA table_info(FACULTY_DIRECTORY)").fetchall()]
    fac_cols_after = [r[1] for r in cur.execute("PRAGMA table_info(FACULTY)").fetchall()]
    print("FACULTY_DIRECTORY cols after:", dir_cols_after)
    print("FACULTY cols after:", fac_cols_after)
    print("FACULTY rows:", cur.execute("SELECT faculty_id, user_id, patient_id, employee_id, employee_code FROM FACULTY").fetchall())
    print("FACULTY_DIRECTORY rows:", cur.execute("SELECT faculty_dir_id, institutional_email, employee_code, employee_id FROM FACULTY_DIRECTORY").fetchall())

    conn.close()
    print("Migration successful!")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "campuscare_dev.db"))
    migrate(path)
