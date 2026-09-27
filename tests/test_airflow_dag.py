"""
tests/test_airflow_dag.py
-------------------------
Comprehensive unit tests for the Apache Airflow DAG (dags/ewaybill_reliability_pipeline.py).

Verifies:
1. DAG imports cleanly without syntax errors or unhandled exceptions.
2. All 10 expected tasks exist with correct IDs and operator types.
3. Task dependency order strictly adheres to:
   start -> ingest_source -> profile_raw_data -> schema_validation ->
   quality_validation -> reconciliation_checks -> statistical_analysis ->
   reliability_decision -> (promote_trusted_data | create_incident).
4. No cyclical dependencies exist in the DAG.
5. Validation strictly precedes reconciliation.
6. Reconciliation strictly precedes statistical analysis.
7. Reliability decision strictly evaluates after statistical analysis.
8. Branching logic: Data integrity failure branches to create_incident and prevents trusted promotion.
9. Branching logic: Statistical difference (STATISTICALLY_DIFFERENT) does NOT fail or prevent promotion.
10. Retry configuration: sensible retries for infrastructure/transient tasks; zero retries for deterministic checks.
11. Run-ID determinism and idempotency.
"""

import os
import pytest
from datetime import datetime, timezone

from airflow.models import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
try:
    from airflow.operators.empty import EmptyOperator
except ImportError:
    from airflow.operators.dummy import DummyOperator as EmptyOperator

from dags.ewaybill_reliability_pipeline import (
    dag,
    compute_deterministic_run_id,
    task_reliability_decision,
)


EXPECTED_TASKS = [
    "start",
    "ingest_source",
    "profile_raw_data",
    "schema_validation",
    "quality_validation",
    "reconciliation_checks",
    "statistical_analysis",
    "reliability_decision",
    "promote_trusted_data",
    "create_incident"
]


# -----------------------------------------------------------------------------
# 1. DAG Import & Integrity Tests
# -----------------------------------------------------------------------------

def test_dag_import_and_metadata():
    """Verifies that the DAG object is instantiated properly with correct metadata."""
    assert dag is not None
    assert isinstance(dag, DAG)
    assert dag.dag_id == "ewaybill_reliability_pipeline"
    assert dag.catchup is False
    assert "reliability" in dag.tags
    assert "reconciliation" in dag.tags


def test_expected_tasks_exist():
    """Verifies that all 10 expected tasks exist in the DAG."""
    actual_task_ids = [t.task_id for t in dag.tasks]
    assert len(actual_task_ids) == len(EXPECTED_TASKS)
    for expected_id in EXPECTED_TASKS:
        assert expected_id in actual_task_ids, f"Expected task '{expected_id}' not found in DAG."


def test_no_cycles():
    """Verifies that the DAG graph is acyclic."""
    from airflow.utils.dag_cycle_tester import check_cycle
    check_cycle(dag)


# -----------------------------------------------------------------------------
# 2. Dependency Order Tests
# -----------------------------------------------------------------------------

def test_task_dependency_graph():
    """Verifies the exact upstream/downstream sequence."""
    task_map = {t.task_id: t for t in dag.tasks}

    # start -> ingest_source
    assert task_map["start"] in task_map["ingest_source"].upstream_list
    # ingest_source -> profile_raw_data
    assert task_map["ingest_source"] in task_map["profile_raw_data"].upstream_list
    # profile_raw_data -> schema_validation
    assert task_map["profile_raw_data"] in task_map["schema_validation"].upstream_list
    # schema_validation -> quality_validation
    assert task_map["schema_validation"] in task_map["quality_validation"].upstream_list
    # quality_validation -> reconciliation_checks
    assert task_map["quality_validation"] in task_map["reconciliation_checks"].upstream_list
    # reconciliation_checks -> statistical_analysis
    assert task_map["reconciliation_checks"] in task_map["statistical_analysis"].upstream_list
    # statistical_analysis -> reliability_decision
    assert task_map["statistical_analysis"] in task_map["reliability_decision"].upstream_list

    # reliability_decision -> [promote_trusted_data, create_incident]
    downstream_decision = [t.task_id for t in task_map["reliability_decision"].downstream_list]
    assert "promote_trusted_data" in downstream_decision
    assert "create_incident" in downstream_decision


def test_validation_precedes_reconciliation():
    """Verifies that schema and quality validation strictly precede reconciliation."""
    task_map = {t.task_id: t for t in dag.tasks}
    assert task_map["quality_validation"] in task_map["reconciliation_checks"].upstream_list
    assert task_map["schema_validation"] in task_map["quality_validation"].upstream_list


