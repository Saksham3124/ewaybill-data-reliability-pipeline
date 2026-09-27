"""
tests/test_corruption_simulation.py
-----------------------------------
Comprehensive unit and integration tests for Phase 7 Controlled Corruption Simulation
and Detection Testing.
Verifies:
1. Source workbooks byte-level immutability (SHA-256 verification).
2. Deterministic scenario generation across all 7 scenarios (A through G).
3. Detection capability for each individual corruption scenario.
4. Correctness of responsible detector assignment and error diagnostic message.
5. Strict pipeline-blocking behavior (blocking for integrity checks, advisory for statistical shift).
6. Production database isolation (zero contaminated rows in PostgreSQL warehouse).
7. Reproducibility across multiple runs.
8. Report compilation and markdown matrix compliance.
"""

import hashlib
import os
from pathlib import Path
import pytest

from src.database.connection import DatabaseManager
from src.ingestion.loader import EwayBillSourceLoader
from src.transformation.normalizer import EwayBillNormalizer
from src.corruption.models import CorruptionScenario, DetectionResult, CorruptionType
from src.corruption.scenarios import (
    get_scenario_definitions,
    deepcopy_dataset,
    apply_scenario_a,
    apply_scenario_b,
    apply_scenario_c,
    apply_scenario_d,
    apply_scenario_e,
    apply_scenario_f,
    apply_scenario_g,
)
from src.corruption.runner import CorruptionSimulationRunner
from src.corruption.reporter import CorruptionReporter

F22_PATH = "data/Road_EwayBill_2022_23.xlsx"
F24_PATH = "data/Road_EwayBill_2023_24.xlsx"
EXPECTED_HASH_22 = "534ae64cdfe76ae1adbe5db789443cd5af5fc34df94925beba1949859d209aef"
EXPECTED_HASH_24 = "42fdba9a6fcf40fb47f9a632d403b28680e610160db51cf75511163f59ce803d"


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture(scope="module")
def clean_datasets():
    """Ingests clean workbooks and normalized tables into memory once for tests."""
    loader_22 = EwayBillSourceLoader(F22_PATH)
    raw_22 = loader_22.load_raw_workbook()

    loader_24 = EwayBillSourceLoader(F24_PATH)
    raw_24 = loader_24.load_raw_workbook()

    normalizer_24 = EwayBillNormalizer(raw_24["tables"])
    norm_24 = normalizer_24.normalize_all()

    return raw_22, raw_24, norm_24


@pytest.fixture
def runner():
    return CorruptionSimulationRunner()


# -----------------------------------------------------------------------------
# 1. Source Immutability
# -----------------------------------------------------------------------------

def test_source_immutability():
    """Verifies that original Excel workbooks remain strictly byte-for-byte unmodified."""
    assert compute_sha256(F22_PATH) == EXPECTED_HASH_22, f"Source {F22_PATH} was altered!"
    assert compute_sha256(F24_PATH) == EXPECTED_HASH_24, f"Source {F24_PATH} was altered!"


# -----------------------------------------------------------------------------
# 2. Deterministic Scenario Definitions
# -----------------------------------------------------------------------------

def test_deterministic_scenario_definitions():
    """Verifies that all 7 scenarios are defined deterministically without unseeded randomness."""
    scenarios = get_scenario_definitions()
    assert len(scenarios) == 7

    expected_keys = [f"CORRUPT-{c}" for c in ["A", "B", "C", "D", "E", "F", "G"]]
    for k in expected_keys:
        assert k in scenarios
        sc = scenarios[k]
        assert isinstance(sc, CorruptionScenario)
        assert sc.scenario_id == k
        assert sc.random_seed is None  # Deterministic record selection


# -----------------------------------------------------------------------------
# 3. Individual Scenario Detection Tests
# -----------------------------------------------------------------------------

def test_scenario_a_missing_record(runner, clean_datasets):
    """Test Scenario A: Missing State/Chapter record caught by CMP-03 and blocks pipeline."""
    raw_22, raw_24, norm_24 = clean_datasets
    res = runner.run_scenario_a(raw_24, norm_24)

    assert res.scenario_id == "CORRUPT-A"
    assert res.corruption_type == CorruptionType.MISSING_RECORD.value
    assert res.detected is True
    assert res.pipeline_blocked is True
    assert res.false_positive is False
    assert "CMP-03" in res.actual_detector
    assert "2969" in res.detection_message


