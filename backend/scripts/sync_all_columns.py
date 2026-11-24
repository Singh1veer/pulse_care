import os
import re
import sqlite3

def sync_missing_columns():
    db_path = "backend/campuscare_dev.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    sql_dir = "backend/sql"
    sql_files = sorted([f for f in os.listdir(sql_dir) if f.endswith(".sql")])

    for fname in sql_files:
        fpath = os.path.join(sql_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        # Find CREATE TABLE statements
        matches = re.finditer(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`"\w]+)\s*\((.*?)\)\s*(?:ENGINE|;)', content, re.DOTALL | re.IGNORECASE)
        for m in matches:
            tbl_name = m.group(1).strip('`"[]').upper()
            body = m.group(2)

            # Check if table exists in SQLite
            cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND UPPER(name)=?", (tbl_name,))
            row = cur.fetchone()
            if not row:
                continue
            actual_tbl_name = row[0]

            # Get existing columns in SQLite
            existing_cols = {c[1].lower(): c for c in cur.execute(f"PRAGMA table_info({actual_tbl_name})").fetchall()}

            # Parse columns from SQL body
            lines = [l.strip() for l in body.split("\n")]
            for line in lines:
                line = line.strip().rstrip(",")
                if not line or line.upper().startswith(("CONSTRAINT", "PRIMARY", "UNIQUE", "FOREIGN", "KEY", "INDEX", "--")):
                    continue
                col_match = re.match(r'^[`"]?(\w+)[`"]?\s+([A-Za-z0-9_()]+)', line)
                if col_match:
                    col_name = col_match.group(1)
                    col_type = col_match.group(2).upper()
                    
                    if col_name.lower() not in existing_cols:
                        # Translate type for SQLite
                        sqlite_type = "TEXT"
                        if any(t in col_type for t in ("INT", "BIGINT", "TINYINT")):
                            sqlite_type = "INTEGER"
                        elif any(t in col_type for t in ("DATETIME", "TIMESTAMP")):
                            sqlite_type = "DATETIME"
                        elif "DATE" in col_type:
                            sqlite_type = "DATE"
                        elif any(t in col_type for t in ("DECIMAL", "NUMERIC", "FLOAT", "DOUBLE")):
                            sqlite_type = "REAL"
                        
                        alter_cmd = f"ALTER TABLE {actual_tbl_name} ADD COLUMN {col_name} {sqlite_type} NULL"
                        try:
                            cur.execute(alter_cmd)
                            print(f"[ADDED] {actual_tbl_name}.{col_name} ({sqlite_type})")
                        except Exception as e:
                            print(f"[ERROR] Could not add {actual_tbl_name}.{col_name}: {e}")

    conn.commit()
    conn.close()
    print("Column synchronization complete.")

if __name__ == "__main__":
    sync_missing_columns()
