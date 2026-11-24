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
    return s.strip()


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
        return dict(row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [dict(r) for r in rows]

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


def get_local_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return SQLiteConnectionWrapper(conn)
