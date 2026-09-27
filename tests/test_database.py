"""
test_database.py
----------------
Integration tests for PostgreSQL schema deployment and trusted loading.
"""

import pytest
import os
import psycopg2

from src.database.connection import DatabaseManager
from src.database.repository import EwayBillRepository
from src.ingestion.loader import EwayBillSourceLoader
from src.transformation.normalizer import EwayBillNormalizer


from unittest.mock import patch


def test_database_manager_default_configuration():
    """Verifies that DatabaseManager defaults to 127.0.0.1:5434 without environment variables."""
    non_pg_env = {k: v for k, v in os.environ.items() if not k.startswith("POSTGRES_")}
    with patch.dict(os.environ, non_pg_env, clear=True):
        mgr = DatabaseManager()
        assert mgr.host == "127.0.0.1"
        assert mgr.port == 5434
        assert mgr.dbname == "ewaybill_dw"
        assert mgr.user == "postgres"
        assert mgr.password == "postgres"


def test_database_manager_docker_override():
    """Verifies that DatabaseManager respects Docker container environment overrides (postgres:5432)."""
    docker_env = {
        "POSTGRES_HOST": "postgres",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "ewaybill_dw",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "postgres"
    }
    with patch.dict(os.environ, docker_env):
        mgr = DatabaseManager()
        assert mgr.host == "postgres"
        assert mgr.port == 5432
        assert mgr.dbname == "ewaybill_dw"
        assert mgr.user == "postgres"
        assert mgr.password == "postgres"


@pytest.fixture(scope="module")
def db_manager():
    # Connect using DatabaseManager default configuration (127.0.0.1:5434)
    mgr = DatabaseManager()
    try:
        conn = mgr.get_connection()
        conn.close()
        return mgr
    except Exception as e:
        pytest.skip(f"PostgreSQL connection unavailable: {e}")


def test_schema_deployment(db_manager):
    """Test PostgreSQL schema tables existence."""
    db_manager.init_schema("sql/schema.sql")
    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = [r[0] for r in cur.fetchall()]
        
        expected_tables = [
            "pipeline_runs",
            "raw_chapter_internal_matrix",
            "raw_chapter_inward_matrix",
            "raw_chapter_outward_matrix",
            "raw_chapter_summary",
            "raw_state_to_state_matrix",
            "raw_worksheet_metadata",
            "trusted_chapter_movement",
            "trusted_state_chapter_internal",
            "trusted_state_chapter_inward",
            "trusted_state_chapter_outward",
            "trusted_state_movement"
        ]
        for tbl in expected_tables:
            assert tbl in tables, f"Expected table '{tbl}' not found in database."
    finally:
        conn.close()


def test_trusted_row_counts_in_database(db_manager):
    """Test that trusted tables contain expected row counts in PostgreSQL."""
    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM trusted_state_movement;")
            assert cur.fetchone()[0] >= 1089

            cur.execute("SELECT COUNT(*) FROM trusted_chapter_movement;")
            assert cur.fetchone()[0] >= 90

            cur.execute("SELECT COUNT(*) FROM trusted_state_chapter_outward;")
            assert cur.fetchone()[0] >= 2970

            cur.execute("SELECT COUNT(*) FROM trusted_state_chapter_inward;")
            assert cur.fetchone()[0] >= 2970

            cur.execute("SELECT COUNT(*) FROM trusted_state_chapter_internal;")
            assert cur.fetchone()[0] >= 2970
    finally:
        conn.close()
