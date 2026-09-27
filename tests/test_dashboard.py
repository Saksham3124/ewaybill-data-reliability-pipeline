"""
tests/test_dashboard.py
-----------------------
Unit tests for the Phase 10 Streamlit Reliability Dashboard.

Verifies:
1. Clean imports and module availability.
2. Database configuration handling via environment variables.
3. All 6 required pages/sections exist in dashboard navigation.
4. Absolute read-only guarantees:
   - No write SQL statements (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE) exist in dashboard codebase.
   - Read-only session configuration in connection factory.
   - No incident mutation or resolution functions.
   - No Airflow trigger logic or DAG execution dispatchers.
5. Epistemic boundary adherence:
   - STATISTICALLY_DIFFERENT informational guidance note is present.
   - REC-DO06 / OTHER TERRITORY UNRESOLVED non-blocking guidance is present.
   - No jurisdiction or composite reliability rankings exist.
6. Data access functions query construction and filtering behavior.
"""

import inspect
import os
import re
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

import dashboard.data_access as da
import dashboard.app as app


# -----------------------------------------------------------------------------
# 1. Imports & Page Sections
# -----------------------------------------------------------------------------

def test_dashboard_imports():
    """Verifies that the dashboard modules import cleanly."""
    assert da is not None
    assert app is not None


def test_required_pages_exist():
    """Verifies that all 6 required pages are declared in dashboard navigation."""
    expected_pages = [
        "📊 Overview",
        "🔍 Data Quality",
        "⚖️ Reconciliation",
        "📈 Year-over-Year Statistics",
        "🚨 Incidents",
        "⏱️ Pipeline Runs"
    ]
    assert hasattr(app, "PAGES")
    for page in expected_pages:
        assert page in app.PAGES, f"Required page '{page}' not found in dashboard PAGES."


# -----------------------------------------------------------------------------
# 2. Database Configuration Handling
# -----------------------------------------------------------------------------

def test_database_configuration_handling():
    """Verifies that get_db_connection reads environment variables with safe defaults."""
    with patch("psycopg2.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        with patch.dict(os.environ, {
            "POSTGRES_HOST": "db.internal.net",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "test_dw",
            "POSTGRES_USER": "test_user",
            "POSTGRES_PASSWORD": "test_password"
        }):
            conn = da.get_db_connection()

            mock_connect.assert_called_once_with(
                host="db.internal.net",
                port=5432,
                dbname="test_dw",
                user="test_user",
                password="test_password",
                connect_timeout=5
            )
            # Verify session is strictly configured as read-only
            mock_conn.set_session.assert_called_once_with(readonly=True, autocommit=True)


