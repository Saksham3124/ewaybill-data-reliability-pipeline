"""
tests/test_reconciliation_engine.py
-----------------------------------
Comprehensive unit & integration tests for Phase 5 Cross-Table Reconciliation Engine.
Verifies all 6 DATA-OBSERVED cross-table audits (REC-DO01 to REC-DO06),
OTHER TERRITORY special handling, tolerance behavior, NULL handling,
database persistence, and strict governance constraints.
"""

import pytest
import os
import pandas as pd
import numpy as np

from src.reconciliation.config import ReconciliationConfig
from src.reconciliation.engine import ReconciliationEngine
from src.reconciliation.models import ReconciliationStatus, ReconciliationSeverity
from src.ingestion.loader import EwayBillSourceLoader
from src.transformation.normalizer import EwayBillNormalizer
from src.database.connection import DatabaseManager
from src.database.repository import EwayBillRepository


@pytest.fixture(scope="module")
def real_dataset():
    """Loads and normalizes real DGCI&S workbook."""
    loader = EwayBillSourceLoader("data/Road_EwayBill_2023_24.xlsx")
    raw = loader.load_raw_workbook()
    normalizer = EwayBillNormalizer(raw["tables"])
    norm = normalizer.normalize_all()
    return raw, norm


@pytest.fixture
def engine():
    return ReconciliationEngine()


# -----------------------------------------------------------------------------
# 1. National-Level Audits (REC-DO01, REC-DO02, REC-DO03)
# -----------------------------------------------------------------------------

def test_rec_do01_national_total_equivalence(engine, real_dataset):
    """Test REC-DO01: Table I matrix total matches Table II national total."""
    raw_data, norm_tables = real_dataset
    res = engine.reconcile_rec_do01(raw_data, norm_tables, run_id="test_do01")

    assert res.rule_code == "REC-DO01"
    assert res.status == ReconciliationStatus.PASS.value
    assert res.expected_value == pytest.approx(20319786.98011017, abs=1e-3)
    assert res.observed_value == pytest.approx(20319786.98011017, abs=1e-3)
    assert res.absolute_difference < 0.001


def test_rec_do02_outward_inward_equivalence(engine, real_dataset):
    """Test REC-DO02: Table III outward matches Table IV inward grand total."""
    raw_data, norm_tables = real_dataset
    res = engine.reconcile_rec_do02(raw_data, norm_tables, run_id="test_do02")

    assert res.rule_code == "REC-DO02"
    assert res.status == ReconciliationStatus.PASS.value
    assert res.expected_value == pytest.approx(10429324.40404665, abs=1e-3)
    assert res.observed_value == pytest.approx(10429324.40404665, abs=1e-3)
    assert res.absolute_difference < 0.001


def test_rec_do03_national_partitioning_outward_internal(engine, real_dataset):
    """Test REC-DO03: Table II total vs (Table III outward + Table V internal)."""
    raw_data, norm_tables = real_dataset
    results = engine.reconcile_rec_do03(raw_data, norm_tables, run_id="test_do03")
    assert len(results) == 2

    r_out = [r for r in results if r.dimension == "OUTWARD_INTERNAL_PARTITION"][0]
    assert r_out.status == ReconciliationStatus.PASS.value
    assert r_out.expected_value == pytest.approx(20319786.98011017, abs=1e-3)
    assert r_out.observed_value == pytest.approx(20319786.98011017, abs=1e-3)
    assert r_out.absolute_difference < 0.001


def test_rec_do03_national_partitioning_inward_internal(engine, real_dataset):
    """Test REC-DO03: Table II total vs (Table IV inward + Table V internal)."""
    raw_data, norm_tables = real_dataset
    results = engine.reconcile_rec_do03(raw_data, norm_tables, run_id="test_do03")

    r_in = [r for r in results if r.dimension == "INWARD_INTERNAL_PARTITION"][0]
    assert r_in.status == ReconciliationStatus.PASS.value
    assert r_in.expected_value == pytest.approx(20319786.98011017, abs=1e-3)
    assert r_in.observed_value == pytest.approx(20319786.98011017, abs=1e-3)
    assert r_in.absolute_difference < 0.001


# -----------------------------------------------------------------------------
# 2. State-Level Marginal Audits (REC-DO04, REC-DO05)
# -----------------------------------------------------------------------------

