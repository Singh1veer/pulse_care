"""
Ensures USER_ACCOUNT has password_hash as nullable (required for Google OAuth).
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "campuscare_dev.db"


def fix_user_account():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    PRAGMA foreign_keys=OFF;

    CREATE TABLE IF NOT EXISTS USER_ACCOUNT_v2 (
        user_id             INTEGER PRIMARY KEY AUTOINCREMENT,
        email               VARCHAR(255) NOT NULL UNIQUE,
        password_hash       VARCHAR(255) NULL,
        google_subject      VARCHAR(255) NULL,
        account_type        TEXT NOT NULL,
        status              TEXT NOT NULL DEFAULT 'ACTIVE',
        last_login_at       DATETIME NULL,
        created_at          DATETIME NULL,
        updated_at          DATETIME NULL
    );

    INSERT OR IGNORE INTO USER_ACCOUNT_v2 (user_id, email, password_hash, google_subject, account_type, status, last_login_at, created_at, updated_at)
    SELECT user_id, email, password_hash, google_subject, account_type, status, last_login_at, created_at, updated_at FROM USER_ACCOUNT;

    DROP TABLE USER_ACCOUNT;
    ALTER TABLE USER_ACCOUNT_v2 RENAME TO USER_ACCOUNT;

    PRAGMA foreign_keys=ON;
    """)

    conn.commit()
    print("USER_ACCOUNT table updated with nullable password_hash.")
    conn.close()


if __name__ == "__main__":
    fix_user_account()