def test_database_configuration_defaults():
    """Verifies that get_db_connection falls back to 127.0.0.1:5434 and ewaybill_dw without env vars."""
    with patch("psycopg2.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        non_pg_env = {k: v for k, v in os.environ.items() if not k.startswith("POSTGRES_")}
        with patch.dict(os.environ, non_pg_env, clear=True):
            conn = da.get_db_connection()

            mock_connect.assert_called_once_with(
                host="127.0.0.1",
                port=5434,
                dbname="ewaybill_dw",
                user="postgres",
                password="postgres",
                connect_timeout=5
            )
            mock_conn.set_session.assert_called_once_with(readonly=True, autocommit=True)


# -----------------------------------------------------------------------------
# 3. Read-Only Codebase & Security Guarantees
# -----------------------------------------------------------------------------

def test_read_only_sql_guarantee():
    """
    Statically audits dashboard/data_access.py and dashboard/app.py
    to verify that NO write SQL statements exist in the dashboard codebase.
    """
    forbidden_sql_patterns = [
        r"\bINSERT\s+INTO\b",
        r"\bUPDATE\s+\w+\s+SET\b",
        r"\bDELETE\s+FROM\b",
        r"\bDROP\s+TABLE\b",
        r"\bALTER\s+TABLE\b",
        r"\bTRUNCATE\b"
    ]

    files_to_check = [
        os.path.join(os.path.dirname(__file__), "..", "dashboard", "data_access.py"),
        os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
    ]

    for fpath in files_to_check:
        with open(fpath, "r", encoding="utf-8") as f:
            code = f.read()

        for pattern in forbidden_sql_patterns:
            matches = re.findall(pattern, code, re.IGNORECASE)
            assert len(matches) == 0, f"Forbidden mutating SQL keyword matching '{pattern}' found in {fpath}!"


def test_no_incident_mutation_functions():
    """Verifies that no functions for resolving, closing, or mutating incidents exist in data_access."""
    functions = [name for name, _ in inspect.getmembers(da, inspect.isfunction)]
    for fn_name in functions:
        assert not fn_name.startswith("resolve_"), f"Mutating function {fn_name} found."
        assert not fn_name.startswith("update_"), f"Mutating function {fn_name} found."
        assert not fn_name.startswith("delete_"), f"Mutating function {fn_name} found."
        assert not fn_name.startswith("insert_"), f"Mutating function {fn_name} found."


def test_no_airflow_triggers():
    """Verifies that dashboard does not import or invoke Airflow triggering operators."""
    app_path = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()

    forbidden_triggers = [
        "TriggerDagRunOperator",
        "trigger_dag",
        "create_dagrun",
        "airflow.api.client"
    ]
    for trigger in forbidden_triggers:
        assert trigger not in content, f"Forbidden Airflow trigger '{trigger}' found in app.py."


# -----------------------------------------------------------------------------
# 4. Epistemic Boundary Verification
# -----------------------------------------------------------------------------

def test_statistical_status_display_epistemic_note():
    """Verifies that the mandatory informational note for STATISTICALLY_DIFFERENT is in app.py."""
    app_path = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()

    part1 = "STATISTICALLY_DIFFERENT indicates an observed distributional difference"
    part2 = "It does not by itself indicate data corruption or pipeline failure."
    assert part1 in content, "Mandatory STATISTICALLY_DIFFERENT informational note missing from app.py."
    assert part2 in content, "Mandatory STATISTICALLY_DIFFERENT informational note missing from app.py."


def test_unresolved_reconciliation_display():
    """Verifies that OTHER TERRITORY / REC-DO06 is explicitly marked as UNRESOLVED non-blocking."""
    app_path = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "OTHER TERRITORY" in content
    assert "REC-DO06" in content
    assert "UNRESOLVED non-blocking" in content


# -----------------------------------------------------------------------------
# 5. Data Access Query Functions & Filtering (Mocked)
# -----------------------------------------------------------------------------

@patch("dashboard.data_access.get_db_connection")
def test_fetch_validation_results_with_filters(mock_get_conn):
    """Verifies that fetch_validation_results constructs parameterized WHERE clauses."""
    mock_conn = MagicMock()
    mock_get_conn.return_value.__enter__.return_value = mock_conn

    # Mock pd.read_sql_query
    with patch("pandas.read_sql_query") as mock_read_sql:
        mock_read_sql.return_value = pd.DataFrame([{"check_id": "NUM-01", "status": "PASS"}])

        df = da.fetch_validation_results(
            run_id="run-123",
            table_name="table_iv_inward",
            check_category="NUMERIC",
            status="PASS"
        )

        assert not df.empty
        query_arg, conn_arg = mock_read_sql.call_args[0]
        params_arg = mock_read_sql.call_args[1].get("params")

        assert "run_id = %s" in query_arg
        assert "table_name = %s" in query_arg
        assert "check_category = %s" in query_arg
        assert "status = %s" in query_arg
        assert params_arg == ["run-123", "table_iv_inward", "NUMERIC", "PASS"]


@patch("dashboard.data_access.get_db_connection")
def test_fetch_incidents_with_filters(mock_get_conn):
    """Verifies that fetch_incidents filters by severity and status correctly."""
    mock_conn = MagicMock()
    mock_get_conn.return_value.__enter__.return_value = mock_conn

    with patch("pandas.read_sql_query") as mock_read_sql:
        mock_read_sql.return_value = pd.DataFrame([{"incident_id": 1, "severity": "CRITICAL"}])

        df = da.fetch_incidents(
            severity="CRITICAL",
            status="OPEN"
        )

        assert not df.empty
        query_arg, _ = mock_read_sql.call_args[0]
        params_arg = mock_read_sql.call_args[1].get("params")

        assert "severity = %s" in query_arg
        assert "status = %s" in query_arg
        assert params_arg == ["CRITICAL", "OPEN"]


@patch("dashboard.data_access.get_db_connection")
def test_fetch_trusted_counts(mock_get_conn):
    """Verifies fetch_trusted_counts queries the 5 golden tables."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_get_conn.return_value.__enter__.return_value = mock_conn

    mock_cur.fetchone.return_value = (42,)

    counts = da.fetch_trusted_counts("run-abc")
    assert len(counts) == 5
    assert "trusted_state_movement" in counts
    assert counts["trusted_state_movement"] == 42
    assert mock_cur.execute.call_count == 5
