import sqlite3

conn = sqlite3.connect("backend/campuscare_dev.db")
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables = [r[0] for r in cursor.fetchall()]

print("Tables with NOT NULL columns without default:")
for t in tables:
    cols = cursor.execute(f"PRAGMA table_info({t})").fetchall()
    not_null_no_def = [c[1] for c in cols if c[3] == 1 and c[4] is None and c[5] == 0]
    if not_null_no_def:
        print(f"  {t}: {', '.join(not_null_no_def)}")
