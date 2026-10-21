import os
import re
import threading
import sqlite3

try:
    import psycopg2
    import psycopg2.pool
    from psycopg2 import IntegrityError as PGIntegrityError
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
    PGIntegrityError = sqlite3.IntegrityError

# Try to get database credentials from Streamlit secrets or Environment or hardcoded Supabase fallback
DATABASE_URL = None
try:
    import streamlit as st
    if hasattr(st, "secrets") and "DATABASE_URL" in st.secrets:
        DATABASE_URL = st.secrets["DATABASE_URL"]
except Exception:
    pass

if not DATABASE_URL:
    DATABASE_URL = os.environ.get("DATABASE_URL")

# Default Supabase Connection Details
DEFAULT_SUPABASE_URL = "postgresql://postgres.mngekqtbfbtianfhafja:Fengabes295123.@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"

# Use Supabase if psycopg2 is available and either DATABASE_URL is set or DEFAULT_SUPABASE_URL is used
USE_POSTGRES = HAS_PSYCOPG2 and (bool(DATABASE_URL) or True)
ACTIVE_DB_URL = DATABASE_URL or DEFAULT_SUPABASE_URL

_lock = threading.RLock()


class PostgresCursorWrapper:
    def __init__(self, raw_cur, conn_wrapper):
        self._cur = raw_cur
        self._conn_wrapper = conn_wrapper
        self.lastrowid = None

    def _prepare_sql(self, sql, params=None):
        clean_sql = sql.strip()

        # Emulate PRAGMA table_info(x)
        if clean_sql.upper().startswith("PRAGMA TABLE_INFO"):
            m = re.findall(r"table_info\((.*?)\)", clean_sql, re.I)
            if m:
                tbl = m[0].strip().strip("'\"")
                return f"SELECT ordinal_position, column_name, data_type FROM information_schema.columns WHERE table_name = '{tbl}';", None

        # Convert SQLite autoincrement syntax
        clean_sql = re.sub(r"(?i)INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT", "SERIAL PRIMARY KEY", clean_sql)

        # Convert ? to %s for parameters
        if params is not None:
            clean_sql = clean_sql.replace("?", "%s")

        # Auto-append RETURNING id for single INSERT statements to support cursor.lastrowid
        is_insert = clean_sql.upper().startswith("INSERT INTO")
        if is_insert and "RETURNING" not in clean_sql.upper() and ";" not in clean_sql[:-1]:
            clean_sql = clean_sql.rstrip().rstrip(";") + " RETURNING id;"

        return clean_sql, params

    def execute(self, sql, params=None):
        with _lock:
            self._conn_wrapper._ensure_connected()
            prep_sql, prep_params = self._prepare_sql(sql, params)
            is_insert = prep_sql.upper().startswith("INSERT INTO") and "RETURNING ID" in prep_sql.upper()
            
            try:
                if prep_params is not None:
                    res = self._cur.execute(prep_sql, prep_params)
                else:
                    res = self._cur.execute(prep_sql)
            except Exception as e:
                # If connection was lost, reconnect and retry once
                if "closed" in str(e).lower() or "terminated" in str(e).lower():
                    self._conn_wrapper._reconnect()
                    self._cur = self._conn_wrapper._raw_conn.cursor()
                    if prep_params is not None:
                        res = self._cur.execute(prep_sql, prep_params)
                    else:
                        res = self._cur.execute(prep_sql)
                else:
                    raise

            if is_insert:
                try:
                    row = self._cur.fetchone()
                    if row:
                        self.lastrowid = row[0]
                except Exception:
                    pass

            return res

    def executemany(self, sql, seq_of_params):
        with _lock:
            self._conn_wrapper._ensure_connected()
            clean_sql = sql.replace("?", "%s")
            clean_sql = re.sub(r"(?i)INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT", "SERIAL PRIMARY KEY", clean_sql)
            return self._cur.executemany(clean_sql, seq_of_params)

    def fetchone(self):
        with _lock:
            return self._cur.fetchone()

    def fetchall(self):
        with _lock:
            return self._cur.fetchall()

    def fetchmany(self, size=None):
        with _lock:
            return self._cur.fetchmany(size) if size else self._cur.fetchmany()

    @property
    def rowcount(self):
        with _lock:
            return self._cur.rowcount

    @property
    def description(self):
        with _lock:
            return self._cur.description

    def close(self):
        with _lock:
            try:
                self._cur.close()
            except Exception:
                pass


class PostgresConnWrapper:
    def __init__(self, dsn):
        self._dsn = dsn
        self._raw_conn = None
        self._connect()

    def _connect(self):
        self._raw_conn = psycopg2.connect(self._dsn)

    def _ensure_connected(self):
        if self._raw_conn is None or self._raw_conn.closed:
            self._connect()
        else:
            try:
                # Quick health check
                with self._raw_conn.cursor() as cur:
                    cur.execute("SELECT 1;")
            except Exception:
                self._reconnect()

    def _reconnect(self):
        try:
            if self._raw_conn and not self._raw_conn.closed:
                self._raw_conn.close()
        except Exception:
            pass
        self._connect()

    def cursor(self):
        with _lock:
            self._ensure_connected()
            return PostgresCursorWrapper(self._raw_conn.cursor(), self)

    def commit(self):
        with _lock:
            self._ensure_connected()
            return self._raw_conn.commit()

    def rollback(self):
        with _lock:
            if self._raw_conn and not self._raw_conn.closed:
                return self._raw_conn.rollback()

    def close(self):
        with _lock:
            if self._raw_conn and not self._raw_conn.closed:
                return self._raw_conn.close()


# Initialize singleton connection
if USE_POSTGRES:
    try:
        conn = PostgresConnWrapper(ACTIVE_DB_URL)
        cursor = conn.cursor()
        IntegrityError = PGIntegrityError
        print("Connected to Supabase PostgreSQL successfully.")
    except Exception as e:
        print(f"Failed to connect to Supabase: {e}. Falling back to SQLite.")
        conn = sqlite3.connect("tahsilat_pro.db", check_same_thread=False)
        cursor = conn.cursor()
        IntegrityError = sqlite3.IntegrityError
else:
    conn = sqlite3.connect("tahsilat_pro.db", check_same_thread=False)
    cursor = conn.cursor()
    IntegrityError = sqlite3.IntegrityError