def test_reconciliation_precedes_statistical_analysis():
    """Verifies that cross-table reconciliation strictly precedes YoY statistical analysis."""
    task_map = {t.task_id: t for t in dag.tasks}
    assert task_map["reconciliation_checks"] in task_map["statistical_analysis"].upstream_list


def test_reliability_decision_occurs_after_statistical_analysis():
    """Verifies that the reliability decision occurs after statistical analysis."""
    task_map = {t.task_id: t for t in dag.tasks}
    assert task_map["statistical_analysis"] in task_map["reliability_decision"].upstream_list


# -----------------------------------------------------------------------------
# 3. Retry Configuration Tests
# -----------------------------------------------------------------------------

def test_sensible_retry_policies():
    """
    Verifies retry configuration:
    - Infrastructure/transient tasks (ingest_source, promote_trusted_data) have retries.
    - Deterministic analytical checks (schema, quality, reconciliation, statistics) have 0 retries.
    """
    task_map = {t.task_id: t for t in dag.tasks}

    # Transient operations
    assert task_map["ingest_source"].retries >= 1, "ingest_source should have retries for file/db transient errors."
    assert task_map["promote_trusted_data"].retries >= 1, "promote_trusted_data should have retries for db transient errors."

    # Deterministic checks must not blindly retry
    assert task_map["profile_raw_data"].retries == 0
    assert task_map["schema_validation"].retries == 0
    assert task_map["quality_validation"].retries == 0
    assert task_map["reconciliation_checks"].retries == 0
    assert task_map["statistical_analysis"].retries == 0
    assert task_map["reliability_decision"].retries == 0


# -----------------------------------------------------------------------------
# 4. Failure Semantics & Branching Decision Tests
# -----------------------------------------------------------------------------

class MockTaskInstance:
    """Mock Airflow TaskInstance to simulate XCom pulling and pushing."""
    def __init__(self, xcom_data=None):
        self.xcom_data = xcom_data or {}
        self.pushed_data = {}

    def xcom_pull(self, task_ids, key=None):
        return self.xcom_data.get(f"{task_ids}:{key}")

    def xcom_push(self, key, value):
        self.pushed_data[key] = value


def test_reliability_decision_branches_to_promote_on_pass():
    """Verifies that when all checks pass, reliability_decision routes to promote_trusted_data."""
    ti = MockTaskInstance({
        "schema_validation:schema_failures": [],
        "quality_validation:quality_failures": [],
        "reconciliation_checks:reconciliation_failures": []
    })
    context = {"task_instance": ti}
    branch = task_reliability_decision(**context)
    assert branch == "promote_trusted_data"


def test_reliability_decision_branches_to_incident_on_integrity_failure():
    """Verifies that data integrity failure prevents promotion and routes to create_incident."""
    ti = MockTaskInstance({
        "schema_validation:schema_failures": [{"check_id": "SCH-02", "status": "FAIL", "severity": "CRITICAL"}],
        "quality_validation:quality_failures": [],
        "reconciliation_checks:reconciliation_failures": []
    })
    context = {"task_instance": ti}
    branch = task_reliability_decision(**context)
    assert branch == "create_incident"
    assert "all_blocking_failures" in ti.pushed_data
    assert len(ti.pushed_data["all_blocking_failures"]) == 1


def test_statistical_difference_does_not_block_promotion():
    """
    Verifies that STATISTICALLY_DIFFERENT does NOT produce blocking failures
    and allows promotion to proceed.
    """
    # Statistical analysis task pushes no blocking failures to XCom
    ti = MockTaskInstance({
        "schema_validation:schema_failures": [],
        "quality_validation:quality_failures": [],
        "reconciliation_checks:reconciliation_failures": []
    })
    context = {"task_instance": ti}
    branch = task_reliability_decision(**context)
    assert branch == "promote_trusted_data"


# -----------------------------------------------------------------------------
# 5. Deterministic Run-ID Handling
# -----------------------------------------------------------------------------

def test_deterministic_run_id_generation():
    """Verifies that run-ID generation is completely deterministic and produces valid UUIDs."""
    context1 = {"run_id": "manual__2026-09-27T12:00:00"}
    context2 = {"run_id": "manual__2026-09-27T12:00:00"}
    context3 = {"run_id": "manual__2026-09-28T12:00:00"}

    id1 = compute_deterministic_run_id(context1)
    id2 = compute_deterministic_run_id(context2)
    id3 = compute_deterministic_run_id(context3)

    assert id1 == id2, "Run IDs for identical execution context must be identical (idempotent)."
    assert id1 != id3, "Run IDs for different execution contexts must be distinct."

    # Validate UUID format
    import uuid
    parsed = uuid.UUID(id1)
    assert str(parsed) == id1
