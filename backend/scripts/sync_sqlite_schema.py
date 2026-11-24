"""
Synchronizes the local SQLite database (campuscare_dev.db) with the full schema
defined across backend/sql/*.sql migrations.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "campuscare_dev.db"


def sync_schema():
    print(f"Syncing SQLite schema on {DB_PATH} ...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    def add_col_if_missing(table, col, col_def):
        cols = [c[1] for c in cur.execute(f"PRAGMA table_info({table})").fetchall()]
        if col not in cols:
            print(f"  Adding column '{col}' to table '{table}'")
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")

    # 1. USER_ACCOUNT
    add_col_if_missing("USER_ACCOUNT", "google_subject", "VARCHAR(255) NULL")
    add_col_if_missing("USER_ACCOUNT", "last_login_at", "DATETIME NULL")
    add_col_if_missing("USER_ACCOUNT", "created_at", "DATETIME NULL")
    add_col_if_missing("USER_ACCOUNT", "updated_at", "DATETIME NULL")

    # 2. STUDENT
    add_col_if_missing("STUDENT", "user_id", "BIGINT NULL")
    add_col_if_missing("STUDENT", "sex", "TEXT NOT NULL DEFAULT 'OTHER'")
    add_col_if_missing("STUDENT", "status", "TEXT NOT NULL DEFAULT 'ACTIVE'")
    add_col_if_missing("STUDENT", "phone_number", "VARCHAR(20) NULL")
    add_col_if_missing("STUDENT", "patient_id", "BIGINT NULL")
    add_col_if_missing("STUDENT", "created_at", "DATETIME NULL")
    add_col_if_missing("STUDENT", "updated_at", "DATETIME NULL")

    # 3. ALLERGY
    add_col_if_missing("ALLERGY", "reaction", "VARCHAR(255) NULL")
    add_col_if_missing("ALLERGY", "recorded_by_user_id", "BIGINT NULL")

    # 4. STUDENT_CONDITION
    add_col_if_missing("STUDENT_CONDITION", "recorded_by_user_id", "BIGINT NULL")

    # 5. STUDENT_MEDICATION
    add_col_if_missing("STUDENT_MEDICATION", "reason", "VARCHAR(255) NULL")
    add_col_if_missing("STUDENT_MEDICATION", "recorded_by_user_id", "BIGINT NULL")

    # 6. VISIT
    add_col_if_missing("VISIT", "doctor_id", "BIGINT NULL")
    add_col_if_missing("VISIT", "patient_id", "BIGINT NULL")
    add_col_if_missing("VISIT", "cancel_reason", "VARCHAR(255) NULL")
    add_col_if_missing("VISIT", "created_at", "DATETIME NULL")
    add_col_if_missing("VISIT", "updated_at", "DATETIME NULL")
    add_col_if_missing("VISIT", "queue_number", "INTEGER NULL")
    add_col_if_missing("VISIT", "called_at", "DATETIME NULL")
    add_col_if_missing("VISIT", "consultation_started_at", "DATETIME NULL")
    add_col_if_missing("VISIT", "consultation_completed_at", "DATETIME NULL")
    add_col_if_missing("VISIT", "completed_at", "DATETIME NULL")
    add_col_if_missing("VISIT", "cancelled_at", "DATETIME NULL")
    add_col_if_missing("VISIT", "exit_reason", "TEXT NULL")

    # 7. QUEUE_ENTRY
    add_col_if_missing("QUEUE_ENTRY", "entry_reason", "TEXT NULL")
    add_col_if_missing("QUEUE_ENTRY", "exit_reason", "TEXT NULL")
    add_col_if_missing("QUEUE_ENTRY", "queue_date", "DATETIME NULL")
    add_col_if_missing("QUEUE_ENTRY", "called_at", "DATETIME NULL")
    add_col_if_missing("QUEUE_ENTRY", "queue_type", "TEXT NOT NULL DEFAULT 'GENERAL'")

    # 7b. VISIT_EVENT
    add_col_if_missing("VISIT_EVENT", "notes", "VARCHAR(500) NULL")
    add_col_if_missing("VISIT_EVENT", "performed_by_user_id", "BIGINT NULL")

    # 8. CONSULTATION
    add_col_if_missing("CONSULTATION", "reason_for_visit", "TEXT NULL")
    add_col_if_missing("CONSULTATION", "clinical_case_category", "TEXT NULL")
    add_col_if_missing("CONSULTATION", "created_at", "DATETIME NULL")
    add_col_if_missing("CONSULTATION", "updated_at", "DATETIME NULL")

    # Migrate DOCTOR_AVAILABILITY if availability_date is missing
    cols_da = [c[1] for c in cur.execute("PRAGMA table_info(DOCTOR_AVAILABILITY)").fetchall()]
    if "availability_date" not in cols_da:
        cur.executescript("""
        DROP TABLE IF EXISTS DOCTOR_AVAILABILITY;
        CREATE TABLE DOCTOR_AVAILABILITY (
            availability_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id           BIGINT NOT NULL,
            availability_date   DATE NOT NULL DEFAULT CURRENT_DATE,
            status              TEXT NOT NULL DEFAULT 'AVAILABLE',
            start_time          TIME NULL,
            end_time            TIME NULL,
            created_by_user_id  BIGINT NULL,
            created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (doctor_id, availability_date)
        );
        INSERT OR IGNORE INTO DOCTOR_AVAILABILITY (doctor_id, status)
        SELECT doctor_id, 'AVAILABLE' FROM DOCTOR;
        """)

    # 9. PRESCRIPTION
    add_col_if_missing("PRESCRIPTION", "finalized_at", "DATETIME NULL")

    # 10. PRESCRIPTION_ITEM
    add_col_if_missing("PRESCRIPTION_ITEM", "dosage_form", "VARCHAR(50) NULL")
    add_col_if_missing("PRESCRIPTION_ITEM", "route", "VARCHAR(50) NULL")
    add_col_if_missing("PRESCRIPTION_ITEM", "duration_value", "INT NULL")
    add_col_if_missing("PRESCRIPTION_ITEM", "duration_unit", "TEXT NULL")
    add_col_if_missing("PRESCRIPTION_ITEM", "meal_relation", "TEXT NULL")
    add_col_if_missing("PRESCRIPTION_ITEM", "created_at", "DATETIME NULL")

    # Create missing tables
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS MEDICAL_PROFILE_STATUS (
        roll_number         VARCHAR(30) PRIMARY KEY,
        allergy_status      TEXT NOT NULL DEFAULT 'NOT_REPORTED',
        condition_status    TEXT NOT NULL DEFAULT 'NOT_REPORTED',
        medication_status   TEXT NOT NULL DEFAULT 'NOT_REPORTED',
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS EMERGENCY_CONTACT (
        emergency_contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_number         VARCHAR(30) NOT NULL UNIQUE,
        name                VARCHAR(150) NOT NULL,
        relationship        VARCHAR(50) NOT NULL,
        phone_number        VARCHAR(20) NOT NULL,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS RFID_CARD (
        rfid_card_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_number         VARCHAR(30) NOT NULL,
        card_uid            VARCHAR(100) NOT NULL UNIQUE,
        card_uid_hash       VARCHAR(100) NULL,
        status              TEXT NOT NULL DEFAULT 'ACTIVE',
        issued_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        deactivated_at      DATETIME NULL,
        issued_by_user_id   BIGINT NULL,
        revoked_by_user_id  BIGINT NULL
    );

    CREATE TABLE IF NOT EXISTS STUDENT_PROFILE_HIST (
        history_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_number         VARCHAR(30) NOT NULL,
        changed_by_user_id  BIGINT NULL,
        field_name          VARCHAR(50) NOT NULL,
        old_value           TEXT NULL,
        new_value           TEXT NULL,
        changed_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS DOCTOR_AVAILABILITY (
        availability_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id           BIGINT NOT NULL,
        availability_date   DATE NOT NULL DEFAULT CURRENT_DATE,
        status              TEXT NOT NULL DEFAULT 'AVAILABLE',
        start_time          TIME NULL,
        end_time            TIME NULL,
        created_by_user_id  BIGINT NULL,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (doctor_id, availability_date)
    );

    CREATE TABLE IF NOT EXISTS VISIT_EVENT (
        event_id            INTEGER PRIMARY KEY AUTOINCREMENT,
        visit_id            BIGINT NOT NULL,
        event_type          TEXT NOT NULL,
        event_data          TEXT NULL,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS DISPENSING (
        dispensing_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        visit_id            BIGINT NOT NULL,
        dispensed_by_staff_id BIGINT NULL,
        dispensed_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        status              TEXT NOT NULL DEFAULT 'COMPLETED'
    );

    CREATE TABLE IF NOT EXISTS DISPENSING_ITEM (
        dispensing_item_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        dispensing_id       BIGINT NOT NULL,
        prescription_item_id BIGINT NULL,
        medicine_name       VARCHAR(150) NOT NULL,
        quantity_dispensed  INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS EMERGENCY_LOG (
        emergency_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        visit_id            BIGINT NULL,
        roll_number         VARCHAR(30) NULL,
        severity            TEXT NOT NULL DEFAULT 'MODERATE',
        status              TEXT NOT NULL DEFAULT 'ACTIVE',
        notes               TEXT NULL,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS AMBULANCE_DISPATCH (
        dispatch_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        emergency_id        BIGINT NULL,
        driver_name         VARCHAR(100) NULL,
        contact_number      VARCHAR(20) NULL,
        destination         VARCHAR(150) NULL,
        status              TEXT NOT NULL DEFAULT 'DISPATCHED',
        dispatched_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS PATIENT (
        patient_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_type        TEXT NOT NULL,
        full_name           VARCHAR(150) NOT NULL,
        date_of_birth       DATE NULL,
        age                 INT NULL,
        gender              TEXT NOT NULL DEFAULT 'OTHER',
        blood_group         VARCHAR(10) NULL,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS COMMUNITY_SEQUENCE (
        seq_id              INTEGER PRIMARY KEY AUTOINCREMENT
    );

    CREATE TABLE IF NOT EXISTS COMMUNITY_PROFILE (
        community_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id          BIGINT NOT NULL UNIQUE,
        community_code      VARCHAR(30) NOT NULL UNIQUE,
        category            TEXT NOT NULL,
        category_other      VARCHAR(150) NULL,
        affiliation_details VARCHAR(255) NOT NULL,
        registered_by_staff_id BIGINT NULL,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS MANUAL_VERIFICATION (
        verification_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id          BIGINT NOT NULL,
        receptionist_user_id BIGINT NOT NULL,
        verification_outcome TEXT NOT NULL,
        notes               TEXT NULL,
        verified_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS FACULTY_DIRECTORY (
        faculty_dir_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        institutional_email VARCHAR(255) NOT NULL UNIQUE,
        full_name           VARCHAR(150) NOT NULL,
        department          VARCHAR(100) NOT NULL,
        designation         VARCHAR(100) NULL,
        employee_code       VARCHAR(50) NULL,
        is_active           BOOLEAN NOT NULL DEFAULT 1,
        account_created     BOOLEAN NOT NULL DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS FACULTY (
        faculty_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id             BIGINT NOT NULL UNIQUE,
        patient_id          BIGINT NOT NULL UNIQUE,
        employee_id         VARCHAR(50) NULL UNIQUE,
        department          VARCHAR(100) NOT NULL,
        designation         VARCHAR(100) NULL,
        status              TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS FACULTY_FAMILY_MEMBER (
        family_member_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        faculty_id          BIGINT NOT NULL,
        patient_id          BIGINT NOT NULL UNIQUE,
        relationship_type   TEXT NOT NULL,
        relationship_status TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS OUTBOX_EVENT (
        event_id            VARCHAR(64) PRIMARY KEY,
        event_type          VARCHAR(100) NOT NULL,
        channel             VARCHAR(200) NOT NULL,
        aggregate_type      VARCHAR(50) NOT NULL,
        aggregate_id        VARCHAR(100) NOT NULL,
        payload             TEXT NOT NULL,
        status              VARCHAR(20) NOT NULL DEFAULT 'PENDING',
        retry_count         INT NOT NULL DEFAULT 0,
        max_retries         INT NOT NULL DEFAULT 5,
        last_error          TEXT NULL,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        processed_at        DATETIME NULL,
        published_at        DATETIME NULL
    );

    CREATE TABLE IF NOT EXISTS ANALYTICS_REPORT_LOG (
        report_id           INTEGER PRIMARY KEY AUTOINCREMENT,
        report_date         DATE NOT NULL UNIQUE,
        report_data         TEXT NOT NULL,
        generated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    print("SQLite schema successfully synced with all 33 migration tables!")
    conn.close()


if __name__ == "__main__":
    sync_schema()