def test_scenario_b_duplicate_record(runner, clean_datasets):
    """Test Scenario B: Duplicate Logical Record caught by UNQ-03 and blocks pipeline."""
    raw_22, raw_24, norm_24 = clean_datasets
    res = runner.run_scenario_b(raw_24, norm_24)

    assert res.scenario_id == "CORRUPT-B"
    assert res.corruption_type == CorruptionType.DUPLICATE_RECORD.value
    assert res.detected is True
    assert res.pipeline_blocked is True
    assert res.false_positive is False
    assert "UNQ-03" in res.actual_detector
    assert "duplicate" in res.detection_message.lower()


def test_scenario_c_invalid_chapter_domain(runner, clean_datasets):
    """Test Scenario C: Invalid Chapter Code caught by DOM-03 and blocks pipeline."""
    raw_22, raw_24, norm_24 = clean_datasets
    res = runner.run_scenario_c(raw_24, norm_24)

    assert res.scenario_id == "CORRUPT-C"
    assert res.corruption_type == CorruptionType.INVALID_DOMAIN.value
    assert res.detected is True
    assert res.pipeline_blocked is True
    assert res.false_positive is False
    assert "DOM-03" in res.actual_detector
    assert "invalid chapter code" in res.detection_message.lower()


def test_scenario_d_altered_movement_value(runner, clean_datasets):
    """Test Scenario D: Altered numeric value caught by REC-V02/REC-DO02 and blocks pipeline."""
    raw_22, raw_24, norm_24 = clean_datasets
    res = runner.run_scenario_d(raw_24, norm_24)

    assert res.scenario_id == "CORRUPT-D"
    assert res.corruption_type == CorruptionType.ALTERED_NUMERIC.value
    assert res.detected is True
    assert res.pipeline_blocked is True
    assert res.false_positive is False
    assert "REC-V02" in res.actual_detector
    assert "REC-DO02" in res.actual_detector
    assert "500.00" in res.detection_message


def test_scenario_e_missing_state_column(runner, clean_datasets):
    """Test Scenario E: Missing state column from Table III caught by CMP-03/REC-DO02 and blocks."""
    raw_22, raw_24, norm_24 = clean_datasets
    res = runner.run_scenario_e(raw_24, norm_24)

    assert res.scenario_id == "CORRUPT-E"
    assert res.corruption_type == CorruptionType.MISSING_ENTITY_COLUMN.value
    assert res.detected is True
    assert res.pipeline_blocked is True
    assert res.false_positive is False
    assert "CMP-03" in res.actual_detector
    assert "REC-DO02" in res.actual_detector
    assert "BIHAR" in res.detection_message


def test_scenario_f_numeric_to_text(runner, clean_datasets):
    """Test Scenario F: Non-numeric textual string caught by NUM-01 and blocks pipeline."""
    raw_22, raw_24, norm_24 = clean_datasets
    res = runner.run_scenario_f(raw_24, norm_24)

    assert res.scenario_id == "CORRUPT-F"
    assert res.corruption_type == CorruptionType.NUMERIC_TO_TEXT.value
    assert res.detected is True
    assert res.pipeline_blocked is True
    assert res.false_positive is False
    assert "NUM-01" in res.actual_detector
    assert "non-numeric" in res.detection_message.lower()


def test_scenario_g_distribution_shift_advisory(runner, clean_datasets):
    """Test Scenario G: Controlled distribution shift detected by KS & PSI as ADVISORY non-blocking signal."""
    raw_22, raw_24, norm_24 = clean_datasets
    res = runner.run_scenario_g(raw_22, raw_24)

    assert res.scenario_id == "CORRUPT-G"
    assert res.corruption_type == CorruptionType.DISTRIBUTION_SHIFT.value
    assert res.detected is True
    assert res.pipeline_blocked is False  # Advisory signal, does NOT block trusted loading
    assert res.false_positive is False
    assert "KS_TEST" in res.actual_detector
    assert "PSI" in res.actual_detector
    assert "STATISTICALLY_DIFFERENT" in res.detection_message