def test_rec_do04_all_33_state_column_marginals(engine, real_dataset):
    """Test REC-DO04: State column marginals hold across all 33 jurisdictions."""
    raw_data, norm_tables = real_dataset
    results = engine.reconcile_rec_do04(raw_data, norm_tables, run_id="test_do04")

    assert len(results) == 33
    passed = [r for r in results if r.status == ReconciliationStatus.PASS.value]
    assert len(passed) == 33

    # Explicitly check OTHER TERRITORY holds in REC-DO04
    ot = [r for r in results if r.entity == "OTHER TERRITORY"][0]
    assert ot.status == ReconciliationStatus.PASS.value
    assert ot.absolute_difference < 0.001


def test_rec_do05_all_33_state_row_marginals(engine, real_dataset):
    """Test REC-DO05: State row marginals hold across all 33 jurisdictions."""
    raw_data, norm_tables = real_dataset
    results = engine.reconcile_rec_do05(raw_data, norm_tables, run_id="test_do05")

    assert len(results) == 33
    passed = [r for r in results if r.status == ReconciliationStatus.PASS.value]
    assert len(passed) == 33

    # Explicitly check OTHER TERRITORY holds in REC-DO05
    ot = [r for r in results if r.entity == "OTHER TERRITORY"][0]
    assert ot.status == ReconciliationStatus.PASS.value
    assert ot.absolute_difference < 0.001


# -----------------------------------------------------------------------------
# 3. REC-DO06 & OTHER TERRITORY Special Handling
# -----------------------------------------------------------------------------

def test_rec_do06_32_passing_jurisdictions(engine, real_dataset):
    """Test REC-DO06: Diagonal equals internal flow for 32 normal jurisdictions."""
    raw_data, norm_tables = real_dataset
    results = engine.reconcile_rec_do06(raw_data, norm_tables, run_id="test_do06")

    assert len(results) == 33
    normal_results = [r for r in results if r.entity != "OTHER TERRITORY"]
    assert len(normal_results) == 32
    assert all(r.status == ReconciliationStatus.PASS.value for r in normal_results)
    assert all(r.absolute_difference < 0.001 for r in normal_results)


def test_rec_do06_other_territory_unresolved_status(engine, real_dataset):
    """Test REC-DO06: OTHER TERRITORY returns UNRESOLVED with documented message and exact discrepancy."""
    raw_data, norm_tables = real_dataset
    results = engine.reconcile_rec_do06(raw_data, norm_tables, run_id="test_do06")

    ot_res = [r for r in results if r.entity == "OTHER TERRITORY"][0]
    assert ot_res.status == ReconciliationStatus.UNRESOLVED.value
    assert ot_res.severity == ReconciliationSeverity.WARNING.value
    assert ot_res.expected_value == pytest.approx(181709.488219, abs=1e-3)
    assert ot_res.observed_value == pytest.approx(258324.421758, abs=1e-3)
    assert ot_res.absolute_difference == pytest.approx(76614.933539, abs=1e-3)
    assert ot_res.message == "UNRESOLVED DATA/DEFINITION DIFFERENCE — REQUIRES FURTHER INVESTIGATION"


# -----------------------------------------------------------------------------
# 4. Tolerance & NULL Handling Tests
# -----------------------------------------------------------------------------

def test_tolerance_behavior(real_dataset):
    """Test configurable tolerance behavior on REC-DO01."""
    raw_data, norm_tables = real_dataset
    # Corrupt slightly by 0.005
    corrupted_tables = {k: v.copy() for k, v in norm_tables.items()}
    corrupted_tables["state_movement"].loc[0, "movement_value_inr_crore"] += 0.005

    # Strict engine (tolerance 0.0001, rel 1e-12) should produce WARNING
    strict_engine = ReconciliationEngine(ReconciliationConfig(absolute_tolerance=0.0001, relative_tolerance=1e-12))
    res_strict = strict_engine.reconcile_rec_do01(raw_data, corrupted_tables, "test_tol")
    assert res_strict.status == ReconciliationStatus.WARNING.value

    # Relaxed engine (tolerance 0.01) should produce PASS
    relaxed_engine = ReconciliationEngine(ReconciliationConfig(absolute_tolerance=0.01, relative_tolerance=1e-5))
    res_relaxed = relaxed_engine.reconcile_rec_do01(raw_data, corrupted_tables, "test_tol")
    assert res_relaxed.status == ReconciliationStatus.PASS.value


