"""
dashboard/data_access.py
-------------------------
Read-only data access layer for the E-Way Bill Streamlit Reliability Dashboard.

Guarantees:
- Strictly read-only operations (SELECT queries only).
- Never writes, updates, deletes, creates, or alters database records.
- Safe connection management and parameterization.
- Streamlit cache integration with manual invalidation support.
"""

import os
import psycopg2
import psycopg2.extras
import pandas as pd
from typing import Dict, Any, List, Optional
import streamlit as st


def get_db_connection():
    """Returns a read-only PostgreSQL database connection using environment variables."""
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = int(os.getenv("POSTGRES_PORT", "5434"))
    dbname = os.getenv("POSTGRES_DB", "ewaybill_dw")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")

    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        connect_timeout=5
    )
    # Set session to read-only for complete security
    conn.set_session(readonly=True, autocommit=True)
    return conn


@st.cache_data(ttl=60)
def fetch_pipeline_runs() -> pd.DataFrame:
    """Fetches all pipeline execution runs ordered by start time descending."""
    query = """
        SELECT run_id::text, source_filename, source_filepath,
               created_at AS started_at, completed_at, status,
               ROUND(EXTRACT(EPOCH FROM (completed_at - created_at))::numeric, 2) AS duration_seconds,
               row_counts AS raw_row_counts, validation_summary
        FROM pipeline_runs
        ORDER BY created_at DESC;
    """
    with get_db_connection() as conn:
        df = pd.read_sql_query(query, conn)
    return df


@st.cache_data(ttl=60)
def fetch_latest_run_summary() -> Optional[Dict[str, Any]]:
    """Retrieves high-level summary metrics for the most recent pipeline execution run."""
    query = """
        SELECT run_id::text, source_filename, created_at AS started_at, completed_at, status,
               ROUND(EXTRACT(EPOCH FROM (completed_at - created_at))::numeric, 2) AS duration_seconds,
               row_counts AS raw_row_counts, validation_summary
        FROM pipeline_runs
        ORDER BY created_at DESC
        LIMIT 1;
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query)
            row = cur.fetchone()
            if not row:
                return None
            return dict(row)


@st.cache_data(ttl=60)
def fetch_validation_results(
    run_id: Optional[str] = None,
    table_name: Optional[str] = None,
    check_category: Optional[str] = None,
    status: Optional[str] = None
) -> pd.DataFrame:
    """Fetches validation results with optional multi-attribute filtering."""
    clauses = ["1=1"]
    params = []

    if run_id and run_id != "ALL":
        clauses.append("run_id = %s")
        params.append(run_id)
    if table_name and table_name != "ALL":
        clauses.append("table_name = %s")
        params.append(table_name)
    if check_category and check_category != "ALL":
        clauses.append("check_category = %s")
        params.append(check_category)
    if status and status != "ALL":
        clauses.append("status = %s")
        params.append(status)

    where_str = " AND ".join(clauses)
    query = f"""
        SELECT validation_id, run_id::text, check_id, check_category,
               check_name, table_name, status, severity,
               expected_value, observed_value, difference,
               affected_records, message, executed_at
        FROM validation_results
        WHERE {where_str}
        ORDER BY validation_id ASC;
    """
    with get_db_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df


@st.cache_data(ttl=60)
def fetch_reconciliation_results(
    run_id: Optional[str] = None,
    rule_code: Optional[str] = None,
    status: Optional[str] = None
) -> pd.DataFrame:
    """Fetches cross-table reconciliation audit results."""
    clauses = ["1=1"]
    params = []

    if run_id and run_id != "ALL":
        clauses.append("run_id = %s")
        params.append(run_id)
    if rule_code and rule_code != "ALL":
        clauses.append("rule_code = %s")
        params.append(rule_code)
    if status and status != "ALL":
        clauses.append("status = %s")
        params.append(status)

    where_str = " AND ".join(clauses)
    query = f"""
        SELECT reconciliation_id, run_id::text, rule_code, rule_category,
               source_tables, dimension, entity,
               expected_value, observed_value,
               absolute_difference, relative_difference,
               absolute_tolerance, relative_tolerance,
               status, severity, message, executed_at
        FROM reconciliation_results
        WHERE {where_str}
        ORDER BY reconciliation_id ASC;
    """
    with get_db_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df


@st.cache_data(ttl=60)
def fetch_statistical_results(
    run_id: Optional[str] = None,
    dimension: Optional[str] = None,
    test_method: Optional[str] = None,
    status: Optional[str] = None
) -> pd.DataFrame:
    """Fetches Year-over-Year statistical comparison results."""
    clauses = ["1=1"]
    params = []

    if run_id and run_id != "ALL":
        clauses.append("run_id = %s")
        params.append(run_id)
    if dimension and dimension != "ALL":
        clauses.append("dimension = %s")
        params.append(dimension)
    if test_method and test_method != "ALL":
        clauses.append("test_method = %s")
        params.append(test_method)
    if status and status != "ALL":
        clauses.append("status = %s")
        params.append(status)

    where_str = " AND ".join(clauses)
    query = f"""
        SELECT statistical_id, run_id::text, comparison_year, reference_year,
               dimension, metric, test_method,
               sample_size_reference, sample_size_comparison,
               statistic, p_value, alpha, psi_value, psi_threshold,
               status, interpretation, executed_at
        FROM statistical_results
        WHERE {where_str}
        ORDER BY statistical_id ASC;
    """
    with get_db_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df


@st.cache_data(ttl=60)
def fetch_incidents(
    run_id: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    source_table: Optional[str] = None
) -> pd.DataFrame:
    """Fetches incident records with failure diagnostics and JSON payloads."""
    clauses = ["1=1"]
    params = []

    if run_id and run_id != "ALL":
        clauses.append("run_id = %s")
        params.append(run_id)
    if severity and severity != "ALL":
        clauses.append("severity = %s")
        params.append(severity)
    if status and status != "ALL":
        clauses.append("status = %s")
        params.append(status)
    if source_table and source_table != "ALL":
        clauses.append("source_table = %s")
        params.append(source_table)

    where_str = " AND ".join(clauses)
    query = f"""
        SELECT incident_id, run_id::text, severity, status, failure_type,
               source_table, check_id, check_name,
               expected_value, observed_value, difference,
               affected_record_count, title, description,
               triggering_failures, detection_timestamp,
               resolution_timestamp, resolution_notes,
               alert_sent, alert_sent_at
        FROM incidents
        WHERE {where_str}
        ORDER BY detection_timestamp DESC;
    """
    with get_db_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df


@st.cache_data(ttl=60)
def fetch_trusted_counts(run_id: str) -> Dict[str, int]:
    """Fetches row counts across the 5 trusted warehouse tables for a run."""
    tables = [
        "trusted_state_movement",
        "trusted_chapter_movement",
        "trusted_state_chapter_outward",
        "trusted_state_chapter_inward",
        "trusted_state_chapter_internal"
    ]
    counts = {}
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for tbl in tables:
                cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE run_id = %s;", (run_id,))
                counts[tbl] = cur.fetchone()[0]
    return counts