# -----------------------------------------------------------------------------
# 4. Full Runner & Pipeline Blocking Summary
# -----------------------------------------------------------------------------

def test_full_runner_execution(runner, clean_datasets):
    """Test running all 7 scenarios together via runner."""
    raw_22, raw_24, norm_24 = clean_datasets
    results = runner.run_all_scenarios(raw_22, raw_24, norm_24)

    assert len(results) == 7
    assert all(r.detected for r in results)
    assert sum(1 for r in results if r.pipeline_blocked) == 6
    assert sum(1 for r in results if not r.pipeline_blocked) == 1
    assert all(not r.false_positive for r in results)


# -----------------------------------------------------------------------------
# 5. Production Database Isolation
# -----------------------------------------------------------------------------

def test_production_database_isolation(runner, clean_datasets):
    """Test that running corruption simulations leaves production warehouse tables unmodified."""
    db_mgr = DatabaseManager(
        host="127.0.0.1",
        port=5433,
        dbname="ewaybill_dw",
        user="postgres",
        password=os.getenv("POSTGRES_PASSWORD", "Saksham@3124")
    )
    try:
        conn = db_mgr.get_connection()
    except Exception as e:
        pytest.skip(f"PostgreSQL connection unavailable: {e}")

    tables_to_check = [
        "trusted_state_movement", "trusted_chapter_movement",
        "trusted_state_chapter_outward", "trusted_state_chapter_inward",
        "trusted_state_chapter_internal"
    ]

    counts_before = {}
    try:
        with conn.cursor() as cur:
            for tbl in tables_to_check:
                cur.execute(f"SELECT COUNT(*) FROM {tbl};")
                counts_before[tbl] = cur.fetchone()[0]
    finally:
        conn.close()

    # Execute simulation
    raw_22, raw_24, norm_24 = clean_datasets
    runner.run_all_scenarios(raw_22, raw_24, norm_24)

    # Re-verify counts
    conn = db_mgr.get_connection()
    counts_after = {}
    try:
        with conn.cursor() as cur:
            for tbl in tables_to_check:
                cur.execute(f"SELECT COUNT(*) FROM {tbl};")
                counts_after[tbl] = cur.fetchone()[0]
    finally:
        conn.close()

    assert counts_before == counts_after, f"Isolation failure! Counts changed: {counts_before} vs {counts_after}"


# -----------------------------------------------------------------------------
# 6. Reproducibility
# -----------------------------------------------------------------------------

def test_simulation_reproducibility(runner, clean_datasets):
    """Test that two separate executions of the simulation suite produce identical detection outcomes."""
    raw_22, raw_24, norm_24 = clean_datasets

    run1 = runner.run_all_scenarios(raw_22, raw_24, norm_24)
    run2 = runner.run_all_scenarios(raw_22, raw_24, norm_24)

    for r1, r2 in zip(run1, run2):
        assert r1.scenario_id == r2.scenario_id
        assert r1.detected == r2.detected
        assert r1.pipeline_blocked == r2.pipeline_blocked
        assert r1.actual_detector == r2.actual_detector
        assert r1.corrupted_value == r2.corrupted_value


# -----------------------------------------------------------------------------
# 7. Reporter Output
# -----------------------------------------------------------------------------

def test_corruption_reporter(runner, clean_datasets, tmp_path):
    """Test that CorruptionReporter outputs a valid markdown report with expected structure."""
    raw_22, raw_24, norm_24 = clean_datasets
    results = runner.run_all_scenarios(raw_22, raw_24, norm_24)

    out_file = tmp_path / "test_corruption_report.md"
    content = CorruptionReporter.generate_report(results, "test_run_123", str(out_file))

    assert out_file.exists()
    assert "# Controlled Corruption Simulation & Detection Report" in content
    assert "## 2. Detection Matrix" in content
    assert "CORRUPT-A" in content
    assert "CORRUPT-G" in content
    assert "🛑 BLOCKED" in content
    assert "ℹ️ ADVISORY" in content
