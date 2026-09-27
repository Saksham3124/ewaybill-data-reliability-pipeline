"""
database/connection.py
----------------------
Database connectivity and persistence engine for PostgreSQL.
Provides helpers for schema deployment, raw data staging, and trusted loading.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import execute_values, Json


class DatabaseManager:
    """Manages PostgreSQL connection and DDL/DML operations."""

    def __init__(self,
                 host: Optional[str] = None,
                 port: Optional[int] = None,
                 dbname: Optional[str] = None,
                 user: Optional[str] = None,
                 password: Optional[str] = None):
        self.host = host or os.getenv("POSTGRES_HOST", "127.0.0.1")
        self.port = port or int(os.getenv("POSTGRES_PORT", "5434"))
        self.dbname = dbname or os.getenv("POSTGRES_DB", "ewaybill_dw")
        self.user = user or os.getenv("POSTGRES_USER", "postgres")
        self.password = password or os.getenv("POSTGRES_PASSWORD", "postgres")

    def get_connection(self):
        """Returns a new psycopg2 connection."""
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password
        )

    def init_schema(self, schema_file: str = "sql/schema.sql") -> None:
        """Executes the DDL schema file on the target database."""
        path = Path(schema_file)
        if not path.exists():
            raise FileNotFoundError(f"Schema file not found at: {path.resolve()}")

        with open(path, "r", encoding="utf-8") as f:
            ddl_sql = f.read()

        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(ddl_sql)
            conn.commit()
        finally:
            conn.close()

    def record_pipeline_run(self, source_filename: str, source_filepath: str, row_counts: Dict[str, int]) -> str:
        """Creates a pipeline_run record and returns run_id UUID string."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO pipeline_runs (source_filename, source_filepath, status, row_counts)
                    VALUES (%s, %s, 'COMPLETED', %s)
                    RETURNING run_id::text;
                """, (source_filename, source_filepath, Json(row_counts)))
                run_id = cur.fetchone()[0]
            conn.commit()
            return run_id
        finally:
            conn.close()
