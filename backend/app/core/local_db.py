import os
import re
import sqlite3
from datetime import date, datetime, timedelta

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "campuscare_dev.db"))


def _clean_sql_for_sqlite(sql: str) -> str:
    s = sql.replace("%s", "?")
    # Strip row lock clauses: FOR UPDATE, FOR UPDATE SKIP LOCKED, FOR UPDATE NOWAIT
    s = re.sub(r'\s+FOR\s+UPDATE(\s+(SKIP\s+LOCKED|NOWAIT))?', '', s, flags=re.IGNORECASE)
    # Strip LOCK IN SHARE MODE
    s = re.sub(r'\s+LOCK\s+IN\s+SHARE\s+MODE', '', s, flags=re.IGNORECASE)
    # Replace INSERT IGNORE INTO with INSERT OR IGNORE INTO
    s = re.sub(r'\bINSERT\s+IGNORE\s+INTO\b', 'INSERT OR IGNORE INTO', s, flags=re.IGNORECASE)
    # Replace CURDATE() and NOW()
    s = re.sub(r'\bCURDATE\(\)', "DATE('now')", s, flags=re.IGNORECASE)
    s = re.sub(r'\bNOW\(\)', "DATETIME('now')", s, flags=re.IGNORECASE)
    # Convert MySQL empty INSERT () VALUES () to SQLite DEFAULT VALUES
    s = re.sub(r'\bINSERT\s+INTO\s+([`"\w]+)\s*\(\s*\)\s*VALUES\s*\(\s*\)', r'INSERT INTO \1 DEFAULT VALUES', s, flags=re.IGNORECASE)

    # Convert MySQL ON DUPLICATE KEY UPDATE to SQLite ON CONFLICT (...) DO UPDATE SET
    if re.search(r'\bON\s+DUPLICATE\s+KEY\s+UPDATE\b', s, flags=re.IGNORECASE):
        tbl_match = re.search(r'INSERT\s+(?:OR\s+\w+\s+)?INTO\s+([`"\w]+)', s, re.IGNORECASE)
        tbl_name = tbl_match.group(1).strip('`"[]').upper() if tbl_match else ""

        conflict_targets = {
            "EMERGENCY_CONTACT": "roll_number",
            "MEDICAL_PROFILE_STATUS": "roll_number",
            "DOCTOR_AVAILABILITY": "doctor_id, availability_date",
            "RFID_CARD": "card_uid",
            "DAILY_ANALYTICS_REPORT_LOG": "reporting_date",
            "ANALYTICS_REPORT_LOG": "report_date",
            "USER_ACCOUNT": "email",
            "STUDENT": "roll_number",
        }
        target = conflict_targets.get(tbl_name, "roll_number")

        # In SQLite upsert, VALUES(col) is written as excluded.col
        s = re.sub(r'\bVALUES\s*\(\s*(\w+)\s*\)', r'excluded.\1', s, flags=re.IGNORECASE)
        s = re.sub(r'\bON\s+DUPLICATE\s+KEY\s+UPDATE\b', f'ON CONFLICT ({target}) DO UPDATE SET', s, flags=re.IGNORECASE)

    return s.strip()


_DATETIME_RE = re.compile(r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$')
_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _convert_sqlite_val(v):
    if isinstance(v, str):
        if len(v) == 10 and _DATE_RE.match(v):
            try:
                return date.fromisoformat(v)
            except Exception:
                return v
        elif len(v) >= 19 and _DATETIME_RE.match(v):
            try:
                v_clean = v.replace('Z', '+00:00') if v.endswith('Z') else v
                return datetime.fromisoformat(v_clean)
            except Exception:
                return v
    return v


def _convert_row_dict(row_dict):
    if not row_dict:
        return row_dict
    return {k: _convert_sqlite_val(v) for k, v in row_dict.items()}


class SQLiteDictCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None

    def execute(self, sql, params=None):
        sqlite_sql = _clean_sql_for_sqlite(sql)

        try:
            if params is not None:
                if not isinstance(params, (tuple, list, dict)):
                    params = (params,)
                self._cursor.execute(sqlite_sql, params)
            else:
                self._cursor.execute(sqlite_sql)
            self.lastrowid = self._cursor.lastrowid
        except Exception as e:
            raise e
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return _convert_row_dict(dict(row))

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [_convert_row_dict(dict(r)) for r in rows]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class SQLiteConnectionWrapper:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return SQLiteDictCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def _sqlite_field(val, *args):
    try:
        return args.index(val) + 1
    except Exception:
        return 0


def _sqlite_concat(*args):
    return "".join(str(a) for a in args if a is not None)


def _sqlite_if(condition, true_val, false_val):
    return true_val if condition else false_val


def get_local_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.create_function("FIELD", -1, _sqlite_field)
    conn.create_function("CONCAT", -1, _sqlite_concat)
    conn.create_function("IF", 3, _sqlite_if)
    conn.create_function("DATABASE", 0, lambda: "campuscare_dev")
    conn.create_function("VERSION", 0, lambda: "3.45.3")
    conn.create_function("NOW", 0, lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    conn.create_function("CURDATE", 0, lambda: date.today().strftime("%Y-%m-%d"))
    return SQLiteConnectionWrapper(conn)