def test_null_handling_preservation(engine, real_dataset):
    """Test that source NULLs remain preserved in input dataframes after reconciliation."""
    raw_data, norm_tables = real_dataset
    initial_null_count = int(norm_tables["state_movement"]["movement_value_inr_crore"].isna().sum())
    assert initial_null_count == 5

    # Run reconciliations
    engine.run_all_reconciliations(raw_data, norm_tables, "test_nulls")

    # Assert NULL count remains intact (no global 0 mutation)
    final_null_count = int(norm_tables["state_movement"]["movement_value_inr_crore"].isna().sum())
    assert final_null_count == initial_null_count


# -----------------------------------------------------------------------------
# 5. Synthetic Discrepancy Produces WARNING (Non-Blocking)
# -----------------------------------------------------------------------------

def test_synthetic_cross_table_discrepancy_produces_warning(engine, real_dataset):
    """Test that an unexpected discrepancy produces WARNING rather than silently passing or crashing."""
    raw_data, norm_tables = real_dataset
    corrupted_tables = {k: v.copy() for k, v in norm_tables.items()}
    # Inject a large 50,000 Crore error in outward table
    corrupted_tables["state_chapter_outward"].loc[0, "movement_value_inr_crore"] += 50000.0

    res = engine.reconcile_rec_do02(raw_data, corrupted_tables, "test_synth")
    assert res.status == ReconciliationStatus.WARNING.value
    assert res.severity == ReconciliationSeverity.WARNING.value
    assert res.absolute_difference == pytest.approx(50000.0, abs=1e-2)


# -----------------------------------------------------------------------------
# 6. Database Persistence & Run Lineage
# -----------------------------------------------------------------------------

def test_reconciliation_persistence(engine, real_dataset):
    """Test persistence of all 103 reconciliation results into PostgreSQL."""
    raw_data, norm_tables = real_dataset
    db_mgr = DatabaseManager(
        host="127.0.0.1",
        port=5433,
        dbname="ewaybill_dw",
        user="postgres",
        password=os.getenv("POSTGRES_PASSWORD", "Saksham@3124")
    )

    try:
        conn = db_mgr.get_connection()
        conn.close()
    except Exception as e:
        pytest.skip(f"PostgreSQL unavailable: {e}")

    repo = EwayBillRepository(db_mgr)
    run_id = repo.start_pipeline_run(
        raw_data["metadata"]["source_filename"],
        raw_data["metadata"]["source_filepath"]
    )

    results = engine.run_all_reconciliations(raw_data, norm_tables, run_id=run_id)
    assert len(results) == 103

    inserted = repo.record_reconciliation_results(run_id, results)
    assert inserted == 103

    conn = db_mgr.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM reconciliation_results WHERE run_id = %s;", (run_id,))
            count = cur.fetchone()[0]
            assert count == 103
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# 7. Governance Constraints Enforcement Test
# -----------------------------------------------------------------------------

def test_governance_no_data_tampering_or_rejected_rules(engine, real_dataset):
    """
    Governance test ensuring that:
    1. OTHER TERRITORY values are never mutated or imputed.
    2. Universal diagonal equality is NOT asserted.
    3. REC-NV01 through REC-NV04 are NOT implemented.
    """
    raw_data, norm_tables = real_dataset
    results = engine.run_all_reconciliations(raw_data, norm_tables, "test_gov")

    rule_codes = {r.rule_code for r in results}
    # Assert rejected rules are absent
    for nv_code in ["REC-NV01", "REC-NV02", "REC-NV03", "REC-NV04"]:
        assert nv_code not in rule_codes, f"Rejected rule {nv_code} found in reconciliation engine results!"

    # Assert OTHER TERRITORY was never marked as PASS with modified difference
    ot_results = [r for r in results if r.rule_code == "REC-DO06" and r.entity == "OTHER TERRITORY"]
    assert len(ot_results) == 1
    ot = ot_results[0]
    assert ot.status == ReconciliationStatus.UNRESOLVED.value
    assert ot.absolute_difference == pytest.approx(76614.933539, abs=1e-3)
    assert ot.message == "UNRESOLVED DATA/DEFINITION DIFFERENCE — REQUIRES FURTHER INVESTIGATION"
