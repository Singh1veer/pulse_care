import sqlite3

def fix_sqlite_defaults():
    conn = sqlite3.connect("backend/campuscare_dev.db")
    cur = conn.cursor()

    cur.execute("PRAGMA foreign_keys=OFF")

    # Helper to recreate table with desired schema and copy overlapping columns
    def migrate_table(old_name, new_sql, new_name=None):
        if not new_name:
            new_name = old_name + "_TMP_MIG"
        cur.execute(f"DROP TABLE IF EXISTS {new_name};")
        cur.execute(new_sql.replace(old_name, new_name, 1))

        # Get overlapping columns
        old_cols = set(r[1] for r in cur.execute(f"PRAGMA table_info({old_name})").fetchall())
        new_cols = set(r[1] for r in cur.execute(f"PRAGMA table_info({new_name})").fetchall())
        common = list(old_cols.intersection(new_cols))
        col_list = ", ".join(common)

        cur.execute(f"INSERT OR IGNORE INTO {new_name} ({col_list}) SELECT {col_list} FROM {old_name};")
        cur.execute(f"DROP TABLE {old_name};")
        cur.execute(f"ALTER TABLE {new_name} RENAME TO {old_name};")
        print(f"[OK] Migrated {old_name} safely.")

    # 1. CONSULTATION
    migrate_table("CONSULTATION", """
    CREATE TABLE CONSULTATION (
        consultation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        visit_id INTEGER NOT NULL UNIQUE,
        doctor_id INTEGER NOT NULL,
        reason_for_visit TEXT NULL,
        diagnosis TEXT NOT NULL,
        clinical_notes TEXT NULL,
        consulted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        clinical_case_category TEXT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. PRESCRIPTION
    migrate_table("PRESCRIPTION", """
    CREATE TABLE PRESCRIPTION (
        prescription_id INTEGER PRIMARY KEY AUTOINCREMENT,
        consultation_id INTEGER NOT NULL UNIQUE,
        general_instructions TEXT NULL,
        finalized_at DATETIME NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. ALLERGY
    migrate_table("ALLERGY", """
    CREATE TABLE ALLERGY (
        allergy_id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_number VARCHAR(30) NULL,
        patient_id BIGINT NULL,
        allergen VARCHAR(150) NOT NULL,
        reaction TEXT NULL,
        severity TEXT NOT NULL DEFAULT 'MILD',
        notes TEXT NULL,
        recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. STUDENT_CONDITION
    migrate_table("STUDENT_CONDITION", """
    CREATE TABLE STUDENT_CONDITION (
        student_condition_id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_number VARCHAR(30) NOT NULL,
        condition_id INTEGER NOT NULL,
        notes TEXT NULL,
        recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5. STUDENT_MEDICATION
    migrate_table("STUDENT_MEDICATION", """
    CREATE TABLE STUDENT_MEDICATION (
        student_medication_id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_number VARCHAR(30) NOT NULL,
        medicine_name VARCHAR(150) NOT NULL,
        dosage VARCHAR(100) NULL,
        frequency VARCHAR(100) NULL,
        started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 6. DISPENSING
    migrate_table("DISPENSING", """
    CREATE TABLE DISPENSING (
        dispensing_id INTEGER PRIMARY KEY AUTOINCREMENT,
        visit_id INTEGER NOT NULL UNIQUE,
        dispensed_by_user_id INTEGER NULL,
        dispensed_at TIMESTAMP NULL,
        dispense_status TEXT NOT NULL DEFAULT 'PENDING',
        notes TEXT NULL
    );
    """)

    conn.commit()
    conn.close()
    print("All SQLite table schemas successfully migrated with robust defaults!")

if __name__ == "__main__":
    fix_sqlite_defaults()
