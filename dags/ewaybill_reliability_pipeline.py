"""
dags/ewaybill_reliability_pipeline.py
-------------------------------------
Airflow-orchestrated batch reliability pipeline for the DGCI&S E-Way Bill data.

Orchestrates:
1. Source ingestion & raw staging (ingest_source)
2. Historical & current source profiling (profile_raw_data)
3. Schema validation SCH-01..07 (schema_validation)
4. Data quality validation suites (quality_validation)
5. Cross-table reconciliation audits REC-DO01..06 (reconciliation_checks)
6. Year-over-Year statistical comparison (statistical_analysis)
7. Reliability branching decision (reliability_decision)
   -> PASS: Promote to trusted warehouse tables (promote_trusted_data)
   -> FAIL: Halt promotion and create incident record (create_incident)

Governance & Architecture:
- Business logic remains exclusively in src/ modules.
- Deterministic run-ID derived from Airflow execution context (compatible with PostgreSQL UUID).
- Strict failure semantics: data integrity failures halt promotion; statistical shifts and advisory
  reconciliation states (OTHER TERRITORY) do NOT cause failure.
- Transient retries for infrastructure/storage operations; zero retries for deterministic checks.
- Fully idempotent warehouse insertion.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import os
import sys
import uuid
from typing import Dict, Any, List

# Airflow imports
from airflow import DAG
from airflow.exceptions import AirflowException
try:
    from airflow.operators.empty import EmptyOperator
except ImportError:
    from airflow.operators.dummy import DummyOperator as EmptyOperator
from airflow.operators.python import PythonOperator, BranchPythonOperator

# Ensure project root is on sys.path for Airflow workers
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.database.connection import DatabaseManager
from src.database.repository import EwayBillRepository
from src.incidents.manager import IncidentManager
from src.notifications.email_service import EmailAlertNotifier
from src.ingestion.loader import EwayBillSourceLoader
from src.reconciliation.config import ReconciliationConfig
from src.reconciliation.engine import ReconciliationEngine
from src.reconciliation.reporter import ReconciliationReporter
from src.statistics.config import StatisticalConfig
from src.statistics.engine import StatisticalAnalysisEngine
from src.statistics.reporter import StatisticalReporter
from src.transformation.normalizer import EwayBillNormalizer
from src.validation.engine import ValidationEngine

# Source file locations
F22_PATH = os.path.join(PROJECT_ROOT, "data", "Road_EwayBill_2022_23.xlsx")
F24_PATH = os.path.join(PROJECT_ROOT, "data", "Road_EwayBill_2023_24.xlsx")


def get_source_file_path(context: Dict[str, Any]) -> str:
    """Resolves target source workbook path from DAG run conf or defaults to official workbook."""
    dag_run = context.get("dag_run")
    if dag_run and dag_run.conf and "source_filepath" in dag_run.conf:
        custom_path = dag_run.conf["source_filepath"]
        if not os.path.isabs(custom_path):
            return os.path.join(PROJECT_ROOT, custom_path)
        return custom_path
    return F24_PATH


def get_db_manager() -> DatabaseManager:
    """Returns DatabaseManager using environment variables with local defaults."""
    return DatabaseManager(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        dbname=os.getenv("POSTGRES_DB", "ewaybill_dw"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "Saksham@3124")
    )


def compute_deterministic_run_id(context: Dict[str, Any]) -> str:
    """Computes a deterministic UUID string from Airflow DAG run context."""
    dag_run = context.get("dag_run")
    raw_id = dag_run.run_id if dag_run else context.get("run_id", "default_manual_run")
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"airflow://ewaybill/{raw_id}"))


# =============================================================================
# Task Callables (Delegating to src/ modules)
# =============================================================================

def task_ingest_source(**context) -> str:
    """Ingests source workbooks, verifies hashes, and stages raw tables in PostgreSQL."""
    run_id = compute_deterministic_run_id(context)
    source_path = get_source_file_path(context)
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source file not found: {source_path}")

    loader = EwayBillSourceLoader(source_path)
    raw_data = loader.load_raw_workbook()

    db_mgr = get_db_manager()
    db_mgr.init_schema(os.path.join(PROJECT_ROOT, "sql", "schema.sql"))
    repo = EwayBillRepository(db_mgr)

    # Idempotent start
    actual_run_id = repo.start_pipeline_run(
        raw_data["metadata"]["source_filename"],
        raw_data["metadata"]["source_filepath"],
        run_id=run_id
    )
    repo.stage_raw_data(run_id, raw_data)

    context["task_instance"].xcom_push(key="run_id", value=actual_run_id)
    return actual_run_id


def task_profile_raw_data(**context) -> Dict[str, Any]:
    """Profiles raw data boundaries and reported totals."""
    source_path = get_source_file_path(context)
    loader = EwayBillSourceLoader(source_path)
    raw_data = loader.load_raw_workbook()
    meta = raw_data["metadata"]

    summary = {
        ws_name: {
            "rows": m.get("row_count"),
            "cols": m.get("column_count"),
            "nulls": m.get("null_cells_count")
        }
        for ws_name, m in meta.get("worksheets", {}).items()
    }
    return summary


def task_schema_validation(**context) -> int:
    """Executes schema validation checks (SCH-01 to SCH-07)."""
    run_id = compute_deterministic_run_id(context)
    source_path = get_source_file_path(context)
    loader = EwayBillSourceLoader(source_path)
    raw_data = loader.load_raw_workbook()
    normalizer = EwayBillNormalizer(raw_data["tables"])
    norm_tables = normalizer.normalize_all()

    engine = ValidationEngine()
    results = engine.validate_schema(raw_data, norm_tables, run_id=run_id)

    db_mgr = get_db_manager()
    repo = EwayBillRepository(db_mgr)
    repo.record_validation_results(run_id, results)

    failed = [r for r in results if r.status == "FAIL"]
    if failed:
        context["task_instance"].xcom_push(key="schema_failures", value=[r.to_dict() for r in failed])
    return len(results)


def task_quality_validation(**context) -> int:
    """Executes completeness, uniqueness, domain, numeric, structural, and total checks."""
    run_id = compute_deterministic_run_id(context)
    source_path = get_source_file_path(context)
    loader = EwayBillSourceLoader(source_path)
    raw_data = loader.load_raw_workbook()
    normalizer = EwayBillNormalizer(raw_data["tables"])
    norm_tables = normalizer.normalize_all()

    engine = ValidationEngine()
    results = []
    results.extend(engine.validate_completeness(raw_data, norm_tables, run_id=run_id))
    results.extend(engine.validate_uniqueness(norm_tables, run_id=run_id))
    results.extend(engine.validate_domain(norm_tables, run_id=run_id))
    results.extend(engine.validate_numeric(norm_tables, run_id=run_id))
    results.extend(engine.validate_structural(raw_data, norm_tables, run_id=run_id))
    results.extend(engine.validate_source_totals(raw_data, run_id=run_id))

    db_mgr = get_db_manager()
    repo = EwayBillRepository(db_mgr)
    repo.record_validation_results(run_id, results)

    failed = [r for r in results if r.status == "FAIL"]
    if failed:
        context["task_instance"].xcom_push(key="quality_failures", value=[r.to_dict() for r in failed])
    return len(results)


def task_reconciliation_checks(**context) -> int:
    """Executes cross-table reconciliation audits (REC-DO01 to REC-DO06)."""
    run_id = compute_deterministic_run_id(context)
    source_path = get_source_file_path(context)
    loader = EwayBillSourceLoader(source_path)
    raw_data = loader.load_raw_workbook()
    normalizer = EwayBillNormalizer(raw_data["tables"])
    norm_tables = normalizer.normalize_all()

    rec_config = ReconciliationConfig(absolute_tolerance=0.0001, relative_tolerance=1e-7)
    engine = ReconciliationEngine(config=rec_config)
    results = engine.run_all_reconciliations(raw_data, norm_tables, run_id=run_id)

    db_mgr = get_db_manager()
    repo = EwayBillRepository(db_mgr)
    repo.record_reconciliation_results(run_id, results)

    report_path = os.path.join(PROJECT_ROOT, "docs", "reconciliation_report.md")
    ReconciliationReporter.generate_report(results, run_id=run_id, output_file=report_path)

    # Note: Advisory warnings/unresolved do NOT block trusted loading.
    # Only critical blocking failures would block.
    blocking_fails = [r for r in results if r.status == "FAIL" and r.severity == "CRITICAL"]
    if blocking_fails:
        context["task_instance"].xcom_push(key="reconciliation_failures", value=[r.to_dict() for r in blocking_fails])
    return len(results)


def task_statistical_analysis(**context) -> int:
    """Executes Year-over-Year statistical analysis against FY 2022–23 baseline."""
    run_id = compute_deterministic_run_id(context)
    source_path = get_source_file_path(context)
    loader_22 = EwayBillSourceLoader(F22_PATH)
    raw_22 = loader_22.load_raw_workbook()
    loader_24 = EwayBillSourceLoader(source_path)
    raw_24 = loader_24.load_raw_workbook()

    stat_config = StatisticalConfig(alpha=0.05, psi_threshold_significant=0.25)
    engine = StatisticalAnalysisEngine(config=stat_config)
    results = engine.run_all_statistical_analyses(raw_22, raw_24, run_id=run_id)

    db_mgr = get_db_manager()
    repo = EwayBillRepository(db_mgr)
    repo.record_statistical_results(run_id, results)

    report_path = os.path.join(PROJECT_ROOT, "docs", "statistical_analysis_report.md")
    StatisticalReporter.generate_report(results, run_id=run_id, output_file=report_path)

    # Note: STATISTICALLY_DIFFERENT is an advisory signal and does NOT cause task or DAG failure.
    return len(results)


def task_reliability_decision(**context) -> str:
    """Evaluates validation outcomes to branch to promotion or incident creation."""
    ti = context["task_instance"]
    schema_fails = ti.xcom_pull(task_ids="schema_validation", key="schema_failures") or []
    quality_fails = ti.xcom_pull(task_ids="quality_validation", key="quality_failures") or []
    rec_fails = ti.xcom_pull(task_ids="reconciliation_checks", key="reconciliation_failures") or []

    all_failures = schema_fails + quality_fails + rec_fails
    if all_failures:
        ti.xcom_push(key="all_blocking_failures", value=all_failures)
        return "create_incident"
    return "promote_trusted_data"


def task_promote_trusted_data(**context) -> Dict[str, int]:
    """Promotes validated staging data into production trusted warehouse tables."""
    run_id = compute_deterministic_run_id(context)
    source_path = get_source_file_path(context)
    loader = EwayBillSourceLoader(source_path)
    raw_data = loader.load_raw_workbook()
    normalizer = EwayBillNormalizer(raw_data["tables"])
    norm_tables = normalizer.normalize_all()

    db_mgr = get_db_manager()
    repo = EwayBillRepository(db_mgr)

    counts = repo.load_trusted_data(run_id, norm_tables)
    repo.complete_pipeline_run(run_id, counts, [{"status": "ALL_GATES_PASSED"}])
    return counts


def task_create_incident(**context) -> None:
    """Records an incident, attempts email notification, and marks the pipeline run as failed."""
    run_id = compute_deterministic_run_id(context)
    ti = context["task_instance"]
    failures = ti.xcom_pull(task_ids="reliability_decision", key="all_blocking_failures") or []

    db_mgr = get_db_manager()
    repo = EwayBillRepository(db_mgr)
    inc_mgr = IncidentManager(db_mgr)

    # 1. Authoritative incident creation & persistence
    incident = inc_mgr.create_incident(run_id=run_id, failures=failures)
    inc_mgr.record_incident_in_db(incident)
    inc_path = inc_mgr.write_incident_file(incident, output_dir=os.path.join(PROJECT_ROOT, "docs", "incidents"))

    # 2. Email alert attempt (secondary delivery mechanism; failure does not erase incident)
    notifier = EmailAlertNotifier(incident_manager=inc_mgr)
    alert_result = notifier.send_incident_alert(incident)

    # 3. Mark pipeline run as failed in database
    repo.fail_pipeline_run(run_id, f"Reliability gate failed with {len(failures)} blocking checks.")

    # 4. Halt pipeline execution with clear failure summary
    raise AirflowException(
        f"Data reliability gates failed ({len(failures)} checks failed). "
        f"Trusted loading halted. Incident #{incident.incident_id or 'OPEN'} recorded at {inc_path}. "
        f"Alert status: {alert_result.get('status')}"
    )


# =============================================================================
# DAG Definition & Retry Policies
# =============================================================================

default_args = {
    "owner": "data-reliability",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,  # Default for transient operations
    "retry_delay": timedelta(seconds=15),
}

with DAG(
    dag_id="ewaybill_reliability_pipeline",
    default_args=default_args,
    description="DGCI&S E-Way Bill road movement data reliability and reconciliation pipeline",
    schedule_interval=None,  # Batch on-demand trigger
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["reliability", "reconciliation", "ewaybill", "dgci&s"],
) as dag:

    # 1. Start anchor
    start = EmptyOperator(
        task_id="start"
    )

    # 2. Source Ingestion (Transient retries: 2)
    ingest_source = PythonOperator(
        task_id="ingest_source",
        python_callable=task_ingest_source,
        retries=2,
        retry_delay=timedelta(seconds=10),
    )

    # 3. Source Profiling (Deterministic: 0 retries)
    profile_raw_data = PythonOperator(
        task_id="profile_raw_data",
        python_callable=task_profile_raw_data,
        retries=0,
    )

    # 4. Schema Validation (Deterministic: 0 retries)
    schema_validation = PythonOperator(
        task_id="schema_validation",
        python_callable=task_schema_validation,
        retries=0,
    )

    # 5. Quality Validation Suites (Deterministic: 0 retries)
    quality_validation = PythonOperator(
        task_id="quality_validation",
        python_callable=task_quality_validation,
        retries=0,
    )

    # 6. Cross-Table Reconciliation (Deterministic: 0 retries)
    reconciliation_checks = PythonOperator(
        task_id="reconciliation_checks",
        python_callable=task_reconciliation_checks,
        retries=0,
    )

    # 7. Year-over-Year Statistical Analysis (Deterministic: 0 retries)
    statistical_analysis = PythonOperator(
        task_id="statistical_analysis",
        python_callable=task_statistical_analysis,
        retries=0,
    )

    # 8. Reliability Decision Branching (Deterministic: 0 retries)
    reliability_decision = BranchPythonOperator(
        task_id="reliability_decision",
        python_callable=task_reliability_decision,
        retries=0,
    )

    # 9a. Trusted Data Promotion (Transient retries: 2)
    promote_trusted_data = PythonOperator(
        task_id="promote_trusted_data",
        python_callable=task_promote_trusted_data,
        retries=2,
        retry_delay=timedelta(seconds=10),
    )

    # 9b. Incident Creation (1 retry)
    create_incident = PythonOperator(
        task_id="create_incident",
        python_callable=task_create_incident,
        retries=1,
    )

    # =========================================================================
    # Task Dependencies (Enforcing strict pipeline sequence)
    # =========================================================================
    (
        start
        >> ingest_source
        >> profile_raw_data
        >> schema_validation
        >> quality_validation
        >> reconciliation_checks
        >> statistical_analysis
        >> reliability_decision
    )

    reliability_decision >> promote_trusted_data
    reliability_decision >> create_incident
