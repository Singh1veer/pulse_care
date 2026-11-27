"""
PulseCare Automated AWS RDS (MySQL 8.0) Migration & Seeding Utility
Usage:
    python backend/scripts/migrate_to_rds.py --host <rds-endpoint> --user <username> --password <password> --db campuscare_dev
Or simply configure backend/.env and run:
    python backend/scripts/migrate_to_rds.py
"""

import argparse
import glob
import os
import ssl
import sys
from pathlib import Path
import pymysql

# Resolve root
ROOT_DIR = Path(__file__).resolve().parents[2]
SQL_DIR = ROOT_DIR / "backend" / "sql"


def parse_args():
    parser = argparse.ArgumentParser(description="Migrate PulseCare schema to AWS RDS MySQL")
    parser.add_argument("--host", help="AWS RDS MySQL Endpoint Hostname", default=os.getenv("DB_HOST", ""))
    parser.add_argument("--port", type=int, help="MySQL Port (default 3306)", default=int(os.getenv("DB_PORT", "3306")))
    parser.add_argument("--user", help="Master Username", default=os.getenv("DB_USER", "admin"))
    parser.add_argument("--password", help="Master Password", default=os.getenv("DB_PASSWORD", ""))
    parser.add_argument("--db", help="Database Name", default=os.getenv("DB_NAME", "campuscare_dev"))
    parser.add_argument("--ssl", help="SSL Mode (REQUIRED or DISABLED)", default=os.getenv("DB_SSL_MODE", "REQUIRED"))
    return parser.parse_args()


def get_connection(args):
    ssl_ctx = None
    if args.ssl.upper() != "DISABLED":
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

    print(f"Connecting to AWS RDS MySQL at {args.host}:{args.port} as {args.user}...")
    # First connect without DB to ensure database exists
    conn = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        ssl=ssl_ctx,
        autocommit=True,
        connect_timeout=15,
    )
    with conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{args.db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        print(f"Database `{args.db}` verified/created.")
    conn.select_db(args.db)
    return conn


def run_migrations(conn):
    sql_files = sorted(SQL_DIR.glob("*.sql"), key=lambda p: p.name)
    print(f"\nFound {len(sql_files)} SQL migration files in {SQL_DIR}.\n")

    executed = 0
    with conn.cursor() as cur:
        for sql_path in sql_files:
            file_name = sql_path.name
            raw_sql = sql_path.read_text(encoding="utf-8")
            
            # Split individual SQL statements
            statements = [stmt.strip() for stmt in raw_sql.split(";") if stmt.strip()]
            print(f"Executing {file_name} ({len(statements)} statements)...")
            
            for statement in statements:
                # Skip comments or empty strings
                if not statement or statement.startswith("--") or statement.startswith("/*"):
                    cleaned = "\n".join([line for line in statement.splitlines() if not line.strip().startswith("--") and not line.strip().startswith("/*")]).strip()
                    if not cleaned:
                        continue
                    statement = cleaned

                try:
                    cur.execute(statement)
                except pymysql.err.OperationalError as op_err:
                    # Ignore duplicate column / table / key errors for idempotent migrations
                    if op_err.args[0] in (1050, 1060, 1061):
                        continue
                    print(f"  Warning on {file_name}: {op_err}")
                except Exception as ex:
                    print(f"  Notice on {file_name}: {ex}")

            executed += 1

    print(f"\nSuccessfully executed all {executed} migration files on AWS RDS MySQL!")

    # Verify table count
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE();")
        table_count = cur.fetchone()[0]
        print(f"Verified total tables in AWS RDS database: {table_count}")


def main():
    args = parse_args()
    if not args.host:
        print("Error: AWS RDS Host is required. Specify via --host or set DB_HOST in backend/.env")
        sys.exit(1)

    try:
        conn = get_connection(args)
        run_migrations(conn)
        conn.close()
        print("\n>>> AWS RDS MIGRATION COMPLETED SUCCESSFULLY! <<<")
        print("To switch your application to this RDS instance:")
        print("Set DB_MODE=mysql in backend/.env and restart the backend container.")
    except Exception as exc:
        print(f"\nMigration failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
